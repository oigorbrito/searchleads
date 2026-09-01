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
    """Legacy person snapshot preserved for compatibility during migration."""

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
class PersonIdentity:
    """Stable person identity independent from any company relationship."""

    person_id: str

    def __post_init__(self) -> None:
        if not self.person_id.strip():
            raise ValueError("person_id must not be blank")


@dataclass(frozen=True, slots=True)
class PersonCompanyRelationship:
    """First-class relationship between a person and a company."""

    relationship_id: str
    person_id: str
    company_id: str
    evidence_ids: tuple[str, ...]
    role_title: str | None = None
    relationship_type: str = "UNKNOWN"
    status: str = "UNKNOWN"
    started_at: datetime | None = None
    ended_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.relationship_id.strip():
            raise ValueError("relationship_id must not be blank")
        if not self.person_id.strip():
            raise ValueError("person_id must not be blank")
        if not self.company_id.strip():
            raise ValueError("company_id must not be blank")
        if not self.evidence_ids:
            raise ValueError("person-company relationship requires evidence")
        if any(not item.strip() for item in self.evidence_ids):
            raise ValueError("evidence_ids must not contain blanks")
        if self.started_at is not None and self.started_at.tzinfo is None:
            raise ValueError("started_at must be timezone-aware")
        if self.ended_at is not None and self.ended_at.tzinfo is None:
            raise ValueError("ended_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ProfessionalRegistration:
    """Person-scoped professional registration or credential."""

    registration_id: str
    person_id: str
    authority: str
    number: str
    status: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.registration_id.strip():
            raise ValueError("registration_id must not be blank")
        if not self.person_id.strip():
            raise ValueError("person_id must not be blank")
        if not self.authority.strip():
            raise ValueError("authority must not be blank")
        if not self.number.strip():
            raise ValueError("number must not be blank")
        if not self.status.strip():
            raise ValueError("status must not be blank")
        if not self.evidence_ids:
            raise ValueError("professional registration requires evidence")
        if any(not item.strip() for item in self.evidence_ids):
            raise ValueError("evidence_ids must not contain blanks")


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
        if self.status is ContactStatus.DISCOVERED and (
            self.validation_evidence_ids or self.validated_at is not None
        ):
            raise ValueError("DISCOVERED contact cannot carry validation metadata")
        if self.validated_at is not None and self.validated_at.tzinfo is None:
            raise ValueError("validated_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class RelationshipContactLink:
    """Explicit relationship-scoped contact association."""

    link_id: str
    relationship_id: str
    contact_id: str
    evidence_ids: tuple[str, ...]
    status: str = "LINKED"

    def __post_init__(self) -> None:
        if not self.link_id.strip():
            raise ValueError("link_id must not be blank")
        if not self.relationship_id.strip():
            raise ValueError("relationship_id must not be blank")
        if not self.contact_id.strip():
            raise ValueError("contact_id must not be blank")
        if not self.evidence_ids:
            raise ValueError("relationship contact link requires evidence")
        if any(not item.strip() for item in self.evidence_ids):
            raise ValueError("evidence_ids must not contain blanks")


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
        expected_status = {
            LeadStage.CANDIDATE: QualificationStatus.UNKNOWN,
            LeadStage.REVIEW: QualificationStatus.UNKNOWN,
            LeadStage.QUALIFIED: QualificationStatus.QUALIFIED,
            LeadStage.DISQUALIFIED: QualificationStatus.NOT_QUALIFIED,
        }[self.stage]
        if self.qualification_status is not expected_status:
            raise ValueError(
                f"{self.stage.value} stage requires {expected_status.value} qualification_status"
            )


@dataclass(frozen=True, slots=True)
class Statement:
    """Derived semantic statement distinct from raw Evidence."""

    statement_id: str
    subject_id: str
    field_name: str
    value: object
    provenance_id: str
    resolution_method: str

    def __post_init__(self) -> None:
        if not self.statement_id.strip():
            raise ValueError("statement_id must not be blank")
        if not self.subject_id.strip():
            raise ValueError("subject_id must not be blank")
        if not self.field_name.strip():
            raise ValueError("field_name must not be blank")
        if not self.provenance_id.strip():
            raise ValueError("provenance_id must not be blank")
        if not self.resolution_method.strip():
            raise ValueError("resolution_method must not be blank")


@dataclass(frozen=True, slots=True)
class StatementEvidenceLink:
    """Many-to-many bridge from a statement to the evidence that supports it."""

    link_id: str
    statement_id: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.link_id.strip():
            raise ValueError("link_id must not be blank")
        if not self.statement_id.strip():
            raise ValueError("statement_id must not be blank")
        if not self.evidence_ids:
            raise ValueError("statement evidence link requires evidence")
        if any(not item.strip() for item in self.evidence_ids):
            raise ValueError("evidence_ids must not contain blanks")


@dataclass(frozen=True, slots=True)
class QualificationDecision:
    """Explicit commercial qualification decision."""

    decision_id: str
    lead_id: str
    qualification_status: QualificationStatus
    reasons: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    decided_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.decision_id.strip():
            raise ValueError("decision_id must not be blank")
        if not self.lead_id.strip():
            raise ValueError("lead_id must not be blank")
        if not isinstance(self.qualification_status, QualificationStatus):
            raise ValueError("qualification_status must be a QualificationStatus")
        if any(not item.strip() for item in self.reasons):
            raise ValueError("reasons must not contain blanks")
        if any(not item.strip() for item in self.evidence_ids):
            raise ValueError("evidence_ids must not contain blanks")
        if self.decided_at.tzinfo is None:
            raise ValueError("decided_at must be timezone-aware")
