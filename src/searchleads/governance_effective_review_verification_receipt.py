from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .governance_effective_review_evidence_bundle import verify_effective_review_evidence_bundle


class EffectiveReviewVerificationReceiptError(RuntimeError):
    pass


class EffectiveReviewVerificationReceiptConflictError(EffectiveReviewVerificationReceiptError):
    pass


class EffectiveReviewVerificationReceiptIntegrityError(EffectiveReviewVerificationReceiptError):
    pass


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class EffectiveReviewVerificationReceipt:
    receipt_id: str
    evidence_sha256: str
    audit_entry_id: str
    audit_id: str
    bundle_sha256: str
    verified_at: datetime
    verifier_reference: str
    send_authorized: bool = False
    verification_is_campaign_authorization: bool = False
    verification_is_human_approval: bool = False

    def __post_init__(self) -> None:
        for field, value in (("receipt_id", self.receipt_id), ("audit_entry_id", self.audit_entry_id), ("audit_id", self.audit_id), ("verifier_reference", self.verifier_reference)):
            if not value.strip():
                raise ValueError(f"{field} must not be blank")
        if len(self.evidence_sha256) != 64 or len(self.bundle_sha256) != 64:
            raise ValueError("evidence_sha256 and bundle_sha256 must be SHA-256 hex digests")
        if self.verified_at.tzinfo is None:
            raise ValueError("verified_at must be timezone-aware")
        if self.send_authorized or self.verification_is_campaign_authorization or self.verification_is_human_approval:
            raise ValueError("verification receipt cannot authorize send/campaign or represent human approval")


def receipt_to_mapping(receipt: EffectiveReviewVerificationReceipt) -> dict[str, Any]:
    return {
        "receipt_id": receipt.receipt_id,
        "evidence_sha256": receipt.evidence_sha256,
        "audit_entry_id": receipt.audit_entry_id,
        "audit_id": receipt.audit_id,
        "bundle_sha256": receipt.bundle_sha256,
        "verified_at": receipt.verified_at.isoformat(),
        "verifier_reference": receipt.verifier_reference,
        "send_authorized": False,
        "verification_is_campaign_authorization": False,
        "verification_is_human_approval": False,
        "receipt_is_observational_only": True,
    }


def receipt_from_mapping(payload: Mapping[str, Any]) -> EffectiveReviewVerificationReceipt:
    def text(field: str) -> str:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-blank string")
        return value.strip()

    for field in ("send_authorized", "verification_is_campaign_authorization", "verification_is_human_approval"):
        if payload.get(field, False) is not False:
            raise ValueError("verification receipt cannot authorize send/campaign or represent human approval")
    if payload.get("receipt_is_observational_only", True) is not True:
        raise ValueError("verification receipt must remain observational only")
    return EffectiveReviewVerificationReceipt(
        receipt_id=text("receipt_id"),
        evidence_sha256=text("evidence_sha256"),
        audit_entry_id=text("audit_entry_id"),
        audit_id=text("audit_id"),
        bundle_sha256=text("bundle_sha256"),
        verified_at=datetime.fromisoformat(text("verified_at").replace("Z", "+00:00")),
        verifier_reference=text("verifier_reference"),
    )


class EffectiveReviewVerificationReceiptRepository:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("""CREATE TABLE IF NOT EXISTS governance_effective_review_verification_receipts (
            receipt_id TEXT PRIMARY KEY,
            evidence_sha256 TEXT NOT NULL,
            verified_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        self._connection.execute("CREATE INDEX IF NOT EXISTS idx_effective_review_receipts_evidence ON governance_effective_review_verification_receipts(evidence_sha256, verified_at)")
        self._connection.commit()

    def __enter__(self) -> "EffectiveReviewVerificationReceiptRepository":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def save(self, receipt: EffectiveReviewVerificationReceipt) -> bool:
        payload_json = _canonical_json(receipt_to_mapping(receipt))
        payload_sha256 = _sha256(payload_json)
        row = self._connection.execute("SELECT payload_json, payload_sha256 FROM governance_effective_review_verification_receipts WHERE receipt_id = ?", (receipt.receipt_id,)).fetchone()
        if row is not None:
            if _sha256(row["payload_json"]) != row["payload_sha256"]:
                raise EffectiveReviewVerificationReceiptIntegrityError("stored verification receipt digest mismatch")
            if row["payload_json"] == payload_json:
                return False
            raise EffectiveReviewVerificationReceiptConflictError(f"receipt_id {receipt.receipt_id!r} already exists with different content")
        self._connection.execute("INSERT INTO governance_effective_review_verification_receipts(receipt_id,evidence_sha256,verified_at,payload_json,payload_sha256) VALUES (?,?,?,?,?)", (receipt.receipt_id, receipt.evidence_sha256, receipt.verified_at.isoformat(), payload_json, payload_sha256))
        self._connection.commit()
        return True

    def load(self, receipt_id: str) -> EffectiveReviewVerificationReceipt:
        row = self._connection.execute("SELECT payload_json, payload_sha256 FROM governance_effective_review_verification_receipts WHERE receipt_id = ?", (receipt_id,)).fetchone()
        if row is None:
            raise KeyError(receipt_id)
        if _sha256(row["payload_json"]) != row["payload_sha256"]:
            raise EffectiveReviewVerificationReceiptIntegrityError("stored verification receipt digest mismatch")
        return receipt_from_mapping(json.loads(row["payload_json"]))

    def list_for_evidence(self, evidence_sha256: str) -> tuple[EffectiveReviewVerificationReceipt, ...]:
        rows = self._connection.execute("SELECT receipt_id FROM governance_effective_review_verification_receipts WHERE evidence_sha256 = ? ORDER BY verified_at ASC, receipt_id ASC", (evidence_sha256,)).fetchall()
        return tuple(self.load(row["receipt_id"]) for row in rows)


def process_verification_receipt(*, repository: EffectiveReviewVerificationReceiptRepository, evidence_bundle: Mapping[str, Any], receipt_payload: Mapping[str, Any]) -> tuple[EffectiveReviewVerificationReceipt, bool]:
    bundle = dict(evidence_bundle)
    verify_effective_review_evidence_bundle(bundle)
    receipt = receipt_from_mapping(receipt_payload)
    expected = {
        "evidence_sha256": bundle.get("evidence_sha256"),
        "audit_entry_id": bundle.get("audit_entry_id"),
        "audit_id": bundle.get("audit_id"),
        "bundle_sha256": bundle.get("bundle_sha256"),
    }
    for field, value in expected.items():
        if getattr(receipt, field) != value:
            raise ValueError(f"verification receipt {field} does not match verified evidence bundle")
    return receipt, repository.save(receipt)


__all__ = [
    "EffectiveReviewVerificationReceipt",
    "EffectiveReviewVerificationReceiptConflictError",
    "EffectiveReviewVerificationReceiptIntegrityError",
    "EffectiveReviewVerificationReceiptRepository",
    "process_verification_receipt",
    "receipt_from_mapping",
    "receipt_to_mapping",
]
