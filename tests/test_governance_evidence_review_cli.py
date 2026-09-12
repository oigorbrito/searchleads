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
from searchleads.governance_persistence import GovernanceDecisionRepository
from searchleads.governance_preflight import CampaignPreflightScope
from searchleads.governance_snapshot import build_governance_operational_snapshot


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "review_governance_evidence.py"
NOW = datetime(2026, 9, 12, 4, 30, tzinfo=timezone.utc)


def _write_bundle(tmp_path: Path) -> Path:
    state_db = tmp_path / "state.sqlite"
    scope = CampaignPreflightScope(
        campaign_id="cmp-cli",
        policy_id="policy-cli",
        policy_version="v1",
        jurisdiction="BR-RS",
        channel="email",
        brasilapi_fresh=False,
    )
    with GovernanceDecisionRepository(state_db) as repository:
        snapshot = build_governance_operational_snapshot(repository=repository, scope=scope, now=NOW)
    with GovernanceAuditRepository(state_db) as repository:
        repository.append_snapshot(audit_id="audit-cli", snapshot=snapshot)
        bundle = governance_evidence_bundle_to_mapping(
            build_governance_evidence_bundle(audit_repository=repository, audit_id="audit-cli")
        )
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    return path


def _write_review(tmp_path: Path, bundle: dict, **overrides) -> Path:
    payload = {
        "review_id": "review-cli",
        "audit_id": bundle["audit_id"],
        "bundle_sha256": bundle["bundle_sha256"],
        "reviewer_reference": "reviewer:bob",
        "decision": "MORE_REVIEW_REQUIRED",
        "reviewed_at": NOW.isoformat(),
        "evidence_refs": ["ticket:CLI-REVIEW-1"],
        "note": "external review of exact bundle",
        "send_authorized": False,
        "review_is_campaign_authorization": False,
    }
    payload.update(overrides)
    path = tmp_path / "review.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_records_and_lists_review_bound_to_bundle(tmp_path) -> None:
    bundle_path = _write_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    review_path = _write_review(tmp_path, bundle)
    review_db = tmp_path / "reviews.sqlite"

    record = _run(
        "record",
        "--bundle",
        str(bundle_path),
        "--review",
        str(review_path),
        "--db",
        str(review_db),
    )
    assert record.returncode == 0, record.stderr
    recorded = json.loads(record.stdout)
    assert recorded["storage_action"] == "INSERTED"
    assert recorded["audit_id"] == bundle["audit_id"]
    assert recorded["bundle_sha256"] == bundle["bundle_sha256"]
    assert recorded["send_authorized"] is False
    assert recorded["review_is_campaign_authorization"] is False

    listing = _run(
        "list",
        "--bundle",
        str(bundle_path),
        "--db",
        str(review_db),
    )
    assert listing.returncode == 0, listing.stderr
    listed = json.loads(listing.stdout)
    assert listed["send_authorized"] is False
    assert listed["reviews_are_campaign_authorization"] is False
    assert len(listed["reviews"]) == 1
    assert listed["reviews"][0]["review_id"] == "review-cli"


def test_cli_rejects_review_for_different_bundle_digest(tmp_path) -> None:
    bundle_path = _write_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    review_path = _write_review(tmp_path, bundle, bundle_sha256="0" * 64)
    result = _run(
        "record",
        "--bundle",
        str(bundle_path),
        "--review",
        str(review_path),
        "--db",
        str(tmp_path / "reviews.sqlite"),
    )
    assert result.returncode == 2
    assert "bundle_sha256 does not match" in result.stderr


def test_cli_rejects_tampered_bundle_before_review_persistence(tmp_path) -> None:
    bundle_path = _write_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    review_path = _write_review(tmp_path, bundle)
    bundle["snapshot"]["policy_id"] = "tampered"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    result = _run(
        "record",
        "--bundle",
        str(bundle_path),
        "--review",
        str(review_path),
        "--db",
        str(tmp_path / "reviews.sqlite"),
    )
    assert result.returncode == 2
    assert "bundle digest mismatch" in result.stderr
