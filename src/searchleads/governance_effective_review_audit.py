from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .governance_effective_review_status import (
    EffectiveEvidenceReviewStatus,
    effective_evidence_review_status_to_mapping,
)


class EffectiveReviewAuditError(RuntimeError):
    pass


class EffectiveReviewAuditConflictError(EffectiveReviewAuditError):
    pass


class EffectiveReviewAuditIntegrityError(EffectiveReviewAuditError):
    pass


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class EffectiveReviewAuditEntry:
    audit_entry_id: str
    sequence: int
    audit_id: str
    bundle_sha256: str
    status_sha256: str
    previous_entry_hash: str | None
    entry_hash: str
    status: Mapping[str, Any]


def _entry_hash_payload(*, audit_entry_id: str, sequence: int, audit_id: str, bundle_sha256: str, status_sha256: str, previous_entry_hash: str | None) -> dict[str, Any]:
    return {
        "audit_entry_id": audit_entry_id,
        "sequence": sequence,
        "audit_id": audit_id,
        "bundle_sha256": bundle_sha256,
        "status_sha256": status_sha256,
        "previous_entry_hash": previous_entry_hash,
    }


class EffectiveReviewAuditRepository:
    """Append-only tamper-evident audit trail for effective review status snapshots."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("""CREATE TABLE IF NOT EXISTS governance_effective_review_audit (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_entry_id TEXT NOT NULL UNIQUE,
            audit_id TEXT NOT NULL,
            bundle_sha256 TEXT NOT NULL,
            status_json TEXT NOT NULL,
            status_sha256 TEXT NOT NULL,
            previous_entry_hash TEXT,
            entry_hash TEXT NOT NULL
        )""")
        self._connection.commit()

    def __enter__(self) -> "EffectiveReviewAuditRepository":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def append_status(self, *, audit_entry_id: str, status: EffectiveEvidenceReviewStatus) -> tuple[EffectiveReviewAuditEntry, bool]:
        if not audit_entry_id.strip():
            raise ValueError("audit_entry_id must not be blank")
        status_mapping = effective_evidence_review_status_to_mapping(status)
        status_json = _canonical_json(status_mapping)
        status_sha256 = _sha256(status_json)
        existing = self._connection.execute(
            "SELECT * FROM governance_effective_review_audit WHERE audit_entry_id = ?",
            (audit_entry_id,),
        ).fetchone()
        if existing is not None:
            entry = self._row_to_entry(existing)
            self._verify_entry(entry)
            if _canonical_json(entry.status) == status_json:
                return entry, False
            raise EffectiveReviewAuditConflictError(f"audit_entry_id {audit_entry_id!r} already exists with different content")

        predecessor = self._connection.execute(
            "SELECT entry_hash FROM governance_effective_review_audit ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_entry_hash = predecessor["entry_hash"] if predecessor is not None else None
        next_sequence = self._connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 AS next_sequence FROM governance_effective_review_audit"
        ).fetchone()["next_sequence"]
        payload = _entry_hash_payload(
            audit_entry_id=audit_entry_id,
            sequence=next_sequence,
            audit_id=status.audit_id,
            bundle_sha256=status.bundle_sha256,
            status_sha256=status_sha256,
            previous_entry_hash=previous_entry_hash,
        )
        entry_hash = _sha256(_canonical_json(payload))
        self._connection.execute(
            "INSERT INTO governance_effective_review_audit(sequence,audit_entry_id,audit_id,bundle_sha256,status_json,status_sha256,previous_entry_hash,entry_hash) VALUES (?,?,?,?,?,?,?,?)",
            (next_sequence, audit_entry_id, status.audit_id, status.bundle_sha256, status_json, status_sha256, previous_entry_hash, entry_hash),
        )
        self._connection.commit()
        return self.load(audit_entry_id), True

    def _row_to_entry(self, row: sqlite3.Row) -> EffectiveReviewAuditEntry:
        try:
            status = json.loads(row["status_json"])
        except json.JSONDecodeError as exc:
            raise EffectiveReviewAuditIntegrityError("stored status JSON is invalid") from exc
        return EffectiveReviewAuditEntry(
            audit_entry_id=row["audit_entry_id"],
            sequence=row["sequence"],
            audit_id=row["audit_id"],
            bundle_sha256=row["bundle_sha256"],
            status_sha256=row["status_sha256"],
            previous_entry_hash=row["previous_entry_hash"],
            entry_hash=row["entry_hash"],
            status=status,
        )

    def load(self, audit_entry_id: str) -> EffectiveReviewAuditEntry:
        row = self._connection.execute(
            "SELECT * FROM governance_effective_review_audit WHERE audit_entry_id = ?",
            (audit_entry_id,),
        ).fetchone()
        if row is None:
            raise KeyError(audit_entry_id)
        entry = self._row_to_entry(row)
        self._verify_entry(entry)
        return entry

    def _verify_entry(self, entry: EffectiveReviewAuditEntry) -> None:
        status_json = _canonical_json(entry.status)
        if _sha256(status_json) != entry.status_sha256:
            raise EffectiveReviewAuditIntegrityError("effective review status digest mismatch")
        expected = _sha256(_canonical_json(_entry_hash_payload(
            audit_entry_id=entry.audit_entry_id,
            sequence=entry.sequence,
            audit_id=entry.audit_id,
            bundle_sha256=entry.bundle_sha256,
            status_sha256=entry.status_sha256,
            previous_entry_hash=entry.previous_entry_hash,
        )))
        if expected != entry.entry_hash:
            raise EffectiveReviewAuditIntegrityError("effective review audit entry hash mismatch")
        if entry.status.get("audit_id") != entry.audit_id or entry.status.get("bundle_sha256") != entry.bundle_sha256:
            raise EffectiveReviewAuditIntegrityError("effective review audit binding mismatch")
        if entry.status.get("send_authorized") is not False or entry.status.get("review_is_campaign_authorization") is not False:
            raise EffectiveReviewAuditIntegrityError("audited effective review status violates non-authorization invariants")

    def verify_chain(self) -> tuple[EffectiveReviewAuditEntry, ...]:
        rows = self._connection.execute("SELECT * FROM governance_effective_review_audit ORDER BY sequence ASC").fetchall()
        entries = tuple(self._row_to_entry(row) for row in rows)
        previous: str | None = None
        for expected_sequence, entry in enumerate(entries, start=1):
            if entry.sequence != expected_sequence:
                raise EffectiveReviewAuditIntegrityError("effective review audit sequence discontinuity")
            if entry.previous_entry_hash != previous:
                raise EffectiveReviewAuditIntegrityError("effective review audit predecessor mismatch")
            self._verify_entry(entry)
            previous = entry.entry_hash
        return entries

    def list_entries(self) -> tuple[EffectiveReviewAuditEntry, ...]:
        return self.verify_chain()


def effective_review_audit_entry_to_mapping(entry: EffectiveReviewAuditEntry) -> dict[str, Any]:
    return {
        "audit_entry_id": entry.audit_entry_id,
        "sequence": entry.sequence,
        "audit_id": entry.audit_id,
        "bundle_sha256": entry.bundle_sha256,
        "status_sha256": entry.status_sha256,
        "previous_entry_hash": entry.previous_entry_hash,
        "entry_hash": entry.entry_hash,
        "status": dict(entry.status),
        "send_authorized": False,
        "audit_is_campaign_authorization": False,
        "audit_is_observational_only": True,
    }


__all__ = [
    "EffectiveReviewAuditConflictError",
    "EffectiveReviewAuditEntry",
    "EffectiveReviewAuditError",
    "EffectiveReviewAuditIntegrityError",
    "EffectiveReviewAuditRepository",
    "effective_review_audit_entry_to_mapping",
]
