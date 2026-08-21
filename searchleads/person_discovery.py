"""Official-page person and company-role discovery for Work Unit 8.

Person discovery creates source-observation identities. It does not collapse
same-name observations into one Person before Person Entity Resolution runs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import re
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .domain import Company, Evidence, Person, ProfessionalRole, Provenance, Source, SourceType
from .persistence import SQLiteLeadStore
from .role_persistence import save_professional_role

AGENT = "searchleads.person_discovery.v1"
_ROLE_RE = re.compile(r"^(?:Diretor(?:a)?(?:-Presidente)?|Presidente|Superintendente|Secret[áa]ri[oa](?:-Executiv[oa])?|Conselheir[oa]|Titular|Auditoria Interna|Ouvidoria|Corregedoria)(?:\b|\s|\-|–)", re.I)
_NAME_RE = re.compile(r"^[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ'’-]+(?:\s+(?:de|da|do|das|dos|e|[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ'’-]+)){1,9}$")


class PersonDiscoveryError(RuntimeError):
    pass


class PersonAcquisitionError(PersonDiscoveryError):
    pass


@dataclass(frozen=True, slots=True)
class PersonRoleObservation:
    name: str
    title: str


@dataclass(frozen=True, slots=True)
class PersonDiscoveryResult:
    company: Company
    source: Source
    evidence: Evidence
    people: tuple[Person, ...]
    roles: tuple[ProfessionalRole, ...]
    observations: tuple[PersonRoleObservation, ...]


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        text = " ".join(data.split())
        if text:
            self.parts.append(text)


def _http_get(url: str) -> str:
    request = Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "searchleads/0.9 (+https://github.com/tihotm/searchleads)",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise PersonAcquisitionError(f"failed to fetch {url}: {exc}") from exc


def discover_person_roles_from_html(html: str) -> tuple[PersonRoleObservation, ...]:
    parser = _TextParser()
    parser.feed(html)
    parts = parser.parts
    result = []
    seen = set()
    for i, title in enumerate(parts[:-1]):
        if not _ROLE_RE.search(title):
            continue
        for candidate in parts[i + 1 : i + 5]:
            if _ROLE_RE.search(candidate):
                break
            if _NAME_RE.fullmatch(candidate) and not re.search(
                r"Telefone|E-mail|CEP|Serpro", candidate, re.I
            ):
                key = (candidate.casefold(), title.casefold())
                if key not in seen:
                    seen.add(key)
                    result.append(PersonRoleObservation(candidate, title))
                break
    return tuple(result)


def _person_observation_id(
    company_id: str,
    evidence_id: str,
    ordinal: int,
    observation: PersonRoleObservation,
) -> str:
    """Create an idempotent source-observation identity, not a name identity."""
    normalized_name = " ".join(observation.name.split())
    normalized_title = " ".join(observation.title.split())
    material = "|".join(
        (
            company_id,
            evidence_id,
            str(ordinal),
            normalized_name.casefold(),
            normalized_title.casefold(),
        )
    )
    return "person:observation:" + hashlib.sha256(material.encode()).hexdigest()[:24]


HtmlTransport = Callable[[str], str]


class OfficialPeopleSource:
    def __init__(self, transport: HtmlTransport | None = None):
        self._transport = transport or _http_get

    def ingest(
        self,
        store: SQLiteLeadStore,
        company_id: str,
        url: str,
        *,
        retrieved_at: datetime | None = None,
        html: str | None = None,
    ) -> PersonDiscoveryResult:
        company = store.get_company(company_id)
        if company is None:
            raise ValueError(f"company must already be persisted: {company_id}")
        page = html if html is not None else self._transport(url)
        at = retrieved_at or datetime.now(timezone.utc)
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("retrieved_at must be timezone-aware")
        digest = hashlib.sha256(page.encode("utf-8")).hexdigest()
        source = Source(
            "source:people-page:" + hashlib.sha256(url.encode()).hexdigest()[:20],
            SourceType.OFFICIAL_SOURCE,
            url,
            "Official company people page",
        )
        evidence = Evidence(
            "evidence:people-page:" + digest[:24],
            source.source_id,
            at,
            {"content_type": "text/html", "body": page},
            locator=url,
            content_hash="sha256:" + digest,
        )
        provenance = Provenance(
            (evidence.evidence_id,),
            "discover_person_company_roles_from_official_page_v1",
            generated_at=at,
            agent=AGENT,
        )
        observations = discover_person_roles_from_html(page)
        people = []
        roles = []
        for ordinal, obs in enumerate(observations):
            person_id = _person_observation_id(
                company_id,
                evidence.evidence_id,
                ordinal,
                obs,
            )
            person = store.get_person(person_id) or Person(person_id, created_at=at)
            role_id = "role:official:" + hashlib.sha256(
                f"{person_id}|{company_id}|{obs.title}|{evidence.evidence_id}".encode()
            ).hexdigest()[:24]
            role = ProfessionalRole(
                role_id,
                person.person_id,
                company_id,
                obs.title,
                provenance,
            )
            people.append(person)
            roles.append(role)
        store.save_source(source)
        store.save_evidence(evidence)
        for person in people:
            store.save_person(person)
        for role in roles:
            save_professional_role(store, role)
        return PersonDiscoveryResult(
            company,
            source,
            evidence,
            tuple(people),
            tuple(roles),
            observations,
        )
