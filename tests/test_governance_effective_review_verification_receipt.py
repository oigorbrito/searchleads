from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import pytest

from searchleads.governance_effective_review_verification_receipt import (
    EffectiveReviewVerificationReceiptConflictError,
    EffectiveReviewVerificationReceiptIntegrityError,
    EffectiveReviewVerificationReceiptRepository,
    process_verification_receipt,
)

NOW = datetime(2026, 9, 12, 6, 0, tzinfo=timezone.utc)


def _canonical(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _evidence():
    status = {
        "audit_id": "audit-38",
        "bundle_sha256": "b" * 64,
        "state": "EFFECTIVE_REVIEW_DECISION",
        "effective_decision": "APPROVED",
        "decision_source": "CONSOLIDATED_REVIEWS",
        "review_ids": ["review-1"],
        "applicable_resolution_ids": [],
        "stale_resolution_ids": [],
        "conflict": False,
        "send_authorized": False,
        "review_is_campaign_authorization": False,
        "changes_auth_campaign_001": False,
        "changes_preflight": False,
        "changes_pilot_release": False,
        "changes_legal_signoff": False,
        "changes_professional_verification": False,
        "changes_source_freshness": False,
        "status_is_observational_only": True,
    }
    status_sha = _sha(_canonical(status))
    header = {
        "audit_entry_id": "effective-audit-38",
        "sequence": 1,
        "audit_id": "audit-38",
        "bundle_sha256": "b" * 64,
        "status_sha256": status_sha,
        "previous_entry_hash": None,
    }
    header["entry_hash"] = _sha(_canonical(header))
    audit_entry = dict(header)
    audit_entry["status"] = status
    audit_entry.update({"send_authorized": False, "audit_is_campaign_authorization": False, "audit_is_observational_only": True})
    evidence = {
        "schema_version": "effective-review-evidence-bundle/v1",
        "audit_entry_id": "effective-audit-38",
        "audit_id": "audit-38",
        "bundle_sha256": "b" * 64,
        "status": status,
        "audit_entry": audit_entry,
        "chain_headers": [header],
        "send_authorized": False,
        "evidence_is_campaign_authorization": False,
        "evidence_is_observational_only": True,
        "changes_auth_campaign_001": False,
        "changes_preflight": False,
        "changes_pilot_release": False,
        "changes_legal_signoff": False,
        "changes_professional_verification": False,
        "changes_source_freshness": False,
    }
    evidence["evidence_sha256"] = _sha(_canonical(evidence))
    return evidence


def _receipt(evidence, receipt_id="receipt-1"):
    return {
        "receipt_id": receipt_id,
        "evidence_sha256": evidence["evidence_sha256"],
        "audit_entry_id": evidence["audit_entry_id"],
        "audit_id": evidence["audit_id"],
        "bundle_sha256": evidence["bundle_sha256"],
        "verified_at": NOW.isoformat(),
        "verifier_reference": "searchleads:offline-verifier/v1",
        "send_authorized": False,
        "verification_is_campaign_authorization": False,
        "verification_is_human_approval": False,
    }


def test_valid_receipt_is_immutable_and_idempotent(tmp_path) -> None:
    evidence = _evidence()
    with EffectiveReviewVerificationReceiptRepository(tmp_path / "receipts.sqlite") as repository:
        receipt, inserted = process_verification_receipt(repository=repository, evidence_bundle=evidence, receipt_payload=_receipt(evidence))
        _, replay = process_verification_receipt(repository=repository, evidence_bundle=evidence, receipt_payload=_receipt(evidence))
        assert inserted is True and replay is False
        assert receipt.send_authorized is False
        assert repository.list_for_evidence(evidence["evidence_sha256"])[0].receipt_id == "receipt-1"


def test_binding_mismatch_and_authority_claims_fail_closed(tmp_path) -> None:
    evidence = _evidence()
    with EffectiveReviewVerificationReceiptRepository(tmp_path / "receipts.sqlite") as repository:
        bad = _receipt(evidence)
        bad["audit_id"] = "other"
        with pytest.raises(ValueError, match="audit_id"):
            process_verification_receipt(repository=repository, evidence_bundle=evidence, receipt_payload=bad)
        authority = _receipt(evidence)
        authority["verification_is_human_approval"] = True
        with pytest.raises(ValueError, match="cannot authorize"):
            process_verification_receipt(repository=repository, evidence_bundle=evidence, receipt_payload=authority)
        non_observational = _receipt(evidence)
        non_observational["receipt_is_observational_only"] = False
        with pytest.raises(ValueError, match="observational only"):
            process_verification_receipt(repository=repository, evidence_bundle=evidence, receipt_payload=non_observational)


def test_tampered_evidence_cannot_produce_receipt(tmp_path) -> None:
    evidence = _evidence()
    evidence["status"] = dict(evidence["status"])
    evidence["status"]["effective_decision"] = "REJECTED"
    with EffectiveReviewVerificationReceiptRepository(tmp_path / "receipts.sqlite") as repository:
        with pytest.raises(RuntimeError):
            process_verification_receipt(repository=repository, evidence_bundle=evidence, receipt_payload=_receipt(evidence))


def test_same_receipt_id_with_different_content_conflicts(tmp_path) -> None:
    evidence = _evidence()
    with EffectiveReviewVerificationReceiptRepository(tmp_path / "receipts.sqlite") as repository:
        process_verification_receipt(repository=repository, evidence_bundle=evidence, receipt_payload=_receipt(evidence))
        changed = _receipt(evidence)
        changed["verifier_reference"] = "searchleads:other-verifier"
        with pytest.raises(EffectiveReviewVerificationReceiptConflictError):
            process_verification_receipt(repository=repository, evidence_bundle=evidence, receipt_payload=changed)


def test_stored_receipt_tampering_is_detected(tmp_path) -> None:
    evidence = _evidence()
    db = tmp_path / "receipts.sqlite"
    with EffectiveReviewVerificationReceiptRepository(db) as repository:
        process_verification_receipt(repository=repository, evidence_bundle=evidence, receipt_payload=_receipt(evidence))
        repository._connection.execute("UPDATE governance_effective_review_verification_receipts SET payload_json = ? WHERE receipt_id = ?", ("{}", "receipt-1"))
        repository._connection.commit()
        with pytest.raises(EffectiveReviewVerificationReceiptIntegrityError):
            repository.load("receipt-1")
