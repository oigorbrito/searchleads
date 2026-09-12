from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from searchleads.governance_audit import GovernanceAuditRepository
from searchleads.governance_evidence_bundle import build_governance_evidence_bundle, governance_evidence_bundle_to_mapping
from searchleads.governance_evidence_review import EvidenceReviewRepository, process_evidence_review
from searchleads.governance_evidence_review_resolution import review_set_sha256
from searchleads.governance_persistence import GovernanceDecisionRepository
from searchleads.governance_preflight import CampaignPreflightScope
from searchleads.governance_snapshot import build_governance_operational_snapshot

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "resolve_governance_evidence_review.py"
NOW = datetime(2026, 9, 12, 5, 30, tzinfo=timezone.utc)


def _fixture(tmp_path: Path):
    state_db = tmp_path / "state.sqlite"
    scope = CampaignPreflightScope(campaign_id="cmp-cli-34", policy_id="policy-cli-34", policy_version="v1", jurisdiction="BR-RS", channel="email", brasilapi_fresh=False)
    with GovernanceDecisionRepository(state_db) as repository:
        snapshot = build_governance_operational_snapshot(repository=repository, scope=scope, now=NOW)
    with GovernanceAuditRepository(state_db) as repository:
        repository.append_snapshot(audit_id="audit-cli-34", snapshot=snapshot)
        bundle = governance_evidence_bundle_to_mapping(build_governance_evidence_bundle(audit_repository=repository, audit_id="audit-cli-34"))
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    review_db = tmp_path / "reviews.sqlite"
    with EvidenceReviewRepository(review_db) as repository:
        for review_id, decision, offset in (("review-cli-a", "APPROVED", 0), ("review-cli-b", "REJECTED", 1)):
            process_evidence_review(repository=repository, bundle=bundle, review_payload={"review_id": review_id, "audit_id": bundle["audit_id"], "bundle_sha256": bundle["bundle_sha256"], "reviewer_reference": f"reviewer:{review_id}", "decision": decision, "reviewed_at": (NOW + timedelta(minutes=offset)).isoformat(), "evidence_refs": [f"ticket:{review_id}"], "send_authorized": False, "review_is_campaign_authorization": False})
    ids = ("review-cli-a", "review-cli-b")
    payload = {"resolution_id": "resolution-cli", "audit_id": bundle["audit_id"], "bundle_sha256": bundle["bundle_sha256"], "review_ids": list(ids), "review_set_sha256": review_set_sha256(ids), "resolver_reference": "resolver:cli-human", "decision": "MORE_REVIEW_REQUIRED", "resolved_at": (NOW + timedelta(hours=1)).isoformat(), "evidence_refs": ["ticket:CLI-RES-34"], "send_authorized": False, "resolution_is_campaign_authorization": False}
    resolution_path = tmp_path / "resolution.json"
    resolution_path.write_text(json.dumps(payload), encoding="utf-8")
    return bundle_path, review_db, resolution_path


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, capture_output=True, text=True, check=False)


def test_cli_records_resolution_and_reports_effective_state(tmp_path) -> None:
    bundle, review_db, resolution = _fixture(tmp_path)
    resolution_db = tmp_path / "resolutions.sqlite"
    result = _run("record", "--bundle", str(bundle), "--review-db", str(review_db), "--resolution-db", str(resolution_db), "--resolution", str(resolution))
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["storage_action"] == "INSERTED"
    assert payload["send_authorized"] is False
    status = _run("status", "--bundle", str(bundle), "--review-db", str(review_db), "--resolution-db", str(resolution_db))
    assert status.returncode == 0, status.stderr
    current = json.loads(status.stdout)
    assert current["state"] == "RESOLVED"
    assert current["effective_decision"] == "MORE_REVIEW_REQUIRED"
    assert current["resolution_is_campaign_authorization"] is False
    assert current["changes_auth_campaign_001"] is False


def test_cli_rejects_wrong_review_set(tmp_path) -> None:
    bundle, review_db, resolution = _fixture(tmp_path)
    payload = json.loads(resolution.read_text(encoding="utf-8"))
    payload["review_ids"] = ["review-cli-a"]
    payload["review_set_sha256"] = review_set_sha256(("review-cli-a",))
    resolution.write_text(json.dumps(payload), encoding="utf-8")
    result = _run("record", "--bundle", str(bundle), "--review-db", str(review_db), "--resolution-db", str(tmp_path / "resolutions.sqlite"), "--resolution", str(resolution))
    assert result.returncode == 2
    assert "exact current review set" in result.stderr
