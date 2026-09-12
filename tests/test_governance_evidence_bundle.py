from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import pytest

from searchleads.governance_audit import GovernanceAuditRepository
from searchleads.governance_evidence_bundle import (
    GovernanceEvidenceBundleError,
    build_governance_evidence_bundle,
    governance_evidence_bundle_to_mapping,
    verify_governance_evidence_bundle,
)
from searchleads.governance_persistence import GovernanceDecisionRepository
from searchleads.governance_preflight import CampaignPreflightScope
from searchleads.governance_snapshot import build_governance_operational_snapshot


NOW = datetime(2026, 9, 12, 4, 0, tzinfo=timezone.utc)


def _snapshot(tmp_path, *, fresh: bool):
    scope = CampaignPreflightScope(
        campaign_id="cmp-1",
        policy_id="policy-1",
        policy_version="v1",
        jurisdiction="BR-RS",
        channel="email",
        brasilapi_fresh=fresh,
    )
    with GovernanceDecisionRepository(tmp_path / "governance.sqlite") as repository:
        return build_governance_operational_snapshot(repository=repository, scope=scope, now=NOW)


def _canonical_digest(payload: dict) -> str:
    unsigned = dict(payload)
    unsigned.pop("bundle_sha256", None)
    encoded = json.dumps(
        unsigned,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def test_bundle_is_deterministic_for_same_historical_audit_entry(tmp_path) -> None:
    audit_db = tmp_path / "audit.sqlite"
    with GovernanceAuditRepository(audit_db) as repository:
        repository.append_snapshot(audit_id="audit-1", snapshot=_snapshot(tmp_path, fresh=False))
        first = governance_evidence_bundle_to_mapping(
            build_governance_evidence_bundle(audit_repository=repository, audit_id="audit-1")
        )
        second = governance_evidence_bundle_to_mapping(
            build_governance_evidence_bundle(audit_repository=repository, audit_id="audit-1")
        )

    assert first == second
    assert first["send_authorized"] is False
    assert first["snapshot"]["send_authorized"] is False
    assert first["audit_entry"]["send_authorized"] is False
    verify_governance_evidence_bundle(first)


def test_bundle_contains_chain_from_genesis_to_selected_entry(tmp_path) -> None:
    with GovernanceAuditRepository(tmp_path / "audit.sqlite") as repository:
        first = repository.append_snapshot(audit_id="audit-1", snapshot=_snapshot(tmp_path, fresh=False))
        second = repository.append_snapshot(audit_id="audit-2", snapshot=_snapshot(tmp_path, fresh=True))
        payload = governance_evidence_bundle_to_mapping(
            build_governance_evidence_bundle(audit_repository=repository, audit_id="audit-2")
        )

    headers = payload["chain_headers"]
    assert [header["audit_id"] for header in headers] == ["audit-1", "audit-2"]
    assert headers[0]["previous_entry_hash"] is None
    assert headers[1]["previous_entry_hash"] == first.entry_hash
    assert headers[1]["entry_hash"] == second.entry_hash
    verify_governance_evidence_bundle(payload)


def test_snapshot_tampering_is_rejected(tmp_path) -> None:
    with GovernanceAuditRepository(tmp_path / "audit.sqlite") as repository:
        repository.append_snapshot(audit_id="audit-1", snapshot=_snapshot(tmp_path, fresh=False))
        payload = governance_evidence_bundle_to_mapping(
            build_governance_evidence_bundle(audit_repository=repository, audit_id="audit-1")
        )

    payload["snapshot"]["blockers"] = []
    payload["bundle_sha256"] = _canonical_digest(payload)
    with pytest.raises(GovernanceEvidenceBundleError, match="snapshot digest"):
        verify_governance_evidence_bundle(payload)


def test_chain_header_tampering_is_rejected_even_with_recomputed_bundle_digest(tmp_path) -> None:
    with GovernanceAuditRepository(tmp_path / "audit.sqlite") as repository:
        repository.append_snapshot(audit_id="audit-1", snapshot=_snapshot(tmp_path, fresh=False))
        repository.append_snapshot(audit_id="audit-2", snapshot=_snapshot(tmp_path, fresh=True))
        payload = governance_evidence_bundle_to_mapping(
            build_governance_evidence_bundle(audit_repository=repository, audit_id="audit-2")
        )

    payload["chain_headers"][1]["previous_entry_hash"] = "0" * 64
    payload["bundle_sha256"] = _canonical_digest(payload)
    with pytest.raises(GovernanceEvidenceBundleError, match="predecessor mismatch"):
        verify_governance_evidence_bundle(payload)


def test_missing_audit_id_is_rejected(tmp_path) -> None:
    with GovernanceAuditRepository(tmp_path / "audit.sqlite") as repository:
        with pytest.raises(KeyError):
            build_governance_evidence_bundle(audit_repository=repository, audit_id="missing")
