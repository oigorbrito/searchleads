from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .enums import ConflictStatus, DecisionClass
from .provenance import utc_now


@dataclass(frozen=True, slots=True)
class CandidateFact:
    """A source-backed candidate value before canonicalization/fusion."""

    fact_id: str
    subject_id: str
    field_name: str
    raw_value: Any
    normalized_value: Any
    evidence_ids: tuple[str, ...]
    provenance_id: str
    confidence: float | None = None
    decision_class: DecisionClass = DecisionClass.UNKNOWN
    observed_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.fact_id.strip():
            raise ValueError("fact_id must not be blank")
        if not self.subject_id.strip():
            raise ValueError("subject_id must not be blank")
        if not self.field_name.strip():
            raise ValueError("field_name must not be blank")
        if not self.evidence_ids:
            raise ValueError("candidate fact requires evidence")
        if any(not item.strip() for item in self.evidence_ids):
            raise ValueError("evidence_ids must not contain blanks")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("evidence_ids must not contain duplicates")
        if not self.provenance_id.strip():
            raise ValueError("provenance_id must not be blank")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class CanonicalFact:
    """A selected/fused value with explicit links to candidate facts."""

    fact_id: str
    subject_id: str
    field_name: str
    value: Any
    candidate_fact_ids: tuple[str, ...]
    provenance_id: str
    resolution_method: str
    decision_class: DecisionClass = DecisionClass.UNKNOWN

    def __post_init__(self) -> None:
        if not self.fact_id.strip():
            raise ValueError("fact_id must not be blank")
        if not self.subject_id.strip():
            raise ValueError("subject_id must not be blank")
        if not self.field_name.strip():
            raise ValueError("field_name must not be blank")
        if not self.candidate_fact_ids:
            raise ValueError("canonical fact requires candidate facts")
        if any(not item.strip() for item in self.candidate_fact_ids):
            raise ValueError("candidate_fact_ids must not contain blanks")
        if len(set(self.candidate_fact_ids)) != len(self.candidate_fact_ids):
            raise ValueError("candidate_fact_ids must not contain duplicates")
        if not self.provenance_id.strip():
            raise ValueError("provenance_id must not be blank")
        if not self.resolution_method.strip():
            raise ValueError("resolution_method must not be blank")


@dataclass(frozen=True, slots=True)
class Conflict:
    """An explicit disagreement among candidate facts for the same field."""

    conflict_id: str
    subject_id: str
    field_name: str
    candidate_fact_ids: tuple[str, ...]
    status: ConflictStatus = ConflictStatus.OPEN
    selected_fact_id: str | None = None
    rationale: str | None = None

    def __post_init__(self) -> None:
        if not self.conflict_id.strip():
            raise ValueError("conflict_id must not be blank")
        if not self.subject_id.strip():
            raise ValueError("subject_id must not be blank")
        if not self.field_name.strip():
            raise ValueError("field_name must not be blank")
        if any(not item.strip() for item in self.candidate_fact_ids):
            raise ValueError("candidate_fact_ids must not contain blanks")
        if len(set(self.candidate_fact_ids)) < 2:
            raise ValueError("conflict requires at least two distinct candidate facts")
        if len(set(self.candidate_fact_ids)) != len(self.candidate_fact_ids):
            raise ValueError("candidate_fact_ids must not contain duplicates")
        if self.status is ConflictStatus.RESOLVED and not self.selected_fact_id:
            raise ValueError("resolved conflict requires selected_fact_id")
        if self.selected_fact_id and self.selected_fact_id not in self.candidate_fact_ids:
            raise ValueError("selected_fact_id must be one of candidate_fact_ids")
