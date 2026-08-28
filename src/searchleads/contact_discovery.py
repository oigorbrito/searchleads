from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .domain import ContactPoint, Evidence, Source

NVIDIA_CONTACT_URL = "https://www.nvidia.com/en-us/contact/"
NVIDIA_COMPANY_ID = "company:sec:cik:0001045810"
NVIDIA_CONTACT_RULE_V1 = "NVIDIA_OFFICIAL_CONTACT_PAGE_V1"

_EMAIL = re.compile(rb"\binfo@nvidia\.com\b", re.IGNORECASE)
_PHONE = re.compile(rb"\+1\s*\(408\)\s*486-2000")


class ContactDiscoveryContractError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ContactDiscovery:
    contact_point: ContactPoint
    status: str = "DISCOVERED"


@dataclass(frozen=True, slots=True)
class ContactDiscoveryBatch:
    source: Source
    evidence: Evidence
    discoveries: tuple[ContactDiscovery, ...]

    @property
    def contacts(self) -> tuple[ContactPoint, ...]:
        return tuple(discovery.contact_point for discovery in self.discoveries)


def discover_nvidia_official_contacts(
    raw_content: bytes, *, retrieved_at: str | None = None
) -> ContactDiscoveryBatch:
    if not isinstance(raw_content, bytes):
        raise ContactDiscoveryContractError("contact page evidence must be bytes")

    email_match = _EMAIL.search(raw_content)
    phone_match = _PHONE.search(raw_content)
    if email_match is None or phone_match is None:
        raise ContactDiscoveryContractError(
            "known NVIDIA contact page no longer exposes expected corporate email and phone"
        )

    digest = hashlib.sha256(raw_content).hexdigest()
    source = Source(
        id="source:nvidia:official-contact",
        name="NVIDIA official contact page",
        kind="OFFICIAL_COMPANY_CONTACT_PAGE",
        locator=NVIDIA_CONTACT_URL,
    )
    evidence = Evidence(
        id=f"evidence:sha256:{digest}",
        source_id=source.id,
        raw_content=raw_content,
        sha256=digest,
        retrieved_at=retrieved_at,
    )

    values = (
        ("EMAIL", email_match.group().decode("ascii").lower()),
        ("PHONE", "+1 (408) 486-2000"),
        ("URL", NVIDIA_CONTACT_URL),
    )
    discoveries = tuple(
        ContactDiscovery(
            ContactPoint(
                id=f"contact:{NVIDIA_COMPANY_ID}:{kind.lower()}:{digest[:16]}",
                owner_type="Company",
                owner_id=NVIDIA_COMPANY_ID,
                kind=kind,
                value=value,
                evidence_id=evidence.id,
                discovery_rule=NVIDIA_CONTACT_RULE_V1,
            )
        )
        for kind, value in values
    )
    return ContactDiscoveryBatch(source, evidence, discoveries)
