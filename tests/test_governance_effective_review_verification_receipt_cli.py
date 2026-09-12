from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from searchleads.governance_effective_review_audit import EffectiveReviewAuditRepository
from searchleads.governance_effective_review_evidence_bundle import (
    build_effective_review_evidence_bundle,
    effective_review_evidence_bundle_to_mapping,
)
from searchleads.governance_effective_review_status import (
    EffectiveEvidenceReviewSource,
    EffectiveEvidenceReviewState,
    EffectiveEvidenceReviewStatus,
)
from searchleads.governance_evidence_review import EvidenceReviewDecision

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "record_governance_effective_review_verification.py"
NOW = datetime(2026, 9, 12, 6, 30, tzinfo=timezone.utc)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, capture_output=True, text=True, check=False)


def _evidence(tmp_path: Path) -> dict:
    audit_db = tmp_path / "audit.sqlite"
    status = EffectiveEvidenceReviewStatus(
        audit_id="audit-cli-38",
        bundle_sha256="e" * 64,
        state=EffectiveEvidenceReviewState.EFFECTIVE_REVIEW_DECISION,
        effective_decision=EvidenceReviewDecision.APPROVED,
        decision_source=EffectiveEvidenceReviewSource.CONSOLIDATED_REVIEWS,
        review_ids=("review-cli-38",),
        applicable_resolution_ids=(),
        stale_resolution_ids=(),
        conflict=False,
    )
    with EffectiveReviewAuditRepository(audit_db) as audit:
        audit.append_status(audit_entry_id="effective-audit-cli-38", status=status)
        return effective_review_evidence_bundle_to_mapping(build_effective_review_evidence_bundle(audit_repository=audit, audit_entry_id="effective-audit-cli-38"))


def test_cli_records_and_lists_receipt(tmp_path) -> None:
    evidence = _evidence(tmp_path)
    evidence_path = tmp_path / "evidence.json"
    receipt_path = tmp_path / "receipt.json"
    db = tmp_path / "receipts.sqlite"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    receipt_path.write_text(json.dumps({
        "receipt_id": "receipt-cli-38",
        "evidence_sha256": evidence["evidence_sha256"],
        "audit_entry_id": evidence["audit_entry_id"],
        "audit_id": evidence["audit_id"],
        "bundle_sha256": evidence["bundle_sha256"],
        "verified_at": NOW.isoformat(),
        "verifier_reference": "searchleads:offline-verifier/v1",
        "send_authorized": False,
        "verification_is_campaign_authorization": False,
        "verification_is_human_approval": False,
    }), encoding="utf-8")

    recorded = _run("record", "--evidence", str(evidence_path), "--receipt", str(receipt_path), "--db", str(db))
    assert recorded.returncode == 0, recorded.stderr
    payload = json.loads(recorded.stdout)
    assert payload["storage_action"] == "INSERTED"
    assert payload["verification_is_human_approval"] is False

    listed = _run("list", "--evidence-sha256", evidence["evidence_sha256"], "--db", str(db))
    assert listed.returncode == 0, listed.stderr
    result = json.loads(listed.stdout)
    assert result["receipt_count"] == 1
    assert result["receipts"][0]["receipt_id"] == "receipt-cli-38"
    assert result["send_authorized"] is False


def test_cli_rejects_tampered_evidence(tmp_path) -> None:
    evidence = _evidence(tmp_path)
    evidence["status"]["effective_decision"] = "REJECTED"
    evidence_path = tmp_path / "evidence.json"
    receipt_path = tmp_path / "receipt.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    receipt_path.write_text(json.dumps({
        "receipt_id": "receipt-cli-38",
        "evidence_sha256": evidence["evidence_sha256"],
        "audit_entry_id": evidence["audit_entry_id"],
        "audit_id": evidence["audit_id"],
        "bundle_sha256": evidence["bundle_sha256"],
        "verified_at": NOW.isoformat(),
        "verifier_reference": "searchleads:offline-verifier/v1",
        "send_authorized": False,
        "verification_is_campaign_authorization": False,
        "verification_is_human_approval": False,
    }), encoding="utf-8")
    result = _run("record", "--evidence", str(evidence_path), "--receipt", str(receipt_path), "--db", str(tmp_path / "receipts.sqlite"))
    assert result.returncode == 2
    assert "INVALID:" in result.stderr
