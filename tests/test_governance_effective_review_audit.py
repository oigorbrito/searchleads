from __future__ import annotations

from datetime import datetime, timezone

import pytest

from searchleads.governance_audit import GovernanceAuditRepository
from searchleads.governance_effective_review_audit import (
    EffectiveReviewAuditConflictError,
    EffectiveReviewAuditIntegrityError,
    EffectiveReviewAuditRepository,
)
from searchleads.governance_effective_review_status import build_effective_evidence_review_status
from searchleads.governance_evidence_bundle import build_governance_evidence_bundle, governance_evidence_bundle_to_mapping
from searchleads.governance_evidence_review import EvidenceReviewRepository, process_evidence_review
from searchleads.governance_evidence_review_resolution import EvidenceReviewResolutionRepository
from searchleads.governance_persistence import GovernanceDecisionRepository
from searchleads.governance_preflight import CampaignPreflightScope
from searchleads.governance_snapshot import build_governance_operational_snapshot

NOW = datetime(2026, 9, 12, 6, 0, tzinfo=timezone.utc)


def _bundle(tmp_path):
    db = tmp_path / "state.sqlite"
    scope = CampaignPreflightScope(campaign_id="cmp-36", policy_id="policy-36", policy_version="v1", jurisdiction="BR-RS", channel="email", brasilapi_fresh=False)
    with GovernanceDecisionRepository(db) as repository:
        snapshot = build_governance_operational_snapshot(repository=repository, scope=scope, now=NOW)
    with GovernanceAuditRepository(db) as repository:
        repository.append_snapshot(audit_id="audit-36", snapshot=snapshot)
        return governance_evidence_bundle_to_mapping(build_governance_evidence_bundle(audit_repository=repository, audit_id="audit-36"))


def _review(bundle, review_id="review-36", decision="APPROVED"):
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


def _status(tmp_path, bundle, *, decision="APPROVED"):
    review_db = tmp_path / "reviews.sqlite"
    resolution_db = tmp_path / "resolutions.sqlite"
    with EvidenceReviewRepository(review_db) as reviews, EvidenceReviewResolutionRepository(resolution_db) as resolutions:
        process_evidence_review(repository=reviews, bundle=bundle, review_payload=_review(bundle, decision=decision))
        return build_effective_evidence_review_status(review_repository=reviews, resolution_repository=resolutions, bundle=bundle)


def test_append_and_verify_effective_review_audit_chain(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    status = _status(tmp_path, bundle)
    with EffectiveReviewAuditRepository(tmp_path / "audit.sqlite") as repository:
        first, inserted = repository.append_status(audit_entry_id="effective-audit-1", status=status)
        replay, replay_inserted = repository.append_status(audit_entry_id="effective-audit-1", status=status)
        assert inserted is True
        assert replay_inserted is False
        assert replay == first
        assert first.previous_entry_hash is None
        assert first.status["send_authorized"] is False
        entries = repository.verify_chain()
        assert entries == (first,)


def test_same_audit_entry_id_with_changed_status_conflicts(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    status = _status(tmp_path, bundle)
    with EffectiveReviewAuditRepository(tmp_path / "audit.sqlite") as repository:
        repository.append_status(audit_entry_id="effective-audit-1", status=status)
        changed = status.__class__(
            audit_id=status.audit_id,
            bundle_sha256=status.bundle_sha256,
            state=status.state,
            effective_decision=status.effective_decision,
            decision_source=status.decision_source,
            review_ids=("other-review",),
            applicable_resolution_ids=status.applicable_resolution_ids,
            stale_resolution_ids=status.stale_resolution_ids,
            conflict=status.conflict,
        )
        with pytest.raises(EffectiveReviewAuditConflictError):
            repository.append_status(audit_entry_id="effective-audit-1", status=changed)


def test_status_tampering_is_detected(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    status = _status(tmp_path, bundle)
    db = tmp_path / "audit.sqlite"
    with EffectiveReviewAuditRepository(db) as repository:
        repository.append_status(audit_entry_id="effective-audit-1", status=status)
        repository._connection.execute(
            "UPDATE governance_effective_review_audit SET status_json = ? WHERE audit_entry_id = ?",
            ('{"send_authorized":true}', "effective-audit-1"),
        )
        repository._connection.commit()
        with pytest.raises(EffectiveReviewAuditIntegrityError):
            repository.verify_chain()


def test_predecessor_tampering_is_detected(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    status = _status(tmp_path, bundle)
    db = tmp_path / "audit.sqlite"
    with EffectiveReviewAuditRepository(db) as repository:
        repository.append_status(audit_entry_id="effective-audit-1", status=status)
        repository.append_status(audit_entry_id="effective-audit-2", status=status)
        repository._connection.execute(
            "UPDATE governance_effective_review_audit SET previous_entry_hash = ? WHERE audit_entry_id = ?",
            ("0" * 64, "effective-audit-2"),
        )
        repository._connection.commit()
        with pytest.raises(EffectiveReviewAuditIntegrityError, match="predecessor mismatch"):
            repository.verify_chain()
