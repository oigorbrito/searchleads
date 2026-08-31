"""Evidence-backed person/role discovery for PERSON_AND_ROLE_DISCOVERY_V1."""
from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import hashlib
import re
from typing import Iterable
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

from searchleads.contact_discovery import HTTPPageObservation, http_get
from searchleads.domain import (
    CandidateFact,
    Company,
    ContactKind,
    ContactPoint,
    ContactStatus,
    DecisionClass,
    Evidence,
    Person,
    Provenance,
    Source,
)
from searchleads.persistence import SQLiteRepository

AGENT = "searchleads.person_discovery.company_people.v1"
NAME_FIELD = "person_name"
ROLE_FIELD = "professional_role_title"
_ROLE_RE = re.compile(
    r"^(?:diretor(?:a)?(?:-presidente)?\b|presidente\b|vice-presidente\b|ceo\b|cfo\b|cto\b|coo\b|"
    r"chief\b|gerente\b|superintendente\b|head\b|s[oó]ci[oa]\b|partner\b|"
    r"conselheir[oa]\b|secret[áa]ri[oa]\b|auditor(?:a)?\b|ouvidor(?:a)?\b|corregedor(?:a)?\b)",
    re.I,
)
_EMAIL_RE = re.compile(r"(?<![\w.+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![\w.-])", re.I)
_PHONE_RE = re.compile(r"(?:telefone|fone|tel\.?|phone)\s*:?\s*(\+?[\d(][\d\s()./-]{5,}\d)", re.I)
_IGNORED = {"script", "style", "noscript", "template"}
_PARTICLES = {"de", "da", "do", "das", "dos", "e", "del", "van", "von"}


class PersonDiscoveryError(RuntimeError):
    """Base error for person/role discovery."""


class PersonPageResponseError(PersonDiscoveryError):
    """Non-success response persisted before person extraction."""

    def __init__(self, status_code: int, evidence_id: str) -> None:
        self.status_code = status_code
        self.evidence_id = evidence_id
        super().__init__(f"people page returned HTTP {status_code}; evidence={evidence_id}")


class PersonAcquisitionError(PersonDiscoveryError):
    """Transport observation is not usable for the requested people page."""


@dataclass(frozen=True, slots=True)
class PersonContactObservation:
    kind: ContactKind
    value: str


@dataclass(frozen=True, slots=True)
class PersonRoleObservation:
    ordinal: int
    name: str
    title: str
    contacts: tuple[PersonContactObservation, ...] = ()

    def __post_init__(self) -> None:
        if self.ordinal < 1:
            raise ValueError("ordinal must be positive")
        if not self.name.strip() or not self.title.strip():
            raise ValueError("name and title must not be blank")


@dataclass(frozen=True, slots=True)
class PersonDiscoveryResult:
    company: Company
    source: Source
    evidence: Evidence
    observations: tuple[PersonRoleObservation, ...]
    people: tuple[Person, ...]
    provenances: tuple[Provenance, ...]
    candidate_facts: tuple[CandidateFact, ...]
    contacts: tuple[ContactPoint, ...]
    evidence_was_new: bool


@dataclass(frozen=True, slots=True)
class _Event:
    kind: str
    value: str


class _EventParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.events: list[_Event] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        if tag in _IGNORED:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if tag == "a":
            data = {key.casefold(): value for key, value in attrs if key}
            href = data.get("href")
            if href:
                self.events.append(_Event("href", href.strip()))

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in _IGNORED and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        text = " ".join(data.split())
        if text:
            self.events.append(_Event("text", text))


def _is_role(text: str) -> bool:
    return bool(_ROLE_RE.match(text.strip()))


def _is_name(text: str) -> bool:
    value = " ".join(text.split())
    if not 2 <= len(value.split()) <= 10 or any(ch.isdigit() for ch in value) or any(x in value for x in "@:/"):
        return False
    words = value.split()
    for word in words:
        bare = word.strip(".,;()[]{}'’-")
        if not bare:
            return False
        if bare.casefold() in _PARTICLES:
            continue
        letters = [ch for ch in bare if ch.isalpha()]
        if not letters:
            return False
        first = letters[0]
        if not (first.isupper() or bare.isupper()):
            return False
    lowered = value.casefold()
    blocked = ("telefone", "email", "e-mail", "contato", "diretoria", "empresa", "serpro sede")
    return not any(term in lowered for term in blocked)


