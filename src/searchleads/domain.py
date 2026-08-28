from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DomainInvariantError(ValueError):
    """Raised when a scientific domain invariant is violated."""


class ContactValidationStatus(str, Enum):
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"
    VALID = "VALID"
    STALE = "STALE"


class ReviewReason(str, Enum):
    ENTITY_AMBIGUITY = "ENTITY_AMBIGUITY"
    CONTACT_VALIDATION_UNKNOWN = "CONTACT_VALIDATION_UNKNOWN"
    FACT_CONFLICT = "FACT_CONFLICT"


@dataclass(frozen=True, slots=True)
class Source:
    id: str
    name: str
    kind: str
    locator: str

    def __post_init__(self) -> None:
        _require_text(self.id, "Source.id")
        _require_text(self.name, "Source.name")
        _require_text(self.kind, "Source.kind")
        _require_text(self.locator, "Source.locator")


@dataclass(frozen=True, slots=True)
class Evidence:
    id: str
    source_id: str
    raw_content: bytes
    sha256: str
    retrieved_at: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.id, "Evidence.id")
        _require_text(self.source_id, "Evidence.source_id")
        if not isinstance(self.raw_content, bytes):
            raise DomainInvariantError("Evidence.raw_content must be bytes")
        _require_text(self.sha256, "Evidence.sha256")


@dataclass(frozen=True, slots=True)
class Company:
    id: str
    legal_name: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.id, "Company.id")


@dataclass(frozen=True, slots=True)
class Person:
    id: str
    name: str
    evidence_id: str

    def __post_init__(self) -> None:
        _require_text(self.id, "Person.id")
        _require_text(self.name, "Person.name")
        _require_text(self.evidence_id, "Person.evidence_id")


@dataclass(frozen=True, slots=True)
class ProfessionalRole:
    id: str
    person_id: str
    company_id: str
    title: str
    evidence_id: str

    def __post_init__(self) -> None:
        _require_text(self.id, "ProfessionalRole.id")
        _require_text(self.person_id, "ProfessionalRole.person_id")
        _require_text(self.company_id, "ProfessionalRole.company_id")
        _require_text(self.title, "ProfessionalRole.title")
        _require_text(self.evidence_id, "ProfessionalRole.evidence_id")


@dataclass(frozen=True, slots=True)
class CandidateFact:
    id: str
    subject_type: str
    subject_id: str
    field_name: str
    value: Any
    evidence_id: str

    def __post_init__(self) -> None:
        _require_text(self.id, "CandidateFact.id")
        _require_text(self.subject_type, "CandidateFact.subject_type")
        _require_text(self.subject_id, "CandidateFact.subject_id")
        _require_text(self.field_name, "CandidateFact.field_name")
        _require_text(self.evidence_id, "CandidateFact.evidence_id")


@dataclass(frozen=True, slots=True)
class CanonicalFact:
    id: str
    subject_type: str
    subject_id: str
    field_name: str
    value: Any
    supporting_candidate_fact_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text(self.id, "CanonicalFact.id")
        _require_text(self.subject_type, "CanonicalFact.subject_type")
        _require_text(self.subject_id, "CanonicalFact.subject_id")
        _require_text(self.field_name, "CanonicalFact.field_name")
        if not self.supporting_candidate_fact_ids:
            raise DomainInvariantError(
                "CanonicalFact requires at least one supporting CandidateFact"
            )
        for candidate_id in self.supporting_candidate_fact_ids:
            _require_text(candidate_id, "CanonicalFact.supporting_candidate_fact_ids")


@dataclass(frozen=True, slots=True)
class ContactPoint:
    id: str
    owner_type: str
    owner_id: str
    kind: str
    value: str
    evidence_id: str
    discovery_rule: str

    def __post_init__(self) -> None:
        _require_text(self.id, "ContactPoint.id")
        _require_text(self.owner_type, "ContactPoint.owner_type")
        _require_text(self.owner_id, "ContactPoint.owner_id")
        _require_text(self.kind, "ContactPoint.kind")
        _require_text(self.value, "ContactPoint.value")
        _require_text(self.evidence_id, "ContactPoint.evidence_id")
        _require_text(self.discovery_rule, "ContactPoint.discovery_rule")


@dataclass(frozen=True, slots=True)
class ContactValidation:
    id: str
    contact_point_id: str
    status: ContactValidationStatus
    rule: str
    evidence_id: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.id, "ContactValidation.id")
        _require_text(self.contact_point_id, "ContactValidation.contact_point_id")
        _require_text(self.rule, "ContactValidation.rule")


@dataclass(frozen=True, slots=True)
class Lead:
    id: str
    company_id: str
    qualification_state: str

    def __post_init__(self) -> None:
        _require_text(self.id, "Lead.id")
        _require_text(self.company_id, "Lead.company_id")
        _require_text(self.qualification_state, "Lead.qualification_state")
        if self.qualification_state == "ICP_UNDEFINED":
            raise DomainInvariantError("Lead cannot be created while ICP is undefined")
        if self.qualification_state != "QUALIFIED":
            raise DomainInvariantError(
                "Lead requires an explicit evaluated QUALIFIED state"
            )


@dataclass(frozen=True, slots=True)
class ReviewCase:
    id: str
    reason: ReviewReason
    subject_type: str
    subject_id: str
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_text(self.id, "ReviewCase.id")
        _require_text(self.subject_type, "ReviewCase.subject_type")
        _require_text(self.subject_id, "ReviewCase.subject_id")


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise DomainInvariantError(f"{field_name} must be non-empty text")
