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
from .governance_evidence_review import (
    EvidenceReviewDecision,
    EvidenceReviewRepository,
)
from .governance_evidence_review_status import (
    ConsolidatedEvidenceReviewState,
    consolidate_evidence_reviews,
)


class EvidenceReviewResolutionState(StrEnum):
    NO_RESOLUTION = "NO_RESOLUTION"
    RESOLVED = "RESOLVED"
    RESOLUTION_CONFLICT = "RESOLUTION_CONFLICT"
    STALE_RESOLUTION = "STALE_RESOLUTION"


class EvidenceReviewResolutionError(RuntimeError):
    pass


class EvidenceReviewResolutionConflictError(EvidenceReviewResolutionError):
    pass


class EvidenceReviewResolutionIntegrityError(EvidenceReviewResolutionError):
    pass


@dataclass(frozen=True, slots=True)
class EvidenceReviewResolutionRecord:
    resolution_id: str
    audit_id: str
    bundle_sha256: str
    review_ids: tuple[str, ...]
    review_set_sha256: str
    resolver_reference: str
    decision: EvidenceReviewDecision
    resolved_at: datetime
    evidence_refs: tuple[str, ...]
    note: str | None = None
    send_authorized: bool = False
    resolution_is_campaign_authorization: bool = False

    def __post_init__(self) -> None:
        for field, value in (
            ("resolution_id", self.resolution_id),
            ("audit_id", self.audit_id),
            ("resolver_reference", self.resolver_reference),
        ):
            if not value.strip():
                raise ValueError(f"{field} must not be blank")
        if len(self.bundle_sha256) != 64 or len(self.review_set_sha256) != 64:
            raise ValueError("bundle_sha256 and review_set_sha256 must be SHA-256 hex digests")
        if not self.review_ids or len(set(self.review_ids)) != len(self.review_ids):
            raise ValueError("review_ids must be a non-empty unique set")
        if tuple(sorted(self.review_ids)) != self.review_ids:
            raise ValueError("review_ids must be sorted deterministically")
        if self.resolved_at.tzinfo is None:
            raise ValueError("resolved_at must be timezone-aware")
        if not self.evidence_refs or any(not ref.strip() for ref in self.evidence_refs):
            raise ValueError("evidence_refs must contain non-blank references")
        if self.note is not None and not self.note.strip():
            raise ValueError("note must not be blank when provided")
        if self.send_authorized or self.resolution_is_campaign_authorization:
            raise ValueError("evidence review resolution cannot authorize send or a campaign")


@dataclass(frozen=True, slots=True)
class EvidenceReviewResolutionStatus:
    audit_id: str
    bundle_sha256: str
    current_review_ids: tuple[str, ...]
    current_review_set_sha256: str
    state: EvidenceReviewResolutionState
    effective_decision: EvidenceReviewDecision | None
    applicable_resolution_ids: tuple[str, ...]
    stale_resolution_ids: tuple[str, ...]
    conflicting_decisions: tuple[EvidenceReviewDecision, ...]
    latest_resolution_id: str | None
    send_authorized: bool = False
    resolution_is_campaign_authorization: bool = False


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def review_set_sha256(review_ids: tuple[str, ...]) -> str:
    return _sha256(_canonical_json(list(sorted(review_ids))))


def evidence_review_resolution_to_mapping(record: EvidenceReviewResolutionRecord) -> dict[str, Any]:
    return {
        "resolution_id": record.resolution_id,
        "audit_id": record.audit_id,
        "bundle_sha256": record.bundle_sha256,
        "review_ids": list(record.review_ids),
        "review_set_sha256": record.review_set_sha256,
        "resolver_reference": record.resolver_reference,
        "decision": record.decision.value,
        "resolved_at": record.resolved_at.isoformat(),
        "evidence_refs": list(record.evidence_refs),
        "note": record.note,
        "send_authorized": False,
        "resolution_is_campaign_authorization": False,
    }


