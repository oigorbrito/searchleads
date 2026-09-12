from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from searchleads.governance_effective_review_verification_audit import EffectiveReviewVerificationAuditRepository
from searchleads.governance_effective_review_verification_receipt import EffectiveReviewVerificationReceipt


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "export_governance_effective_review_verification_audit_evidence.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, capture_output=True, text=True, check=False)


def _seed(db: Path) -> None:
    receipt = EffectiveReviewVerificationReceipt(
        receipt_id="receipt-cli-40",
        evidence_sha256="e" * 64,
        audit_entry_id="effective-receipt-cli-40",
        audit_id="audit-cli-40",
        bundle_sha256="b" * 64,
        verified_at=datetime(2026, 9, 12, 7, 30, tzinfo=timezone.utc),
        verifier_reference="searchleads:offline-verifier/v1",
    )
    with EffectiveReviewVerificationAuditRepository(db) as repository:
        repository.append_receipt(audit_entry_id="verification-audit-cli-40", receipt=receipt)


def test_cli_exports_and_offline_verifies(tmp_path) -> None:
    db = tmp_path / "audit.sqlite"
    output = tmp_path / "verification-audit-evidence.json"
    _seed(db)
    exported = _run("export", "--audit-db", str(db), "--audit-entry-id", "verification-audit-cli-40", "--output", str(output))
    assert exported.returncode == 0, exported.stderr
    payload = json.loads(exported.stdout)
    assert payload == json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "effective-review-verification-audit-evidence-bundle/v1"
    assert payload["evidence_is_human_approval"] is False

    verified = _run("verify", "--bundle", str(output))
    assert verified.returncode == 0, verified.stderr
    result = json.loads(verified.stdout)
    assert result["valid"] is True
    assert result["audit_entry_id"] == "verification-audit-cli-40"
    assert result["evidence_is_campaign_authorization"] is False


def test_cli_verify_rejects_tampered_export(tmp_path) -> None:
    db = tmp_path / "audit.sqlite"
    output = tmp_path / "verification-audit-evidence.json"
    _seed(db)
    assert _run("export", "--audit-db", str(db), "--audit-entry-id", "verification-audit-cli-40", "--output", str(output)).returncode == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["receipt"]["verifier_reference"] = "tampered"
    output.write_text(json.dumps(payload), encoding="utf-8")
    result = _run("verify", "--bundle", str(output))
    assert result.returncode == 2
    assert "INVALID:" in result.stderr


def test_cli_export_rejects_missing_entry(tmp_path) -> None:
    result = _run("export", "--audit-db", str(tmp_path / "audit.sqlite"), "--audit-entry-id", "missing")
    assert result.returncode == 2
    assert "missing" in result.stderr
