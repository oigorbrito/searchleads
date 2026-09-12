from __future__ import annotations

from datetime import datetime, timezone

import pytest

from searchleads.governance_effective_review_verification_audit import (
    EffectiveReviewVerificationAuditIntegrityError,
    EffectiveReviewVerificationAuditRepository,
)
from searchleads.governance_effective_review_verification_receipt import EffectiveReviewVerificationReceipt

NOW = datetime(2026, 9, 12, 6, 30, tzinfo=timezone.utc)


def _receipt(receipt_id: str, evidence: str) -> EffectiveReviewVerificationReceipt:
    return EffectiveReviewVerificationReceipt(
        receipt_id=receipt_id,
        evidence_sha256=evidence,
        audit_entry_id=f"effective-{receipt_id}",
        audit_id=f"audit-{receipt_id}",
        bundle_sha256="b" * 64,
        verified_at=NOW,
        verifier_reference="searchleads:offline-verifier/v1",
    )


def test_append_chain_and_idempotent_replay(tmp_path) -> None:
    db = tmp_path / "verification-audit.sqlite"
    with EffectiveReviewVerificationAuditRepository(db) as audit:
        first, inserted = audit.append_receipt(audit_entry_id="va-1", receipt=_receipt("receipt-1", "a" * 64))
        replay, replayed = audit.append_receipt(audit_entry_id="va-1", receipt=_receipt("receipt-1", "a" * 64))
        second, inserted_second = audit.append_receipt(audit_entry_id="va-2", receipt=_receipt("receipt-2", "c" * 64))
        assert inserted is True and replayed is False and inserted_second is True
        assert replay.entry_hash == first.entry_hash
        assert second.previous_entry_hash == first.entry_hash
        assert len(audit.verify_chain()) == 2


def test_receipt_tampering_and_predecessor_tampering_fail_closed(tmp_path) -> None:
    db = tmp_path / "verification-audit.sqlite"
    with EffectiveReviewVerificationAuditRepository(db) as audit:
        audit.append_receipt(audit_entry_id="va-1", receipt=_receipt("receipt-1", "a" * 64))
        audit.append_receipt(audit_entry_id="va-2", receipt=_receipt("receipt-2", "c" * 64))
        audit._connection.execute("UPDATE governance_effective_review_verification_audit SET receipt_json = ? WHERE audit_entry_id = ?", ("{}", "va-1"))
        audit._connection.commit()
        with pytest.raises(EffectiveReviewVerificationAuditIntegrityError):
            audit.verify_chain()

    db2 = tmp_path / "verification-audit-2.sqlite"
    with EffectiveReviewVerificationAuditRepository(db2) as audit:
        audit.append_receipt(audit_entry_id="va-1", receipt=_receipt("receipt-1", "a" * 64))
        audit.append_receipt(audit_entry_id="va-2", receipt=_receipt("receipt-2", "c" * 64))
        audit._connection.execute("UPDATE governance_effective_review_verification_audit SET previous_entry_hash = ? WHERE audit_entry_id = ?", ("0" * 64, "va-2"))
        audit._connection.commit()
        with pytest.raises(EffectiveReviewVerificationAuditIntegrityError, match="predecessor"):
            audit.verify_chain()


def test_non_authorization_semantics_are_verified(tmp_path) -> None:
    db = tmp_path / "verification-audit.sqlite"
    with EffectiveReviewVerificationAuditRepository(db) as audit:
        audit.append_receipt(audit_entry_id="va-1", receipt=_receipt("receipt-1", "a" * 64))
        row = audit._connection.execute("SELECT receipt_json FROM governance_effective_review_verification_audit WHERE audit_entry_id = 'va-1'").fetchone()
        import json, hashlib
        payload = json.loads(row["receipt_json"])
        payload["verification_is_human_approval"] = True
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(text.encode()).hexdigest()
        audit._connection.execute("UPDATE governance_effective_review_verification_audit SET receipt_json = ?, receipt_sha256 = ? WHERE audit_entry_id = 'va-1'", (text, digest))
        audit._connection.commit()
        with pytest.raises(EffectiveReviewVerificationAuditIntegrityError, match="human approval"):
            audit.verify_chain()
