from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from searchleads.governance_effective_review_verification_receipt import (
    EffectiveReviewVerificationReceipt,
    EffectiveReviewVerificationReceiptRepository,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_governance_effective_review_verification.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, capture_output=True, text=True, check=False)


def _seed_receipt(db: Path) -> None:
    receipt = EffectiveReviewVerificationReceipt(
        receipt_id="receipt-cli-39",
        evidence_sha256="a" * 64,
        audit_entry_id="effective-audit-cli-39",
        audit_id="audit-cli-39",
        bundle_sha256="b" * 64,
        verified_at=datetime(2026, 9, 12, 7, 0, tzinfo=timezone.utc),
        verifier_reference="searchleads:offline-verifier/v1",
    )
    with EffectiveReviewVerificationReceiptRepository(db) as repository:
        repository.save(receipt)


def test_cli_records_verifies_and_lists_receipt_audit(tmp_path) -> None:
    receipt_db = tmp_path / "receipts.sqlite"
    audit_db = tmp_path / "receipt-audit.sqlite"
    _seed_receipt(receipt_db)

    recorded = _run("record", "--receipt-db", str(receipt_db), "--audit-db", str(audit_db), "--receipt-id", "receipt-cli-39", "--audit-entry-id", "verification-audit-cli-39")
    assert recorded.returncode == 0, recorded.stderr
    payload = json.loads(recorded.stdout)
    assert payload["storage_action"] == "INSERTED"
    assert payload["audit_is_human_approval"] is False
    assert payload["send_authorized"] is False

    verified = _run("verify", "--audit-db", str(audit_db))
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["entry_count"] == 1

    listing = _run("list", "--audit-db", str(audit_db))
    assert listing.returncode == 0, listing.stderr
    entries = json.loads(listing.stdout)["entries"]
    assert entries[0]["receipt_id"] == "receipt-cli-39"


def test_cli_missing_receipt_fails_closed(tmp_path) -> None:
    result = _run("record", "--receipt-db", str(tmp_path / "receipts.sqlite"), "--audit-db", str(tmp_path / "audit.sqlite"), "--receipt-id", "missing", "--audit-entry-id", "va-missing")
    assert result.returncode == 2
    assert "missing" in result.stderr
