from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from .governance_evidence_bundle import verify_governance_evidence_bundle


class EvidenceReviewDecision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MORE_REVIEW_REQUIRED = "MORE_REVIEW_REQUIRED"


class EvidenceReviewError(RuntimeError):
    """Base class for evidence-review failures."""


class EvidenceReviewConflictError(EvidenceReviewError):
    """Raised when an immutable review ID is reused with different content."""


class EvidenceReviewIntegrityError(EvidenceReviewError):
    """Raised when persisted review payload integrity does not verify."""


@dataclass(frozen=True, slots=True)
class EvidenceReviewRecord:
    review_id: str
    audit_id: str
    bundle_sha256: str
    reviewer_reference: str
    decision: EvidenceReviewDecision
    reviewed_at: datetime
    evidence_refs: tuple[str, ...]
    note: str | None = None
    send_authorized: bool = False

    def __post_init__(self) -> None:
        for field, value in (
            ("review_id", self.review_id),
            ("audit_id", self.audit_id),
            ("reviewer_reference", self.reviewer_reference),
        ):
            if not value.strip():
                raise ValueError(f"{field} must not be blank")
        if len(self.bundle_sha256) != 64:
            raise ValueError("bundle_sha256 must be a SHA-256 hex digest")
        if self.reviewed_at.tzinfo is None:
            raise ValueError("reviewed_at must be timezone-aware")
        if not self.evidence_refs or any(not ref.strip() for ref in self.evidence_refs):
            raise ValueError("evidence_refs must contain non-blank references")
        if self.note is not None and not self.note.strip():
            raise ValueError("note must not be blank when provided")
        if self.send_authorized:
            raise ValueError("evidence review cannot authorize send")


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def evidence_review_to_mapping(record: EvidenceReviewRecord) -> dict[str, Any]:
    return {
        "review_id": record.review_id,
        "audit_id": record.audit_id,
        "bundle_sha256": record.bundle_sha256,
        "reviewer_reference": record.reviewer_reference,
        "decision": record.decision.value,
        "reviewed_at": record.reviewed_at.isoformat(),
        "evidence_refs": list(record.evidence_refs),
        "note": record.note,
        "send_authorized": False,
        "review_is_campaign_authorization": False,
    }


def evidence_review_from_mapping(payload: Mapping[str, Any]) -> EvidenceReviewRecord:
    if not isinstance(payload, Mapping):
        raise ValueError("review payload must be an object")

    def required_text(field: str) -> str:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-blank string")
        return value.strip()

    raw_refs = payload.get("evidence_refs")
    if not isinstance(raw_refs, list) or not raw_refs or any(
        not isinstance(item, str) or not item.strip() for item in raw_refs
    ):
        raise ValueError("evidence_refs must be a non-empty list of non-blank strings")
    raw_reviewed_at = required_text("reviewed_at").replace("Z", "+00:00")
    try:
        reviewed_at = datetime.fromisoformat(raw_reviewed_at)
    except ValueError as exc:
        raise ValueError("reviewed_at must be valid ISO-8601") from exc
    note = payload.get("note")
    if note is not None and (not isinstance(note, str) or not note.strip()):
        raise ValueError("note must be a non-blank string when provided")
    if payload.get("send_authorized", False) is not False:
        raise ValueError("evidence review must not authorize send")
    if payload.get("review_is_campaign_authorization", False) is not False:
        raise ValueError("evidence review must not be campaign authorization")
    try:
        decision = EvidenceReviewDecision(required_text("decision"))
    except ValueError as exc:
        raise ValueError("decision must be APPROVED, REJECTED, or MORE_REVIEW_REQUIRED") from exc
    return EvidenceReviewRecord(
        review_id=required_text("review_id"),
        audit_id=required_text("audit_id"),
        bundle_sha256=required_text("bundle_sha256"),
        reviewer_reference=required_text("reviewer_reference"),
        decision=decision,
        reviewed_at=reviewed_at,
        evidence_refs=tuple(item.strip() for item in raw_refs),
        note=note.strip() if isinstance(note, str) else None,
        send_authorized=False,
    )


