from __future__ import annotations

import hashlib
import html
from dataclasses import dataclass
from html.parser import HTMLParser
import re
from typing import Iterable
from urllib.parse import urljoin

from searchleads.domain import (
    CandidateFact,
    DecisionClass,
    Evidence,
    Person,
    Provenance,
    Source,
)
from searchleads.normalization import normalize_text
from searchleads.sources.brasilapi import HTTPObservation, http_get


AGENT = "company-people-discovery:v1"
_ROLE_TERMS = (
    "administrador",
    "administradora",
    "cirurgiao dentista",
    "cirurgiã dentista",
    "dentista",
    "diretor",
    "diretora",
    "responsavel tecnico",
    "responsável técnico",
    "responsavel tecnica",
    "responsável técnica",
    "socio",
    "sócio",
    "socia",
    "sócia",
    "titular",
)
_EMAIL_RE = re.compile(r"(?i)(?<![A-Z0-9._%+\-])[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}(?![A-Z0-9._%+\-])")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?(?:9\s*)?\d{4}[\s.\-]?\d{4}(?!\d)")
_CRO_RE = re.compile(r"(?i)\bCRO\s*[-/:]?\s*([A-Z]{2})?\s*[-/:]?\s*(\d{2,8})\b")
_TAG_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class PageEvent:
    kind: str
    value: str


@dataclass(frozen=True, slots=True)
class PersonRoleObservation:
    ordinal: int
    name: str
    role: str
    contacts: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class PersonRoleDiscoveryResult:
    source: Source
    evidence: Evidence
    people: tuple[Person, ...]
    facts: tuple[CandidateFact, ...]
    provenances: tuple[Provenance, ...]