def _valid_email(value: str) -> bool:
    if len(value) > 254 or value.count("@") != 1:
        return False
    local, domain = value.rsplit("@", 1)
    if not local or len(local) > 64 or not domain or "." not in domain:
        return False
    if re.fullmatch(r"[A-Z0-9._%+-]+", local, re.I) is None or re.fullmatch(r"[A-Z0-9.-]+", domain, re.I) is None:
        return False
    labels = domain.split(".")
    return len(domain) <= 253 and all(1 <= len(label) <= 63 and not label.startswith("-") and not label.endswith("-") for label in labels)


def _clean_phone(value: str) -> str | None:
    cleaned = " ".join(unquote(value).split()).strip(" ,;.")
    digits = re.sub(r"\D", "", cleaned)
    return cleaned if 7 <= len(digits) <= 15 else None


def _profile_url(base_url: str, href: str) -> str | None:
    try:
        parsed = urlsplit(urljoin(base_url, href))
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return None
    host = parsed.hostname.casefold().rstrip(".")
    if host != "linkedin.com" and not host.endswith(".linkedin.com"):
        return None
    segments = [part for part in parsed.path.split("/") if part]
    if len(segments) != 2 or segments[0].casefold() != "in":
        return None
    return urlunsplit((parsed.scheme.lower(), host, f"/in/{segments[1]}", "", ""))


def _contact_key(item: PersonContactObservation) -> tuple[str, str]:
    if item.kind is ContactKind.EMAIL:
        value = item.value.casefold()
    elif item.kind is ContactKind.PHONE:
        value = re.sub(r"\D", "", item.value)
    else:
        value = item.value.rstrip("/").casefold()
    return item.kind.value, value


def _contacts_in_window(base_url: str, events: list[_Event]) -> tuple[PersonContactObservation, ...]:
    found: list[PersonContactObservation] = []
    for event in events:
        if event.kind == "href":
            lower = event.value.casefold()
            if lower.startswith("mailto:"):
                email = unquote(event.value.split(":", 1)[1].split("?", 1)[0]).strip()
                if _valid_email(email):
                    found.append(PersonContactObservation(ContactKind.EMAIL, email))
                continue
            if lower.startswith("tel:"):
                value = event.value.split(":", 1)[1].split("?", 1)[0].split(";", 1)[0]
                if phone := _clean_phone(value):
                    found.append(PersonContactObservation(ContactKind.PHONE, phone))
                continue
            if profile := _profile_url(base_url, event.value):
                found.append(PersonContactObservation(ContactKind.PROFESSIONAL_PROFILE, profile))
        else:
            for match in _EMAIL_RE.finditer(event.value):
                email = match.group(1)
                if _valid_email(email):
                    found.append(PersonContactObservation(ContactKind.EMAIL, email))
            for match in _PHONE_RE.finditer(event.value):
                if phone := _clean_phone(match.group(1)):
                    found.append(PersonContactObservation(ContactKind.PHONE, phone))
    deduped: dict[tuple[str, str], PersonContactObservation] = {}
    for item in found:
        deduped.setdefault(_contact_key(item), item)
    return tuple(sorted(deduped.values(), key=lambda item: (item.kind.value, _contact_key(item)[1])))


def discover_person_roles_from_html(url: str, html: str, *, contact_window_events: int = 12) -> tuple[PersonRoleObservation, ...]:
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("url must be an absolute http/https URL")
    if not isinstance(html, str):
        raise TypeError("html must be text")
    if contact_window_events < 1:
        raise ValueError("contact_window_events must be positive")
    parser = _EventParser(); parser.feed(html)
    events = parser.events
    results: list[PersonRoleObservation] = []
    ordinal = 0
    for role_index, event in enumerate(events):
        if event.kind != "text" or not _is_role(event.value):
            continue
        name_index: int | None = None
        text_seen = 0
        for idx in range(role_index + 1, min(len(events), role_index + 12)):
            candidate = events[idx]
            if candidate.kind != "text":
                continue
            text_seen += 1
            if _is_role(candidate.value):
                break
            if _is_name(candidate.value):
                name_index = idx
                break
            if text_seen >= 5:
                break
        if name_index is None:
            continue
        ordinal += 1
        stop = min(len(events), name_index + 1 + contact_window_events)
        for idx in range(name_index + 1, stop):
            if events[idx].kind == "text" and _is_role(events[idx].value):
                stop = idx
                break
        contacts = _contacts_in_window(url, events[name_index + 1:stop])
        results.append(PersonRoleObservation(ordinal, events[name_index].value, event.value, contacts))
    return tuple(results)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fact_and_provenance(person_id: str, field_name: str, value: str, evidence: Evidence, suffix: str) -> tuple[Provenance, CandidateFact]:
    provenance_id = f"provenance:person-discovery:{suffix}:{_digest(person_id + '\0' + evidence.evidence_id)[:24]}"
    fact_id = f"fact:person-discovery:{suffix}:{_digest(person_id + '\0' + value + '\0' + evidence.evidence_id)[:24]}"
    provenance = Provenance(
        provenance_id, person_id, field_name, (evidence.evidence_id,),
        "discover-person-role-from-company-page-v1", evidence.captured_at, AGENT,
    )
    fact = CandidateFact(
        fact_id, person_id, field_name, value, None, (evidence.evidence_id,), provenance_id,
        None, DecisionClass.EVIDENCE_BACKED, evidence.captured_at,
    )
    return provenance, fact


