from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .domain import ContactPoint, Evidence, Person, ProfessionalRole, Source

JENSEN_PROFILE_URL = "https://nvidianews.nvidia.com/bios/jensen-huang"
NVIDIA_COMPANY_ID = "company:sec:cik:0001045810"
JENSEN_PERSON_ID = "person:nvidia:jensen-huang"
JENSEN_ROLE_ID = "role:nvidia:jensen-huang:founder-ceo"
PERSON_ROLE_DISCOVERY_RULE_V1 = "NVIDIA_OFFICIAL_EXECUTIVE_BIO_V1"

_NAME = re.compile(rb"\bJensen Huang\b", re.IGNORECASE)
_ROLE = re.compile(rb"\bFounder\s*&\s*CEO\b", re.IGNORECASE)


class PersonDiscoveryContractError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PersonRoleDiscoveryBatch:
    source: Source
    evidence: Evidence
    person: Person
    role: ProfessionalRole
    professional_profile: ContactPoint


def discover_jensen_huang_profile(
    raw_content: bytes, *, retrieved_at: str | None = None
) -> PersonRoleDiscoveryBatch:
    if not isinstance(raw_content, bytes):
        raise PersonDiscoveryContractError("executive profile evidence must be bytes")
    if _NAME.search(raw_content) is None or _ROLE.search(raw_content) is None:
        raise PersonDiscoveryContractError(
            "known NVIDIA executive profile no longer exposes expected name and role"
        )

    digest = hashlib.sha256(raw_content).hexdigest()
    source = Source(
        id="source:nvidia:newsroom:jensen-huang",
        name="NVIDIA Newsroom Jensen Huang executive bio",
        kind="OFFICIAL_COMPANY_EXECUTIVE_PROFILE",
        locator=JENSEN_PROFILE_URL,
    )
    evidence = Evidence(
        id=f"evidence:sha256:{digest}",
        source_id=source.id,
        raw_content=raw_content,
        sha256=digest,
        retrieved_at=retrieved_at,
    )
    person = Person(
        id=JENSEN_PERSON_ID,
        name="Jensen Huang",
        evidence_id=evidence.id,
    )
    role = ProfessionalRole(
        id=JENSEN_ROLE_ID,
        person_id=person.id,
        company_id=NVIDIA_COMPANY_ID,
        title="Founder & CEO",
        evidence_id=evidence.id,
    )
    professional_profile = ContactPoint(
        id=f"contact:{person.id}:professional-profile:{digest[:16]}",
        owner_type="Person",
        owner_id=person.id,
        kind="URL",
        value=JENSEN_PROFILE_URL,
        evidence_id=evidence.id,
        discovery_rule=PERSON_ROLE_DISCOVERY_RULE_V1,
    )
    return PersonRoleDiscoveryBatch(
        source=source,
        evidence=evidence,
        person=person,
        role=role,
        professional_profile=professional_profile,
    )
