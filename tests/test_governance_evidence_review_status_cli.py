from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from searchleads.governance_audit import GovernanceAuditRepository
from searchleads.governance_evidence_bundle import (
    build_governance_evidence_bundle,
    governance_evidence_bundle_to_mapping,
)
from searchleads.governance_evidence_review import EvidenceReviewRepository, process_evidence_review
from searchleads.governance_persistence import GovernanceDecisionRepository
from searchleads.governance_preflight import CampaignPreflightScope
from searchleads.governance_snapshot import build_governance_operational_snapshot


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "show_governance_evidence_review_status.py"
NOW = datetime(2026, 9, 12, 5, 0, tzinfo=timezone.utc)


def _bundle(tmp_path: Path) -> tuple[Path, dict]:
    state_db = tmp_path / "state.sqlite"
    scope = CampaignPreflightScope(
        campaign_id="cmp-status",
        policy_id="policy-status",
        policy_version="v1",
        jurisdiction="BR-RS",
        channel="email",
        brasilapi_fresh=False,
    )
    with GovernanceDecisionRepository(state_db) as repository:
        snapshot = build_governance_operational_snapshot(repository=repository, scope=scope, now=NOW)
    with GovernanceAuditRepository(state_db) as repository:
        repository.append_snapshot(audit_id="audit-status", snapshot=snapshot)
        bundle = governance_evidence_bundle_to_mapping(
            build_governance_evidence_bundle(audit_repository=repository, audit_id="audit-status")
        )
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    return path, bundle


def _review(bundle: dict, review_id: str, decision: str) -> dict:
    return {
        "review_id": review_id,
        "audit_id": bundle["audit_id"],
        "bundle_sha256": bundle["bundle_sha256"],
        "reviewer_reference": f"reviewer:{review_id}",
        "decision": decision,
        "reviewed_at": NOW.isoformat(),
        "evidence_refs": [f"ticket:{review_id}"],
        "send_authorized": False,
        "review_is_campaign_authorization": False,
    }


def _run(bundle_path: Path, review_db: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--bundle", str(bundle_path), "--db", str(review_db)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_reports_no_review(tmp_path) -> None:
    bundle_path, _ = _bundle(tmp_path)
    result = _run(bundle_path, tmp_path / "reviews.sqlite")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["state"] == "NO_REVIEW"
    assert payload["review_count"] == 0
    assert payload["send_authorized"] is False
    assert payload["review_is_campaign_authorization"] is False


def test_cli_reports_conflict_without_resolving_it(tmp_path) -> None:
    bundle_path, bundle = _bundle(tmp_path)
    review_db = tmp_path / "reviews.sqlite"
    with EvidenceReviewRepository(review_db) as repository:
        process_evidence_review(repository=repository, bundle=bundle, review_payload=_review(bundle, "review-a", "APPROVED"))
        process_evidence_review(repository=repository, bundle=bundle, review_payload=_review(bundle, "review-b", "MORE_REVIEW_REQUIRED"))
    result = _run(bundle_path, review_db)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["state"] == "CONFLICT"
    assert payload["conflict"] is True
    assert set(payload["conflicting_decisions"]) == {"APPROVED", "MORE_REVIEW_REQUIRED"}
    assert payload["latest_review_id"] == "review-b"


def test_cli_rejects_tampered_bundle(tmp_path) -> None:
    bundle_path, bundle = _bundle(tmp_path)
    bundle["snapshot"]["policy_id"] = "tampered"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    result = _run(bundle_path, tmp_path / "reviews.sqlite")
    assert result.returncode == 2
    assert "bundle digest mismatch" in result.stderr