def evidence_review_resolution_from_mapping(payload: Mapping[str, Any]) -> EvidenceReviewResolutionRecord:
    def text(field: str) -> str:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-blank string")
        return value.strip()

    raw_review_ids = payload.get("review_ids")
    if not isinstance(raw_review_ids, list) or not raw_review_ids or any(not isinstance(v, str) or not v.strip() for v in raw_review_ids):
        raise ValueError("review_ids must be a non-empty list of strings")
    review_ids = tuple(sorted(v.strip() for v in raw_review_ids))
    if len(set(review_ids)) != len(review_ids):
        raise ValueError("review_ids must not contain duplicates")
    raw_refs = payload.get("evidence_refs")
    if not isinstance(raw_refs, list) or not raw_refs or any(not isinstance(v, str) or not v.strip() for v in raw_refs):
        raise ValueError("evidence_refs must be a non-empty list of strings")
    resolved_at = datetime.fromisoformat(text("resolved_at").replace("Z", "+00:00"))
    note = payload.get("note")
    if note is not None and (not isinstance(note, str) or not note.strip()):
        raise ValueError("note must be non-blank when provided")
    if payload.get("send_authorized", False) is not False or payload.get("resolution_is_campaign_authorization", False) is not False:
        raise ValueError("resolution must not authorize send or campaign")
    return EvidenceReviewResolutionRecord(
        resolution_id=text("resolution_id"),
        audit_id=text("audit_id"),
        bundle_sha256=text("bundle_sha256"),
        review_ids=review_ids,
        review_set_sha256=text("review_set_sha256"),
        resolver_reference=text("resolver_reference"),
        decision=EvidenceReviewDecision(text("decision")),
        resolved_at=resolved_at,
        evidence_refs=tuple(v.strip() for v in raw_refs),
        note=note.strip() if isinstance(note, str) else None,
    )


