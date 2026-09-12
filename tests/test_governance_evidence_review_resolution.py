from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from searchleads.governance_audit import GovernanceAuditRepository
from searchleads.governance_evidence_bundle import build_governance_evidence_bundle, governance_evidence_bundle_to_mapping
from searchleads.governance_evidence_review import EvidenceReviewRepository, process_evidence_review
from searchleads.governance_evidence_review_resolution import (
    EvidenceReviewResolutionConflictError,
    EvidenceReviewResolutionRepository,
    EvidenceReviewResolutionState,
    build_evidence_review_resolution_status,
    process_evidence_review_resolution,
    review_set_sha256,
)
from searchleads.governance_persistence import GovernanceDecisionRepository
from searchleads.governance_preflight import CampaignPreflightScope
from searchleads.governance_snapshot import build_governance_operational_snapshot

NOW = datetime(2026, 9, 12, 5, 0, tzinfo=timezone.utc)


def _bundle(tmp_path):
    db = tmp_path / "state.sqlite"
    scope = CampaignPreflightScope(campaign_id="cmp-34", policy_id="policy-34", policy_version="v1", jurisdiction="BR-RS", channel="email", brasilapi_fresh=False)
    with GovernanceDecisionRepository(db) as repository:
        snapshot = build_governance_operational_snapshot(repository=repository, scope=scope, now=NOW)
    with GovernanceAuditRepository(db) as repository:
        repository.append_snapshot(audit_id="audit-34", snapshot=snapshot)
        return governance_evidence_bundle_to_mapping(build_governance_evidence_bundle(audit_repository=repository, audit_id="audit-34"))


def _review(bundle, review_id, decision, when):
    return {"review_id": review_id, "audit_id": bundle["audit_id"], "bundle_sha256": bundle["bundle_sha256"], "reviewer_reference": f"reviewer:{review_id}", "decision": decision, "reviewed_at": when.isoformat(), "evidence_refs": [f"ticket:{review_id}"], "send_authorized": False, "review_is_campaign_authorization": False}


def _resolution(bundle, review_ids, decision="APPROVED", resolution_id="resolution-1", when=NOW + timedelta(hours=1)):
    ordered = tuple(sorted(review_ids))
    return {"resolution_id": resolution_id, "audit_id": bundle["audit_id"], "bundle_sha256": bundle["bundle_sha256"], "review_ids": list(ordered), "review_set_sha256": review_set_sha256(ordered), "resolver_reference": "resolver:human-1", "decision": decision, "resolved_at": when.isoformat(), "evidence_refs": ["ticket:RES-34"], "note": "explicit human conflict disposition", "send_authorized": False, "resolution_is_campaign_authorization": False}


def _seed_conflict(repository, bundle):
    process_evidence_review(repository=repository, bundle=bundle, review_payload=_review(bundle, "review-a", "APPROVED", NOW))
    process_evidence_review(repository=repository, bundle=bundle, review_payload=_review(bundle, "review-b", "REJECTED", NOW + timedelta(minutes=1)))