class CompanyPeopleSource:
    def __init__(self, transport=http_get) -> None:
        self._transport = transport

    def ingest(self, company_id: str, url: str, repository: SQLiteRepository) -> PersonDiscoveryResult:
        company = repository.load(Company, company_id)
        if company is None:
            raise ValueError(f"company must already be persisted: {company_id}")
        observation: HTTPPageObservation = self._transport(url)
        if observation.url != url:
            raise PersonAcquisitionError("transport returned an observation for a different URL")
        source_id = f"source:company-people-page:{_digest(url)[:24]}"
        source = Source(source_id, "company-people-page", url, "Company people page")
        repository.save(source)
        observation_id = _digest(f"{url}\0{observation.status_code}\0{observation.raw_html}")
        evidence_id = f"evidence:company-people-page:{observation_id}"
        existing = repository.load(Evidence, evidence_id)
        if existing is None:
            evidence = Evidence(
                evidence_id, source_id, url, observation.captured_at, observation.raw_html,
                f"sha256:{_digest(observation.raw_html)}",
                {"http_status": observation.status_code, "headers": dict(observation.headers), "transport": "http"},
            )
            repository.save(evidence); evidence_was_new = True
        else:
            if existing.locator != url or existing.raw_payload != observation.raw_html:
                raise PersonAcquisitionError("content-addressed evidence ID collision")
            evidence = existing; evidence_was_new = False
        if observation.status_code != 200:
            raise PersonPageResponseError(observation.status_code, evidence.evidence_id)

        observations = discover_person_roles_from_html(url, observation.raw_html)
        people: list[Person] = []; provenances: list[Provenance] = []; facts: list[CandidateFact] = []; contacts: list[ContactPoint] = []
        for item in observations:
            normalized_name = " ".join(item.name.split()).casefold()
            normalized_role = " ".join(item.title.split()).casefold()
            person_id = "person:observation:" + _digest(
                f"{company_id}\0{evidence.evidence_id}\0{item.ordinal}\0{normalized_name}\0{normalized_role}"
            )
            name_prov, name_fact = _fact_and_provenance(person_id, NAME_FIELD, item.name, evidence, "name")
            role_prov, role_fact = _fact_and_provenance(person_id, ROLE_FIELD, item.title, evidence, "role")
            person_contacts: list[ContactPoint] = []
            for observed_contact in item.contacts:
                contact_id = "contact:person-discovered:" + _digest(
                    f"{person_id}\0{observed_contact.kind.value}\0{_contact_key(observed_contact)[1]}\0{evidence.evidence_id}"
                )
                person_contacts.append(ContactPoint(
                    contact_id, person_id, observed_contact.kind, observed_contact.value,
                    (evidence.evidence_id,), ContactStatus.DISCOVERED, evidence.captured_at,
                ))
            person = Person(
                person_id, company_id, (evidence.evidence_id,),
                (name_fact.fact_id, role_fact.fact_id), (), tuple(c.contact_id for c in person_contacts),
            )
            repository.save(person)
            for provenance in (name_prov, role_prov): repository.save(provenance)
            for fact in (name_fact, role_fact): repository.save(fact)
            for contact in person_contacts: repository.save(contact)
            people.append(person); provenances.extend((name_prov, role_prov)); facts.extend((name_fact, role_fact)); contacts.extend(person_contacts)
        return PersonDiscoveryResult(company, source, evidence, observations, tuple(people), tuple(provenances), tuple(facts), tuple(contacts), evidence_was_new)