class EvidenceReviewResolutionRepository:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("""CREATE TABLE IF NOT EXISTS governance_evidence_review_resolutions (
            resolution_id TEXT PRIMARY KEY,
            audit_id TEXT NOT NULL,
            bundle_sha256 TEXT NOT NULL,
            review_set_sha256 TEXT NOT NULL,
            resolved_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        self._connection.execute("CREATE INDEX IF NOT EXISTS idx_review_resolution_bundle ON governance_evidence_review_resolutions(audit_id, bundle_sha256, resolved_at)")
        self._connection.commit()

    def __enter__(self) -> "EvidenceReviewResolutionRepository":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def save(self, record: EvidenceReviewResolutionRecord) -> bool:
        payload_json = _canonical_json(evidence_review_resolution_to_mapping(record))
        digest = _sha256(payload_json)
        row = self._connection.execute("SELECT payload_json, payload_sha256 FROM governance_evidence_review_resolutions WHERE resolution_id = ?", (record.resolution_id,)).fetchone()
        if row is not None:
            if _sha256(row["payload_json"]) != row["payload_sha256"]:
                raise EvidenceReviewResolutionIntegrityError("stored resolution digest mismatch")
            if row["payload_json"] == payload_json:
                return False
            raise EvidenceReviewResolutionConflictError(f"resolution_id {record.resolution_id!r} already exists with different content")
        self._connection.execute("INSERT INTO governance_evidence_review_resolutions(resolution_id,audit_id,bundle_sha256,review_set_sha256,resolved_at,payload_json,payload_sha256) VALUES (?,?,?,?,?,?,?)", (record.resolution_id, record.audit_id, record.bundle_sha256, record.review_set_sha256, record.resolved_at.isoformat(), payload_json, digest))
        self._connection.commit()
        return True

    def load(self, resolution_id: str) -> EvidenceReviewResolutionRecord:
        row = self._connection.execute("SELECT payload_json, payload_sha256 FROM governance_evidence_review_resolutions WHERE resolution_id = ?", (resolution_id,)).fetchone()
        if row is None:
            raise KeyError(resolution_id)
        if _sha256(row["payload_json"]) != row["payload_sha256"]:
            raise EvidenceReviewResolutionIntegrityError("stored resolution digest mismatch")
        return evidence_review_resolution_from_mapping(json.loads(row["payload_json"]))

    def list_for_bundle(self, *, audit_id: str, bundle_sha256: str) -> tuple[EvidenceReviewResolutionRecord, ...]:
        rows = self._connection.execute("SELECT resolution_id FROM governance_evidence_review_resolutions WHERE audit_id = ? AND bundle_sha256 = ? ORDER BY resolved_at ASC, resolution_id ASC", (audit_id, bundle_sha256)).fetchall()
        return tuple(self.load(row["resolution_id"]) for row in rows)


def process_evidence_review_resolution(*, review_repository: EvidenceReviewRepository, resolution_repository: EvidenceReviewResolutionRepository, bundle: Mapping[str, Any], resolution_payload: Mapping[str, Any]) -> tuple[EvidenceReviewResolutionRecord, bool]:
    verify_governance_evidence_bundle(dict(bundle))
    consolidated = consolidate_evidence_reviews(repository=review_repository, bundle=bundle)
    if consolidated.state is not ConsolidatedEvidenceReviewState.CONFLICT:
        raise ValueError("resolution may only be recorded for a current CONFLICT review state")
    record = evidence_review_resolution_from_mapping(resolution_payload)
    if record.audit_id != consolidated.audit_id or record.bundle_sha256 != consolidated.bundle_sha256:
        raise ValueError("resolution does not match verified bundle")
    current_ids = tuple(sorted(review.review_id for review in consolidated.reviews))
    if record.review_ids != current_ids:
        raise ValueError("resolution review_ids do not match the exact current review set")
    expected_set_digest = review_set_sha256(current_ids)
    if record.review_set_sha256 != expected_set_digest:
        raise ValueError("resolution review_set_sha256 does not match the exact current review set")
    return record, resolution_repository.save(record)


def build_evidence_review_resolution_status(*, review_repository: EvidenceReviewRepository, resolution_repository: EvidenceReviewResolutionRepository, bundle: Mapping[str, Any]) -> EvidenceReviewResolutionStatus:
    verify_governance_evidence_bundle(dict(bundle))
    consolidated = consolidate_evidence_reviews(repository=review_repository, bundle=bundle)
    current_ids = tuple(sorted(review.review_id for review in consolidated.reviews))
    current_digest = review_set_sha256(current_ids)
    records = resolution_repository.list_for_bundle(audit_id=consolidated.audit_id, bundle_sha256=consolidated.bundle_sha256)
    applicable = tuple(record for record in records if record.review_set_sha256 == current_digest and record.review_ids == current_ids)
    stale = tuple(record for record in records if record not in applicable)
    latest = max(records, key=lambda record: (record.resolved_at, record.resolution_id)).resolution_id if records else None
    decisions = tuple(sorted({record.decision for record in applicable}, key=lambda decision: decision.value))
    if not records:
        state, effective = EvidenceReviewResolutionState.NO_RESOLUTION, None
    elif not applicable:
        state, effective = EvidenceReviewResolutionState.STALE_RESOLUTION, None
    elif len(decisions) == 1:
        state, effective = EvidenceReviewResolutionState.RESOLVED, decisions[0]
    else:
        state, effective = EvidenceReviewResolutionState.RESOLUTION_CONFLICT, None
    return EvidenceReviewResolutionStatus(
        audit_id=consolidated.audit_id,
        bundle_sha256=consolidated.bundle_sha256,
        current_review_ids=current_ids,
        current_review_set_sha256=current_digest,
        state=state,
        effective_decision=effective,
        applicable_resolution_ids=tuple(record.resolution_id for record in applicable),
        stale_resolution_ids=tuple(record.resolution_id for record in stale),
        conflicting_decisions=decisions if len(decisions) > 1 else (),
        latest_resolution_id=latest,
    )


def evidence_review_resolution_status_to_mapping(status: EvidenceReviewResolutionStatus) -> dict[str, Any]:
    return {
        "audit_id": status.audit_id,
        "bundle_sha256": status.bundle_sha256,
        "current_review_ids": list(status.current_review_ids),
        "current_review_set_sha256": status.current_review_set_sha256,
        "state": status.state.value,
        "effective_decision": status.effective_decision.value if status.effective_decision else None,
        "applicable_resolution_ids": list(status.applicable_resolution_ids),
        "stale_resolution_ids": list(status.stale_resolution_ids),
        "conflicting_decisions": [decision.value for decision in status.conflicting_decisions],
        "latest_resolution_id": status.latest_resolution_id,
        "send_authorized": False,
        "resolution_is_campaign_authorization": False,
        "changes_auth_campaign_001": False,
        "changes_preflight": False,
        "changes_pilot_release": False,
        "changes_legal_signoff": False,
        "changes_professional_verification": False,
        "changes_source_freshness": False,
    }


__all__ = [
    "EvidenceReviewResolutionConflictError",
    "EvidenceReviewResolutionIntegrityError",
    "EvidenceReviewResolutionRecord",
    "EvidenceReviewResolutionRepository",
    "EvidenceReviewResolutionState",
    "EvidenceReviewResolutionStatus",
    "build_evidence_review_resolution_status",
    "evidence_review_resolution_from_mapping",
    "evidence_review_resolution_status_to_mapping",
    "evidence_review_resolution_to_mapping",
    "process_evidence_review_resolution",
    "review_set_sha256",
]
