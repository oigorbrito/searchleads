from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from searchleads.governance_audit import GovernanceAuditRepository
from searchleads.governance_evidence_bundle import build_governance_evidence_bundle, governance_evidence_bundle_to_mapping
from searchleads.governance_persistence import GovernanceDecisionRepository
from searchleads.governance_preflight import CampaignPreflightScope
from searchleads.governance_snapshot import build_governance_operational_snapshot

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "show_governance_effective_review_status.py"
NOW = datetime(2026, 9, 12, 6, 30, tzinfo=timezone.utc)


def _bundle_file(tmp_path: Path) -> Path:
    state_db = tmp_path / "state.sqlite"
    scope = CampaignPreflightScope(campaign_id="cmp-35-cli", policy_id="policy-35-cli", policy_version="v1", jurisdiction="BR-RS", channel="email", brasilapi_fresh=False)
    with GovernanceDecisionRepository(state_db) as repository:
        snapshot = build_governance_operational_snapshot(repository=repository, scope=scope, now=NOW)
    with GovernanceAuditRepository(state_db) as repository:
        repository.append_snapshot(audit_id="audit-35-cli", snapshot=snapshot)
        bundle = governance_evidence_bundle_to_mapping(build_governance_evidence_bundle(audit_repository=repository, audit_id="audit-35-cli"))
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    return path


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, capture_output=True, text=True, check=False)


def test_cli_reports_no_review_without_authority_claim(tmp_path) -> None:
    bundle = _bundle_file(tmp_path)
    result = _run("--bundle", str(bundle), "--review-db", str(tmp_path / "reviews.sqlite"), "--resolution-db", str(tmp_path / "resolutions.sqlite"))
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["state"] == "NO_REVIEW"
    assert payload["effective_decision"] is None
    assert payload["send_authorized"] is False
    assert payload["review_is_campaign_authorization"] is False
    assert payload["status_is_observational_only"] is True


def test_cli_rejects_tampered_bundle(tmp_path) -> None:
    bundle_path = _bundle_file(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["snapshot"]["campaign_id"] = "tampered"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    result = _run("--bundle", str(bundle_path), "--review-db", str(tmp_path / "reviews.sqlite"), "--resolution-db", str(tmp_path / "resolutions.sqlite"))
    assert result.returncode == 2
    assert "bundle digest mismatch" in result.stderr