def test_resolution_requires_current_conflict_and_exact_review_set(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as reviews, EvidenceReviewResolutionRepository(tmp_path / "resolutions.sqlite") as resolutions:
        with pytest.raises(ValueError, match="current CONFLICT"):
            process_evidence_review_resolution(review_repository=reviews, resolution_repository=resolutions, bundle=bundle, resolution_payload=_resolution(bundle, ("review-a",)))
        _seed_conflict(reviews, bundle)
        with pytest.raises(ValueError, match="exact current review set"):
            process_evidence_review_resolution(review_repository=reviews, resolution_repository=resolutions, bundle=bundle, resolution_payload=_resolution(bundle, ("review-a",)))
        record, inserted = process_evidence_review_resolution(review_repository=reviews, resolution_repository=resolutions, bundle=bundle, resolution_payload=_resolution(bundle, ("review-a", "review-b")))
        assert inserted is True
        assert record.send_authorized is False
        status = build_evidence_review_resolution_status(review_repository=reviews, resolution_repository=resolutions, bundle=bundle)
        assert status.state is EvidenceReviewResolutionState.RESOLVED
        assert status.effective_decision.value == "APPROVED"


def test_new_review_makes_prior_resolution_stale(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as reviews, EvidenceReviewResolutionRepository(tmp_path / "resolutions.sqlite") as resolutions:
        _seed_conflict(reviews, bundle)
        process_evidence_review_resolution(review_repository=reviews, resolution_repository=resolutions, bundle=bundle, resolution_payload=_resolution(bundle, ("review-a", "review-b")))
        process_evidence_review(repository=reviews, bundle=bundle, review_payload=_review(bundle, "review-c", "MORE_REVIEW_REQUIRED", NOW + timedelta(minutes=2)))
        status = build_evidence_review_resolution_status(review_repository=reviews, resolution_repository=resolutions, bundle=bundle)
        assert status.state is EvidenceReviewResolutionState.STALE_RESOLUTION
        assert status.effective_decision is None
        assert status.stale_resolution_ids == ("resolution-1",)


def test_contradictory_resolutions_are_not_auto_resolved(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as reviews, EvidenceReviewResolutionRepository(tmp_path / "resolutions.sqlite") as resolutions:
        _seed_conflict(reviews, bundle)
        ids = ("review-a", "review-b")
        process_evidence_review_resolution(review_repository=reviews, resolution_repository=resolutions, bundle=bundle, resolution_payload=_resolution(bundle, ids, decision="APPROVED", resolution_id="resolution-a"))
        process_evidence_review_resolution(review_repository=reviews, resolution_repository=resolutions, bundle=bundle, resolution_payload=_resolution(bundle, ids, decision="REJECTED", resolution_id="resolution-b", when=NOW + timedelta(hours=2)))
        status = build_evidence_review_resolution_status(review_repository=reviews, resolution_repository=resolutions, bundle=bundle)
        assert status.state is EvidenceReviewResolutionState.RESOLUTION_CONFLICT
        assert status.effective_decision is None
        assert set(decision.value for decision in status.conflicting_decisions) == {"APPROVED", "REJECTED"}
        assert status.latest_resolution_id == "resolution-b"


def test_resolution_id_is_immutable_and_replay_idempotent(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as reviews, EvidenceReviewResolutionRepository(tmp_path / "resolutions.sqlite") as resolutions:
        _seed_conflict(reviews, bundle)
        payload = _resolution(bundle, ("review-a", "review-b"))
        _, inserted = process_evidence_review_resolution(review_repository=reviews, resolution_repository=resolutions, bundle=bundle, resolution_payload=payload)
        _, replayed = process_evidence_review_resolution(review_repository=reviews, resolution_repository=resolutions, bundle=bundle, resolution_payload=payload)
        assert inserted is True and replayed is False
        changed = dict(payload)
        changed["decision"] = "REJECTED"
        with pytest.raises(EvidenceReviewResolutionConflictError):
            process_evidence_review_resolution(review_repository=reviews, resolution_repository=resolutions, bundle=bundle, resolution_payload=changed)


def test_tampered_bundle_and_authority_claims_fail_closed(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as reviews, EvidenceReviewResolutionRepository(tmp_path / "resolutions.sqlite") as resolutions:
        _seed_conflict(reviews, bundle)
        payload = _resolution(bundle, ("review-a", "review-b"))
        bad = dict(payload)
        bad["send_authorized"] = True
        with pytest.raises(ValueError, match="must not authorize"):
            process_evidence_review_resolution(review_repository=reviews, resolution_repository=resolutions, bundle=bundle, resolution_payload=bad)
        tampered = dict(bundle)
        tampered["snapshot"] = dict(bundle["snapshot"])
        tampered["snapshot"]["campaign_id"] = "tampered"
        with pytest.raises(RuntimeError, match="bundle digest mismatch"):
            process_evidence_review_resolution(review_repository=reviews, resolution_repository=resolutions, bundle=tampered, resolution_payload=payload)
