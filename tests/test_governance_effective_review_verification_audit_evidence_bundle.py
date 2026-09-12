from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import pytest

from searchleads.governance_effective_review_verification_audit import EffectiveReviewVerificationAuditRepository
from searchleads.governance_effective_review_verification_audit_evidence_bundle import (
    EffectiveReviewVerificationAuditEvidenceError,
    build_effective_review_verification_audit_evidence_bundle,
    verification_audit_evidence_bundle_to_mapping,
    verify_effective_review_verification_audit_evidence_bundle,
)
from searchleads.governance_effective_review_verification_receipt import EffectiveReviewVerificationReceipt


NOW = datetime(2026, 9, 12, 7, 0, tzinfo=timezone.utc)


def _receipt(receipt_id: str, evidence_char: str) -> EffectiveReviewVerificationReceipt:
    return EffectiveReviewVerificationReceipt(
        receipt_id=receipt_id,
        evidence_sha256=evidence_char * 64,
        audit_entry_id=f"effective-{receipt_id}",
        audit_id=f"audit-{receipt_id}",
        bundle_sha256="b" * 64,
        verified_at=NOW,
        verifier_reference="searchleads:offline-verifier/v1",
    )


def test_builds_deterministic_historical_chain_prefix(tmp_path) -> None:
    db = tmp_path / "verification-audit.sqlite"
    with EffectiveReviewVerificationAuditRepository(db) as repository:
        repository.append_receipt(audit_entry_id="verification-audit-1", receipt=_receipt("receipt-1", "a"))
        repository.append_receipt(audit_entry_id="verification-audit-2", receipt=_receipt("receipt-2", "c"))
        first = verification_audit_evidence_bundle_to_mapping(build_effective_review_verification_audit_evidence_bundle(audit_repository=repository, audit_entry_id="verification-audit-1"))
        first_again = verification_audit_evidence_bundle_to_mapping(build_effective_review_verification_audit_evidence_bundle(audit_repository=repository, audit_entry_id="verification-audit-1"))
        second = verification_audit_evidence_bundle_to_mapping(build_effective_review_verification_audit_evidence_bundle(audit_repository=repository, audit_entry_id="verification-audit-2"))
    assert first == first_again
    assert len(first["chain_headers"]) == 1
    assert len(second["chain_headers"]) == 2
    assert first["receipt_id"] == "receipt-1"
    assert first["send_authorized"] is False
    assert first["evidence_is_human_approval"] is False
    verify_effective_review_verification_audit_evidence_bundle(first)
    verify_effective_review_verification_audit_evidence_bundle(second)


def test_tampering_and_binding_mismatch_fail_closed(tmp_path) -> None:
    with EffectiveReviewVerificationAuditRepository(tmp_path / "audit.sqlite") as repository:
        repository.append_receipt(audit_entry_id="verification-audit-1", receipt=_receipt("receipt-1", "a"))
        payload = verification_audit_evidence_bundle_to_mapping(build_effective_review_verification_audit_evidence_bundle(audit_repository=repository, audit_entry_id="verification-audit-1"))
    tampered = json.loads(json.dumps(payload))
    tampered["receipt"]["verifier_reference"] = "other"
    with pytest.raises(EffectiveReviewVerificationAuditEvidenceError):
        verify_effective_review_verification_audit_evidence_bundle(tampered)


def test_negative_scope_rewrite_rejected_even_with_recomputed_digest(tmp_path) -> None:
    with EffectiveReviewVerificationAuditRepository(tmp_path / "audit.sqlite") as repository:
        repository.append_receipt(audit_entry_id="verification-audit-1", receipt=_receipt("receipt-1", "a"))
        payload = verification_audit_evidence_bundle_to_mapping(build_effective_review_verification_audit_evidence_bundle(audit_repository=repository, audit_entry_id="verification-audit-1"))
    payload["changes_preflight"] = True
    unsigned = dict(payload)
    unsigned.pop("export_sha256")
    payload["export_sha256"] = hashlib.sha256(json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    with pytest.raises(EffectiveReviewVerificationAuditEvidenceError, match="negative-scope"):
        verify_effective_review_verification_audit_evidence_bundle(payload)


def test_missing_entry_rejected(tmp_path) -> None:
    with EffectiveReviewVerificationAuditRepository(tmp_path / "audit.sqlite") as repository:
        with pytest.raises(KeyError):
            build_effective_review_verification_audit_evidence_bundle(audit_repository=repository, audit_entry_id="missing")
