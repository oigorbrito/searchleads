from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from searchleads.governance_effective_review_audit import EffectiveReviewAuditRepository
from searchleads.governance_effective_review_status import (
    EffectiveEvidenceReviewSource,
    EffectiveEvidenceReviewState,
    EffectiveEvidenceReviewStatus,
)
from searchleads.governance_evidence_review import EvidenceReviewDecision


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "export_governance_effective_review_evidence.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _seed(audit_db: Path) -> None:
    status = EffectiveEvidenceReviewStatus(
        audit_id="audit-cli-37",
        bundle_sha256="d" * 64,
        state=EffectiveEvidenceReviewState.EFFECTIVE_REVIEW_DECISION,
        effective_decision=EvidenceReviewDecision.APPROVED,
        decision_source=EffectiveEvidenceReviewSource.CONSOLIDATED_REVIEWS,
        review_ids=("review-cli-37",),
        applicable_resolution_ids=(),
        stale_resolution_ids=(),
        conflict=False,
    )
    with EffectiveReviewAuditRepository(audit_db) as audit:
        audit.append_status(audit_entry_id="effective-audit-cli-37", status=status)


def test_cli_exports_and_offline_verifies_bundle(tmp_path) -> None:
    audit_db = tmp_path / "audit.sqlite"
    output = tmp_path / "effective-review-evidence.json"
    _seed(audit_db)

    exported = _run(
        "export",
        "--audit-db",
        str(audit_db),
        "--audit-entry-id",
        "effective-audit-cli-37",
        "--output",
        str(output),
    )
    assert exported.returncode == 0, exported.stderr
    payload = json.loads(exported.stdout)
    assert payload == json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "effective-review-evidence-bundle/v1"
    assert payload["send_authorized"] is False

    verified = _run("verify", "--bundle", str(output))
    assert verified.returncode == 0, verified.stderr
    result = json.loads(verified.stdout)
    assert result["valid"] is True
    assert result["audit_entry_id"] == "effective-audit-cli-37"
    assert result["evidence_is_campaign_authorization"] is False


def test_cli_verify_rejects_tampered_bundle(tmp_path) -> None:
    audit_db = tmp_path / "audit.sqlite"
    output = tmp_path / "effective-review-evidence.json"
    _seed(audit_db)
    exported = _run(
        "export",
        "--audit-db",
        str(audit_db),
        "--audit-entry-id",
        "effective-audit-cli-37",
        "--output",
        str(output),
    )
    assert exported.returncode == 0, exported.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["status"]["decision_source"] = "HUMAN_CONFLICT_RESOLUTION"
    output.write_text(json.dumps(payload), encoding="utf-8")

    verified = _run("verify", "--bundle", str(output))
    assert verified.returncode == 2
    assert "digest mismatch" in verified.stderr


def test_cli_export_rejects_missing_entry(tmp_path) -> None:
    result = _run(
        "export",
        "--audit-db",
        str(tmp_path / "audit.sqlite"),
        "--audit-entry-id",
        "missing",
    )
    assert result.returncode == 2
    assert "missing" in result.stderr
