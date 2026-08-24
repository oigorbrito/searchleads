from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .enums import ContactKind, ContactStatus, LeadStage, QualificationStatus
from .provenance import utc_now


@dataclass(frozen=True, slots=True)
class Company:
    """Enterprise entity. Identity attributes live as source-backed facts."""

    company_id: str
    candidate_fact_ids: tuple[str, ...] = ()
    canonical_fact_ids: tuple[str, ...] = ()
    person_ids: tuple[str, ...] = ()
    contact_point_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.company_id.strip():
            raise ValueError("company_id must not be blank")


@dataclass(frozen=True, slots=True)
class Person:
    """A professional person linked to a company with explicit evidence."""

    person_id: str
    company_id: str
    relationship_evidence_ids: tuple[str, ...]
    candidate_fact_ids: tuple[str, ...] = ()
    canonical_fact_ids: tuple[str, ...] = ()
    contact_point_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.person_id.strip():
            raise ValueError("person_id must not be blank")
        if not self.company_id.strip():
            raise ValueError("company_id must not be blank")
        if not self.relationship_evidence_ids:
            raise ValueError("person requires company relationship evidence")
        if any(not item.strip() for item in self.relationship_evidence_ids):
            raise ValueError("relationship_evidence_ids must not contain blanks")


@dataclass(frozen=True, slots=True)
class ContactPoint:
    """A discovered professional contact; discovery and validation are separate."""

    contact_id: str
    owner_id: str
    kind: ContactKind
    value: str
    discovery_evidence_ids: tuple[str, ...]
    status: ContactStatus = ContactStatus.DISCOVERED
    discovered_at: datetime = field(default_factory=utc_now)
    validation_evidence_ids: tuple[str, ...] = ()
    validated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.contact_id.strip():
            raise ValueError("contact_id must not be blank")
        if not self.owner_id.strip():
            raise ValueError("owner_id must not be blank")
        if not self.value.strip():
            raise ValueError("contact value must not be blank")
        if not self.discovery_evidence_ids:
            raise ValueError("contact requires discovery evidence")
        if any(not item.strip() for item in self.discovery_evidence_ids):
            raise ValueError("discovery_evidence_ids must not contain blanks")
        if self.discovered_at.tzinfo is None:
            raise ValueError("discovered_at must be timezone-aware")
        assessed = self.status in {
            ContactStatus.VALIDATED,
            ContactStatus.INVALID,
            ContactStatus.STALE,
        }
        if assessed and not self.validation_evidence_ids:
            raise ValueError("assessed contact status requires validation evidence")
        if assessed and self.validated_at is None:
            raise ValueError("assessed contact status requires validated_at")
        if self.validated_at is not None and self.validated_at.tzinfo is None:
            raise ValueError("validated_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class Lead:
    """Commercial-pipeline wrapper around a Company; not synonymous with Company."""

    lead_id: str
    company_id: str
    stage: LeadStage = LeadStage.CANDIDATE
    qualification_status: QualificationStatus = QualificationStatus.UNKNOWN
    qualification_reasons: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.lead_id.strip():
            raise ValueError("lead_id must not be blank")
        if not self.company_id.strip():
            raise ValueError("company_id must not be blank")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if self.stage is LeadStage.QUALIFIED and self.qualification_status is not QualificationStatus.QUALIFIED:
            raise ValueError("QUALIFIED stage requires QUALIFIED qualification_status")
        if self.stage is LeadStage.DISQUALIFIED and self.qualification_status is not QualificationStatus.NOT_QUALIFIED:
            raise ValueError("DISQUALIFIED stage requires NOT_QUALIFIED qualification_status")