class _PeopleHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.events: list[PageEvent] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "svg", "noscript"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        attributes = {str(key).lower(): value or "" for key, value in attrs}
        if tag == "a" and attributes.get("href"):
            self.events.append(PageEvent("href", html.unescape(attributes["href"])))
        if tag in {"br", "hr", "li", "p", "div", "section", "article", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.events.append(PageEvent("boundary", tag))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "svg", "noscript"}:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if not self._skip_depth and tag in {"li", "p", "div", "section", "article", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.events.append(PageEvent("boundary", tag))

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = _clean_text(data)
        if text:
            self.events.append(PageEvent("text", text))


def _clean_text(value: str) -> str:
    return _TAG_WS_RE.sub(" ", html.unescape(value)).strip()


def _normal(value: str) -> str:
    return normalize_text(value).lower()


def _is_role(value: str) -> bool:
    normalized = _normal(value)
    return any(term in normalized for term in _ROLE_TERMS)


def _is_name(value: str) -> bool:
    cleaned = _clean_text(value)
    if len(cleaned) < 3 or len(cleaned) > 120:
        return False
    if "@" in cleaned or _PHONE_RE.search(cleaned) or _CRO_RE.search(cleaned):
        return False
    words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ'’-]+", cleaned)
    if len(words) < 2 or len(words) > 8:
        return False
    if any(character.isdigit() for character in cleaned):
        return False
    normalized = _normal(cleaned)
    if _is_role(normalized):
        return False
    stop_phrases = (
        "entre em contato",
        "fale conosco",
        "nossa equipe",
        "quem somos",
        "saiba mais",
        "todos os direitos",
    )
    return not any(phrase in normalized for phrase in stop_phrases)


def _normalize_email(value: str) -> str:
    return value.strip().lower().strip(".,;:()[]{}<>")


def _normalize_phone(value: str) -> str | None:
    digits = "".join(character for character in value if character.isdigit())
    if digits.startswith("55") and len(digits) in {12, 13}:
        digits = digits[2:]
    if len(digits) not in {10, 11}:
        return None
    return digits


def _contacts_from_value(url: str, value: str) -> tuple[tuple[str, str], ...]:
    contacts: set[tuple[str, str]] = set()
    lower = value.lower()
    if lower.startswith("mailto:"):
        email = _normalize_email(value[7:].split("?", 1)[0])
        if email and _EMAIL_RE.fullmatch(email):
            contacts.add(("email", email))
    elif lower.startswith("tel:"):
        phone = _normalize_phone(value[4:].split("?", 1)[0])
        if phone:
            contacts.add(("phone", phone))
    elif lower.startswith("http://") or lower.startswith("https://"):
        absolute = urljoin(url, value)
        if "wa.me/" in absolute.lower() or "whatsapp" in absolute.lower():
            phone = _normalize_phone(absolute)
            if phone:
                contacts.add(("phone", phone))
    for email_match in _EMAIL_RE.findall(value):
        contacts.add(("email", _normalize_email(email_match)))
    for phone_match in _PHONE_RE.findall(value):
        phone = _normalize_phone(phone_match)
        if phone:
            contacts.add(("phone", phone))
    for state, number in _CRO_RE.findall(value):
        registry = f"CRO-{state.upper()}-{number}" if state else f"CRO-{number}"
        contacts.add(("professional_registration", registry))
    return tuple(sorted(contacts))


def _contacts_in_window(url: str, events: Iterable[PageEvent]) -> tuple[tuple[str, str], ...]:
    contacts: set[tuple[str, str]] = set()
    for event in events:
        if event.kind in {"text", "href"}:
            contacts.update(_contacts_from_value(url, event.value))
    return tuple(sorted(contacts))


def _extract_observations(url: str, raw_html: str, *, contact_window_events: int = 12) -> tuple[PersonRoleObservation, ...]:
    parser = _PeopleHTMLParser()
    parser.feed(raw_html)
    events = parser.events
    results: list[PersonRoleObservation] = []
    ordinal = 0
    for role_index, event in enumerate(events):
        if event.kind != "text" or not _is_role(event.value):
            continue
        name_index: int | None = None
        text_seen = 0
        lower_bound = max(-1, role_index - 8)
        for idx in range(role_index - 1, lower_bound, -1):
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
    separator = "\0"
    provenance_material = person_id + separator + evidence.evidence_id
    fact_material = person_id + separator + value + separator + evidence.evidence_id
    provenance_id = f"provenance:person-discovery:{suffix}:{_digest(provenance_material)[:24]}"
    fact_id = f"fact:person-discovery:{suffix}:{_digest(fact_material)[:24]}"
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

    def fetch(
        self,
        source: Source,
        company_id: str,
        url: str,
        *,
        fetched_at=None,
        body: str | None = None,
    ) -> PersonRoleDiscoveryResult:
        if body is None:
            observation = self._transport(url)
            raw_payload = observation.raw_payload
            captured_at = fetched_at or observation.captured_at
            locator = observation.url
        else:
            raw_payload = body
            captured_at = fetched_at
            locator = url
        if captured_at is None:
            raise ValueError("fetched_at is required when body is supplied")
        evidence_id = f"evidence:person-discovery:{_digest(locator + '\0' + captured_at.isoformat())[:24]}"
        evidence = Evidence(
            evidence_id,
            source.source_id,
            locator,
            captured_at,
            raw_payload,
            metadata={"purpose": "person-role-discovery"},
        )
        observations = _extract_observations(locator, raw_payload)
        people: list[Person] = []
        facts: list[CandidateFact] = []
        provenances: list[Provenance] = []
        for observation in observations:
            person_id = f"person:discovery:{_digest(company_id + '\0' + observation.name)[:24]}"
            role_provenance, role_fact = _fact_and_provenance(
                person_id, "role", observation.role, evidence, "role"
            )
            name_provenance, name_fact = _fact_and_provenance(
                person_id, "name", observation.name, evidence, "name"
            )
            provenances.extend((name_provenance, role_provenance))
            facts.extend((name_fact, role_fact))
            people.append(
                Person(
                    person_id,
                    company_id,
                    relationship_evidence_ids=(evidence.evidence_id,),
                    candidate_fact_ids=(name_fact.fact_id, role_fact.fact_id),
                )
            )
        return PersonRoleDiscoveryResult(
            source,
            evidence,
            tuple(people),
            tuple(facts),
            tuple(provenances),
        )


__all__ = [
    "CompanyPeopleSource",
    "PersonRoleDiscoveryResult",
    "PersonRoleObservation",
]