def bind_review_to_bundle(
    *,
    bundle: Mapping[str, Any],
    review: EvidenceReviewRecord,
) -> None:
    """Verify the reviewed artifact and enforce exact cryptographic binding."""
    verify_governance_evidence_bundle(dict(bundle))
    if bundle.get("audit_id") != review.audit_id:
        raise ValueError("review audit_id does not match verified bundle")
    if bundle.get("bundle_sha256") != review.bundle_sha256:
        raise ValueError("review bundle_sha256 does not match verified bundle")


class EvidenceReviewRepository:
    """Append-only store for human reviews of exact evidence bundles."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            """CREATE TABLE IF NOT EXISTS governance_evidence_reviews (
                review_id TEXT PRIMARY KEY,
                audit_id TEXT NOT NULL,
                bundle_sha256 TEXT NOT NULL,
                reviewed_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL,
                recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_governance_evidence_reviews_bundle ON governance_evidence_reviews(audit_id, bundle_sha256, reviewed_at)"
        )
        self._connection.commit()

    def __enter__(self) -> "EvidenceReviewRepository":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def save(self, record: EvidenceReviewRecord) -> bool:
        payload_json = _canonical_json(evidence_review_to_mapping(record))
        payload_sha256 = _sha256(payload_json)
        existing = self._connection.execute(
            "SELECT payload_json, payload_sha256 FROM governance_evidence_reviews WHERE review_id = ?",
            (record.review_id,),
        ).fetchone()
        if existing is not None:
            if _sha256(existing["payload_json"]) != existing["payload_sha256"]:
                raise EvidenceReviewIntegrityError("stored evidence review digest mismatch")
            if existing["payload_json"] == payload_json:
                return False
            raise EvidenceReviewConflictError(f"review_id {record.review_id!r} already exists with different content")
        self._connection.execute(
            "INSERT INTO governance_evidence_reviews(review_id, audit_id, bundle_sha256, reviewed_at, payload_json, payload_sha256) VALUES (?, ?, ?, ?, ?, ?)",
            (
                record.review_id,
                record.audit_id,
                record.bundle_sha256,
                record.reviewed_at.isoformat(),
                payload_json,
                payload_sha256,
            ),
        )
        self._connection.commit()
        return True

    def load(self, review_id: str) -> EvidenceReviewRecord:
        row = self._connection.execute(
            "SELECT payload_json, payload_sha256 FROM governance_evidence_reviews WHERE review_id = ?",
            (review_id,),
        ).fetchone()
        if row is None:
            raise KeyError(review_id)
        if _sha256(row["payload_json"]) != row["payload_sha256"]:
            raise EvidenceReviewIntegrityError("stored evidence review digest mismatch")
        payload = json.loads(row["payload_json"])
        return evidence_review_from_mapping(payload)

    def list_for_bundle(self, *, audit_id: str, bundle_sha256: str) -> tuple[EvidenceReviewRecord, ...]:
        rows = self._connection.execute(
            "SELECT review_id FROM governance_evidence_reviews WHERE audit_id = ? AND bundle_sha256 = ? ORDER BY reviewed_at ASC, review_id ASC",
            (audit_id, bundle_sha256),
        ).fetchall()
        return tuple(self.load(row["review_id"]) for row in rows)


def process_evidence_review(
    *,
    repository: EvidenceReviewRepository,
    bundle: Mapping[str, Any],
    review_payload: Mapping[str, Any],
) -> tuple[EvidenceReviewRecord, bool]:
    """Validate bundle + review binding, then persist the immutable human review."""
    review = evidence_review_from_mapping(review_payload)
    bind_review_to_bundle(bundle=bundle, review=review)
    inserted = repository.save(review)
    return review, inserted


__all__ = [
    "EvidenceReviewConflictError",
    "EvidenceReviewDecision",
    "EvidenceReviewError",
    "EvidenceReviewIntegrityError",
    "EvidenceReviewRecord",
    "EvidenceReviewRepository",
    "bind_review_to_bundle",
    "evidence_review_from_mapping",
    "evidence_review_to_mapping",
    "process_evidence_review",
]
