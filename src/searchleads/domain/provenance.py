from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class Source:
    """A stable origin such as a website, directory, registry, or dataset."""

    source_id: str
    source_type: str
    locator: str
    name: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id must not be blank")
        if not self.source_type.strip():
            raise ValueError("source_type must not be blank")
        if not self.locator.strip():
            raise ValueError("locator must not be blank")


@dataclass(frozen=True, slots=True)
class Evidence:
    """A captured observation from a source at a point in time."""

    evidence_id: str
    source_id: str
    locator: str
    captured_at: datetime = field(default_factory=utc_now)
    raw_payload: str | None = None
    content_digest: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("evidence_id must not be blank")
        if not self.source_id.strip():
            raise ValueError("source_id must not be blank")
        if not self.locator.strip():
            raise ValueError("locator must not be blank")
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class Provenance:
    """Minimal fact-level derivation record inspired by W3C PROV concepts."""

    provenance_id: str
    subject_id: str
    field_name: str
    evidence_ids: tuple[str, ...]
    activity: str
    generated_at: datetime = field(default_factory=utc_now)
    agent: str | None = None
    derived_from_fact_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.provenance_id.strip():
            raise ValueError("provenance_id must not be blank")
        if not self.subject_id.strip():
            raise ValueError("subject_id must not be blank")
        if not self.field_name.strip():
            raise ValueError("field_name must not be blank")
        if not self.evidence_ids:
            raise ValueError("provenance requires at least one evidence_id")
        if any(not item.strip() for item in self.evidence_ids):
            raise ValueError("evidence_ids must not contain blanks")
        if not self.activity.strip():
            raise ValueError("activity must not be blank")
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware")
