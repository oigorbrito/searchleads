from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from searchleads.governance_audit import GovernanceAuditRepository
from searchleads.governance_evidence_bundle import build_governance_evidence_bundle, governance_evidence_bundle_to_mapping
from searchleads.governance_evidence_review import EvidenceReviewRepository, process_evidence_review
from searchleads.governance_persistence import GovernanceDecisionRepository
from searchleads.governance_preflight import CampaignPreflightScope
from searchleads.governance_snapshot import build_governance_operational_snapshot

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_governance_effective_review.py"
NOW = datetime(2026, 9, 12, 6, 30, tzinfo=timezone.utc)


def _bundle(tmp_path: Path) -> Path:
    state_db = tmp_path / "state.sqlite"
    scope = CampaignPreflightScope(campaign_id="cmp-cli-36", policy_id="policy-cli-36", policy_version="v1", jurisdiction="BR-RS", channel="email", brasilapi_fresh=False)
    with GovernanceDecisionRepository(state_db) as repository:
        snapshot = build_governance_operational_snapshot(repository=repository, scope=scope, now=NOW)
    with GovernanceAuditRepository(state_db) as repository:
        repository.append_snapshot(audit_id="audit-cli-36", snapshot=snapshot)
        bundle = governance_evidence_bundle_to_mapping(build_governance_evidence_bundle(audit_repository=repository, audit_id="audit-cli-36"))
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    return path


def _seed_review(tmp_path: Path, bundle: dict) -> Path:
    db = tmp_path / "reviews.sqlite"
    payload = {
        "review_id": "review-cli-36",
        "audit_id": bundle["audit_id"],
        "bundle_sha256": bundle["bundle_sha256"],
        "reviewer_reference": "reviewer:cli-36",
        "decision": "APPROVED",
        "reviewed_at": NOW.isoformat(),
        "evidence_refs": ["ticket:CLI-36"],
        "send_authorized": False,
        "review_is_campaign_authorization": False,
    }
    with EvidenceReviewRepository(db) as repository:
        process_evidence_review(repository=repository, bundle=bundle, review_payload=payload)
    return db


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, capture_output=True, text=True, check=False)


def test_cli_record_verify_and_list(tmp_path) -> None:
    bundle_path = _bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    review_db = _seed_review(tmp_path, bundle)
    resolution_db = tmp_path / "resolutions.sqlite"
    audit_db = tmp_path / "effective-audit.sqlite"

    recorded = _run("record", "--bundle", str(bundle_path), "--review-db", str(review_db), "--resolution-db", str(resolution_db), "--audit-db", str(audit_db), "--audit-entry-id", "effective-audit-cli-1")
    assert recorded.returncode == 0, recorded.stderr
    payload = json.loads(recorded.stdout)
    assert payload["storage_action"] == "INSERTED"
    assert payload["status"]["effective_decision"] == "APPROVED"
    assert payload["send_authorized"] is False

    verified = _run("verify", "--audit-db", str(audit_db))
    assert verified.returncode == 0, verified.stderr
    verify_payload = json.loads(verified.stdout)
    assert verify_payload["valid"] is True
    assert verify_payload["entry_count"] == 1

    listing = _run("list", "--audit-db", str(audit_db))
    assert listing.returncode == 0, listing.stderr
    list_payload = json.loads(listing.stdout)
    assert len(list_payload["entries"]) == 1
    assert list_payload["audit_is_campaign_authorization"] is False


def test_cli_rejects_tampered_bundle_before_record(tmp_path) -> None:
    bundle_path = _bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    review_db = _seed_review(tmp_path, bundle)
    bundle["snapshot"]["campaign_id"] = "tampered"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    result = _run("record", "--bundle", str(bundle_path), "--review-db", str(review_db), "--resolution-db", str(tmp_path / "resolutions.sqlite"), "--audit-db", str(tmp_path / "audit.sqlite"), "--audit-entry-id", "effective-audit-cli-1")
    assert result.returncode == 2
    assert "bundle digest mismatch" in result.stderr
