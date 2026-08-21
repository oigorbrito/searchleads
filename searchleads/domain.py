"""Core domain model for LEADS_SCIENTIFIC_FOUNDATION_AND_DOMAIN_V1.

This module deliberately stops before acquisition, entity-resolution algorithms,
contact validation techniques, qualification scoring, persistence, or source
integrations. Those belong to later work units in the handoff.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _require_non_blank(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-blank string")
    return value


def _require_non_empty_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not values:
        raise ValueError(f"{field_name} must contain at least one value")
    for value in values:
        _require_non_blank(value, field_name)
    if len(set(values)) != len(values):
        raise ValueError(f"{field_name} must not contain duplicates")
    return values


def _require_confidence(value: float | None) -> float | None:
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")
    return value


class DecisionClass(str, Enum):
    EVIDENCE_BACKED = "EVIDENCE_BACKED"
    HYPOTHESIS = "HYPOTHESIS"
    ENGINEERING_CHOICE = "ENGINEERING_CHOICE"
    LOCALLY_VERIFIED = "LOCALLY_VERIFIED"
    UNKNOWN = "UNKNOWN"


class EntityType(str, Enum):
    COMPANY = "COMPANY"
    PERSON = "PERSON"
    CONTACT_POINT = "CONTACT_POINT"
    LEAD = "LEAD"


class SourceType(str, Enum):
    WEBSITE = "WEBSITE"
    DIRECTORY = "DIRECTORY"
    SEARCH_RESULT = "SEARCH_RESULT"
    DATASET = "DATASET"
    OFFICIAL_SOURCE = "OFFICIAL_SOURCE"
    SOCIAL_PROFILE = "SOCIAL_PROFILE"
    OTHER = "OTHER"


class ContactKind(str, Enum):
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    WHATSAPP = "WHATSAPP"
    CONTACT_FORM = "CONTACT_FORM"
    LINKEDIN = "LINKEDIN"
    INSTAGRAM = "INSTAGRAM"
    PROFESSIONAL_PROFILE = "PROFESSIONAL_PROFILE"
    OTHER = "OTHER"


class ContactStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    VALIDATED = "VALIDATED"
    STALE = "STALE"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


class LeadStatus(str, Enum):
    QUALIFIED = "QUALIFIED"
    NOT_QUALIFIED = "NOT_QUALIFIED"
    UNKNOWN = "UNKNOWN"


class ConflictStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


@dataclass(frozen=True, slots=True)
class EntityRef:
    entity_type: EntityType
    entity_id: str

    def __post_init__(self) -> None:
        _require_non_blank(self.entity_id, "entity_id")


@dataclass(frozen=True, slots=True)
class Source:
    """A retrievable origin from which evidence can be captured."""

    source_id: str
    source_type: SourceType
    locator: str
    label: str | None = None

    def __post_init__(self) -> None:
        _require_non_blank(self.source_id, "source_id")
        _require_non_blank(self.locator, "locator")
        if self.label is not None:
            _require_non_blank(self.label, "label")


@dataclass(frozen=True, slots=True)
class Evidence:
    """Immutable-ish observation captured from a source at a point in time.

    `payload` intentionally preserves the raw observation shape. It can be text,
    structured data, or metadata supplied by a future acquisition adapter.
    """

    evidence_id: str
    source_id: str
    retrieved_at: datetime
    payload: Any
    locator: str | None = None
    content_hash: str | None = None

    def __post_init__(self) -> None:
        _require_non_blank(self.evidence_id, "evidence_id")
        _require_non_blank(self.source_id, "source_id")
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
            raise ValueError("retrieved_at must be timezone-aware")
        if self.locator is not None:
            _require_non_blank(self.locator, "locator")
        if self.content_hash is not None:
            _require_non_blank(self.content_hash, "content_hash")


@dataclass(frozen=True, slots=True)
class Provenance:
    """Per-fact derivation metadata, inspired by W3C PROV concepts."""

    evidence_ids: tuple[str, ...]
    activity: str
    generated_at: datetime = field(default_factory=utc_now)
    agent: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_tuple(self.evidence_ids, "evidence_ids")
        _require_non_blank(self.activity, "activity")
        if self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")
        if self.agent is not None:
            _require_non_blank(self.agent, "agent")


@dataclass(frozen=True, slots=True)
class Company:
    """A discovered business entity, not automatically a lead."""

    company_id: str
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_blank(self.company_id, "company_id")


@dataclass(frozen=True, slots=True)
class Person:
    """A person identity shell; names/attributes should be evidence-backed facts."""

    person_id: str
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_blank(self.person_id, "person_id")


@dataclass(frozen=True, slots=True)
class ProfessionalRole:
    """Evidence-backed relationship between a person and a company."""

    role_id: str
    person_id: str
    company_id: str
    title: str
    provenance: Provenance

    def __post_init__(self) -> None:
        _require_non_blank(self.role_id, "role_id")
        _require_non_blank(self.person_id, "person_id")
        _require_non_blank(self.company_id, "company_id")
        _require_non_blank(self.title, "title")


@dataclass(frozen=True, slots=True)
class ContactPoint:
    """A discovered professional contact point with its own evidence state."""

    contact_id: str
    owner: EntityRef
    kind: ContactKind
    value: str
    provenance: Provenance
    status: ContactStatus = ContactStatus.DISCOVERED

    def __post_init__(self) -> None:
        _require_non_blank(self.contact_id, "contact_id")
        _require_non_blank(self.value, "value")
        if self.owner.entity_type not in {EntityType.COMPANY, EntityType.PERSON}:
            raise ValueError("contact owner must be a COMPANY or PERSON")


@dataclass(frozen=True, slots=True)
class CandidateFact:
    """A source-derived assertion that has not yet become canonical."""

    candidate_fact_id: str
    subject: EntityRef
    predicate: str
    raw_value: Any
    provenance: Provenance
    normalized_value: Any | None = None
    normalization_rule: str | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        _require_non_blank(self.candidate_fact_id, "candidate_fact_id")
        _require_non_blank(self.predicate, "predicate")
        if self.normalization_rule is not None:
            _require_non_blank(self.normalization_rule, "normalization_rule")
        _require_confidence(self.confidence)


@dataclass(frozen=True, slots=True)
class CanonicalFact:
    """A selected/fused fact backed by one or more candidate facts."""

    canonical_fact_id: str
    subject: EntityRef
    predicate: str
    value: Any
    candidate_fact_ids: tuple[str, ...]
    provenance: Provenance
    confidence: float | None = None

    def __post_init__(self) -> None:
        _require_non_blank(self.canonical_fact_id, "canonical_fact_id")
        _require_non_blank(self.predicate, "predicate")
        _require_non_empty_tuple(self.candidate_fact_ids, "candidate_fact_ids")
        _require_confidence(self.confidence)


@dataclass(frozen=True, slots=True)
class Conflict:
    """Competing candidate facts for the same subject/predicate."""

    conflict_id: str
    subject: EntityRef
    predicate: str
    candidate_fact_ids: tuple[str, ...]
    status: ConflictStatus = ConflictStatus.OPEN
    resolved_canonical_fact_id: str | None = None
    resolution_note: str | None = None

    def __post_init__(self) -> None:
        _require_non_blank(self.conflict_id, "conflict_id")
        _require_non_blank(self.predicate, "predicate")
        _require_non_empty_tuple(self.candidate_fact_ids, "candidate_fact_ids")
        if len(self.candidate_fact_ids) < 2:
            raise ValueError("a conflict requires at least two candidate facts")
        if self.status is ConflictStatus.OPEN and self.resolved_canonical_fact_id is not None:
            raise ValueError("open conflict cannot point to a resolved canonical fact")
        if self.status is ConflictStatus.RESOLVED and self.resolved_canonical_fact_id is None:
            raise ValueError("resolved conflict requires resolved_canonical_fact_id")
        if self.resolution_note is not None:
            _require_non_blank(self.resolution_note, "resolution_note")


@dataclass(frozen=True, slots=True)
class Lead:
    """Commercial pipeline entity kept distinct from Company.

    The model can represent qualification state and reasons, but this work unit
    does not define ICP criteria, weights, or a qualification algorithm.
    """

    lead_id: str
    company_id: str
    status: LeadStatus
    reasons: tuple[str, ...] = ()
    qualification_facts: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_blank(self.lead_id, "lead_id")
        _require_non_blank(self.company_id, "company_id")
        for reason in self.reasons:
            _require_non_blank(reason, "reasons")
        for fact_id in self.qualification_facts:
            _require_non_blank(fact_id, "qualification_facts")
        if self.status is LeadStatus.QUALIFIED and not self.reasons:
            raise ValueError("qualified lead requires at least one explicit reason")
