from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .governance_effective_review_verification_receipt import (
    EffectiveReviewVerificationReceipt,
    EffectiveReviewVerificationReceiptRepository,
    receipt_to_mapping,
)


class EffectiveReviewVerificationAuditError(RuntimeError):
    pass


class EffectiveReviewVerificationAuditConflictError(EffectiveReviewVerificationAuditError):
    pass


class EffectiveReviewVerificationAuditIntegrityError(EffectiveReviewVerificationAuditError):
    pass


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class EffectiveReviewVerificationAuditEntry:
    audit_entry_id: str
    sequence: int
    receipt_id: str
    evidence_sha256: str
    receipt_sha256: str
    previous_entry_hash: str | None
    entry_hash: str
    receipt: Mapping[str, Any]


def _entry_hash_payload(*, audit_entry_id: str, sequence: int, receipt_id: str, evidence_sha256: str, receipt_sha256: str, previous_entry_hash: str | None) -> dict[str, Any]:
    return {
        "audit_entry_id": audit_entry_id,
        "sequence": sequence,
        "receipt_id": receipt_id,
        "evidence_sha256": evidence_sha256,
        "receipt_sha256": receipt_sha256,
        "previous_entry_hash": previous_entry_hash,
    }


class EffectiveReviewVerificationAuditRepository:
    """Append-only tamper-evident audit trail for Wave 38 technical verification receipts."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("""CREATE TABLE IF NOT EXISTS governance_effective_review_verification_audit (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_entry_id TEXT NOT NULL UNIQUE,
            receipt_id TEXT NOT NULL,
            evidence_sha256 TEXT NOT NULL,
            receipt_json TEXT NOT NULL,
            receipt_sha256 TEXT NOT NULL,
            previous_entry_hash TEXT,
            entry_hash TEXT NOT NULL
        )""")
        self._connection.commit()

    def __enter__(self) -> "EffectiveReviewVerificationAuditRepository":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def append_receipt(self, *, audit_entry_id: str, receipt: EffectiveReviewVerificationReceipt) -> tuple[EffectiveReviewVerificationAuditEntry, bool]:
        if not audit_entry_id.strip():
            raise ValueError("audit_entry_id must not be blank")
        receipt_mapping = receipt_to_mapping(receipt)
        receipt_json = _canonical_json(receipt_mapping)
        receipt_sha256 = _sha256(receipt_json)
        existing = self._connection.execute(
            "SELECT * FROM governance_effective_review_verification_audit WHERE audit_entry_id = ?",
            (audit_entry_id,),
        ).fetchone()
        if existing is not None:
            entry = self._row_to_entry(existing)
            self._verify_entry(entry)
            if _canonical_json(entry.receipt) == receipt_json:
                return entry, False
            raise EffectiveReviewVerificationAuditConflictError(
                f"audit_entry_id {audit_entry_id!r} already exists with different content"
            )

        predecessor = self._connection.execute(
            "SELECT entry_hash FROM governance_effective_review_verification_audit ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_entry_hash = predecessor["entry_hash"] if predecessor is not None else None
        sequence = self._connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 AS next_sequence FROM governance_effective_review_verification_audit"
        ).fetchone()["next_sequence"]
        entry_hash = _sha256(_canonical_json(_entry_hash_payload(
            audit_entry_id=audit_entry_id,
            sequence=sequence,
            receipt_id=receipt.receipt_id,
            evidence_sha256=receipt.evidence_sha256,
            receipt_sha256=receipt_sha256,
            previous_entry_hash=previous_entry_hash,
        )))
        self._connection.execute(
            "INSERT INTO governance_effective_review_verification_audit(sequence,audit_entry_id,receipt_id,evidence_sha256,receipt_json,receipt_sha256,previous_entry_hash,entry_hash) VALUES (?,?,?,?,?,?,?,?)",
            (sequence, audit_entry_id, receipt.receipt_id, receipt.evidence_sha256, receipt_json, receipt_sha256, previous_entry_hash, entry_hash),
        )
        self._connection.commit()
        return self.load(audit_entry_id), True

    def _row_to_entry(self, row: sqlite3.Row) -> EffectiveReviewVerificationAuditEntry:
        try:
            receipt = json.loads(row["receipt_json"])
        except json.JSONDecodeError as exc:
            raise EffectiveReviewVerificationAuditIntegrityError("stored receipt JSON is invalid") from exc
        return EffectiveReviewVerificationAuditEntry(
            audit_entry_id=row["audit_entry_id"],
            sequence=row["sequence"],
            receipt_id=row["receipt_id"],
            evidence_sha256=row["evidence_sha256"],
            receipt_sha256=row["receipt_sha256"],
            previous_entry_hash=row["previous_entry_hash"],
            entry_hash=row["entry_hash"],
            receipt=receipt,
        )

    def _verify_entry(self, entry: EffectiveReviewVerificationAuditEntry) -> None:
        receipt_json = _canonical_json(entry.receipt)
        if _sha256(receipt_json) != entry.receipt_sha256:
            raise EffectiveReviewVerificationAuditIntegrityError("verification receipt digest mismatch")
        if entry.receipt.get("receipt_id") != entry.receipt_id or entry.receipt.get("evidence_sha256") != entry.evidence_sha256:
            raise EffectiveReviewVerificationAuditIntegrityError("verification audit binding mismatch")
        if entry.receipt.get("send_authorized") is not False:
            raise EffectiveReviewVerificationAuditIntegrityError("audited receipt must not authorize send")
        if entry.receipt.get("verification_is_campaign_authorization") is not False or entry.receipt.get("verification_is_human_approval") is not False:
            raise EffectiveReviewVerificationAuditIntegrityError("audited receipt must not represent campaign authorization or human approval")
        if entry.receipt.get("receipt_is_observational_only") is not True:
            raise EffectiveReviewVerificationAuditIntegrityError("audited receipt must remain observational only")
        expected = _sha256(_canonical_json(_entry_hash_payload(
            audit_entry_id=entry.audit_entry_id,
            sequence=entry.sequence,
            receipt_id=entry.receipt_id,
            evidence_sha256=entry.evidence_sha256,
            receipt_sha256=entry.receipt_sha256,
            previous_entry_hash=entry.previous_entry_hash,
        )))
        if expected != entry.entry_hash:
            raise EffectiveReviewVerificationAuditIntegrityError("verification audit entry hash mismatch")

    def load(self, audit_entry_id: str) -> EffectiveReviewVerificationAuditEntry:
        row = self._connection.execute(
            "SELECT * FROM governance_effective_review_verification_audit WHERE audit_entry_id = ?",
            (audit_entry_id,),
        ).fetchone()
        if row is None:
            raise KeyError(audit_entry_id)
        entry = self._row_to_entry(row)
        self._verify_entry(entry)
        return entry

    def verify_chain(self) -> tuple[EffectiveReviewVerificationAuditEntry, ...]:
        rows = self._connection.execute(
            "SELECT * FROM governance_effective_review_verification_audit ORDER BY sequence ASC"
        ).fetchall()
        entries = tuple(self._row_to_entry(row) for row in rows)
        previous: str | None = None
        for expected_sequence, entry in enumerate(entries, start=1):
            if entry.sequence != expected_sequence:
                raise EffectiveReviewVerificationAuditIntegrityError("verification audit sequence discontinuity")
            if entry.previous_entry_hash != previous:
                raise EffectiveReviewVerificationAuditIntegrityError("verification audit predecessor mismatch")
            self._verify_entry(entry)
            previous = entry.entry_hash
        return entries

    def list_entries(self) -> tuple[EffectiveReviewVerificationAuditEntry, ...]:
        return self.verify_chain()


def append_receipt_by_id(*, receipt_repository: EffectiveReviewVerificationReceiptRepository, audit_repository: EffectiveReviewVerificationAuditRepository, receipt_id: str, audit_entry_id: str) -> tuple[EffectiveReviewVerificationAuditEntry, bool]:
    receipt = receipt_repository.load(receipt_id)
    return audit_repository.append_receipt(audit_entry_id=audit_entry_id, receipt=receipt)


def verification_audit_entry_to_mapping(entry: EffectiveReviewVerificationAuditEntry) -> dict[str, Any]:
    return {
        "audit_entry_id": entry.audit_entry_id,
        "sequence": entry.sequence,
        "receipt_id": entry.receipt_id,
        "evidence_sha256": entry.evidence_sha256,
        "receipt_sha256": entry.receipt_sha256,
        "previous_entry_hash": entry.previous_entry_hash,
        "entry_hash": entry.entry_hash,
        "receipt": dict(entry.receipt),
        "send_authorized": False,
        "audit_is_campaign_authorization": False,
        "audit_is_human_approval": False,
        "audit_is_observational_only": True,
    }


__all__ = [
    "EffectiveReviewVerificationAuditConflictError",
    "EffectiveReviewVerificationAuditEntry",
    "EffectiveReviewVerificationAuditError",
    "EffectiveReviewVerificationAuditIntegrityError",
    "EffectiveReviewVerificationAuditRepository",
    "append_receipt_by_id",
    "verification_audit_entry_to_mapping",
]
