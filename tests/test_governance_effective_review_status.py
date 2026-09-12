from __future__ import annotations

from datetime import datetime, timedelta, timezone

from searchleads.governance_audit import GovernanceAuditRepository
from searchleads.governance_effective_review_status import (
    EffectiveEvidenceReviewSource,
    EffectiveEvidenceReviewState,
    build_effective_evidence_review_status,
    effective_evidence_review_status_to_mapping,
)
from searchleads.governance_evidence_bundle import build_governance_evidence_bundle, governance_evidence_bundle_to_mapping
from searchleads.governance_evidence_review import EvidenceReviewRepository, process_evidence_review
from searchleads.governance_evidence_review_resolution import (
    EvidenceReviewResolutionRepository,
    process_evidence_review_resolution,
    review_set_sha256,
)
from searchleads.governance_persistence import GovernanceDecisionRepository
from searchleads.governance_preflight import CampaignPreflightScope
from searchleads.governance_snapshot import build_governance_operational_snapshot

NOW = datetime(2026, 9, 12, 6, 0, tzinfo=timezone.utc)


def _bundle(tmp_path):
    db = tmp_path / "state.sqlite"
    scope = CampaignPreflightScope(campaign_id="cmp-35", policy_id="policy-35", policy_version="v1", jurisdiction="BR-RS", channel="email", brasilapi_fresh=False)
    with GovernanceDecisionRepository(db) as repository:
        snapshot = build_governance_operational_snapshot(repository=repository, scope=scope, now=NOW)
    with GovernanceAuditRepository(db) as repository:
        repository.append_snapshot(audit_id="audit-35", snapshot=snapshot)
        return governance_evidence_bundle_to_mapping(build_governance_evidence_bundle(audit_repository=repository, audit_id="audit-35"))


def _review(bundle, review_id, decision, when):
    return {"review_id": review_id, "audit_id": bundle["audit_id"], "bundle_sha256": bundle["bundle_sha256"], "reviewer_reference": f"reviewer:{review_id}", "decision": decision, "reviewed_at": when.isoformat(), "evidence_refs": [f"ticket:{review_id}"], "send_authorized": False, "review_is_campaign_authorization": False}


def _resolution(bundle, review_ids, decision, resolution_id="resolution-35"):
    ordered = tuple(sorted(review_ids))
    return {"resolution_id": resolution_id, "audit_id": bundle["audit_id"], "bundle_sha256": bundle["bundle_sha256"], "review_ids": list(ordered), "review_set_sha256": review_set_sha256(ordered), "resolver_reference": "resolver:human-35", "decision": decision, "resolved_at": (NOW + timedelta(hours=1)).isoformat(), "evidence_refs": ["ticket:RES-35"], "send_authorized": False, "resolution_is_campaign_authorization": False}


def test_no_review_and_unanimous_review_states(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as reviews, EvidenceReviewResolutionRepository(tmp_path / "resolutions.sqlite") as resolutions:
        status = build_effective_evidence_review_status(review_repository=reviews, resolution_repository=resolutions, bundle=bundle)
        assert status.state is EffectiveEvidenceReviewState.NO_REVIEW
        assert status.effective_decision is None
        process_evidence_review(repository=reviews, bundle=bundle, review_payload=_review(bundle, "review-a", "APPROVED", NOW))
        status = build_effective_evidence_review_status(review_repository=reviews, resolution_repository=resolutions, bundle=bundle)
        assert status.state is EffectiveEvidenceReviewState.EFFECTIVE_REVIEW_DECISION
        assert status.effective_decision.value == "APPROVED"
        assert status.decision_source is EffectiveEvidenceReviewSource.CONSOLIDATED_REVIEWS


def test_unresolved_conflict_has_no_effective_decision(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as reviews, EvidenceReviewResolutionRepository(tmp_path / "resolutions.sqlite") as resolutions:
        process_evidence_review(repository=reviews, bundle=bundle, review_payload=_review(bundle, "review-a", "APPROVED", NOW))
        process_evidence_review(repository=reviews, bundle=bundle, review_payload=_review(bundle, "review-b", "REJECTED", NOW + timedelta(minutes=1)))
        status = build_effective_evidence_review_status(review_repository=reviews, resolution_repository=resolutions, bundle=bundle)
        assert status.state is EffectiveEvidenceReviewState.UNRESOLVED_CONFLICT
        assert status.effective_decision is None
        assert status.conflict is True


def test_explicit_resolution_becomes_effective_review_decision_only(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as reviews, EvidenceReviewResolutionRepository(tmp_path / "resolutions.sqlite") as resolutions:
        process_evidence_review(repository=reviews, bundle=bundle, review_payload=_review(bundle, "review-a", "APPROVED", NOW))
        process_evidence_review(repository=reviews, bundle=bundle, review_payload=_review(bundle, "review-b", "REJECTED", NOW + timedelta(minutes=1)))
        process_evidence_review_resolution(review_repository=reviews, resolution_repository=resolutions, bundle=bundle, resolution_payload=_resolution(bundle, ("review-a", "review-b"), "MORE_REVIEW_REQUIRED"))
        status = build_effective_evidence_review_status(review_repository=reviews, resolution_repository=resolutions, bundle=bundle)
        mapping = effective_evidence_review_status_to_mapping(status)
        assert status.state is EffectiveEvidenceReviewState.EFFECTIVE_RESOLVED_DECISION
        assert status.effective_decision.value == "MORE_REVIEW_REQUIRED"
        assert status.decision_source is EffectiveEvidenceReviewSource.HUMAN_CONFLICT_RESOLUTION
        assert mapping["send_authorized"] is False
        assert mapping["review_is_campaign_authorization"] is False
        assert mapping["changes_auth_campaign_001"] is False


def test_new_review_invalidates_effective_resolution(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as reviews, EvidenceReviewResolutionRepository(tmp_path / "resolutions.sqlite") as resolutions:
        process_evidence_review(repository=reviews, bundle=bundle, review_payload=_review(bundle, "review-a", "APPROVED", NOW))
        process_evidence_review(repository=reviews, bundle=bundle, review_payload=_review(bundle, "review-b", "REJECTED", NOW + timedelta(minutes=1)))
        process_evidence_review_resolution(review_repository=reviews, resolution_repository=resolutions, bundle=bundle, resolution_payload=_resolution(bundle, ("review-a", "review-b"), "APPROVED"))
        process_evidence_review(repository=reviews, bundle=bundle, review_payload=_review(bundle, "review-c", "MORE_REVIEW_REQUIRED", NOW + timedelta(minutes=2)))
        status = build_effective_evidence_review_status(review_repository=reviews, resolution_repository=resolutions, bundle=bundle)
        assert status.state is EffectiveEvidenceReviewState.STALE_RESOLUTION
        assert status.effective_decision is None
        assert status.conflict is True


def test_contradictory_resolutions_fail_closed(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as reviews, EvidenceReviewResolutionRepository(tmp_path / "resolutions.sqlite") as resolutions:
        process_evidence_review(repository=reviews, bundle=bundle, review_payload=_review(bundle, "review-a", "APPROVED", NOW))
        process_evidence_review(repository=reviews, bundle=bundle, review_payload=_review(bundle, "review-b", "REJECTED", NOW + timedelta(minutes=1)))
        ids = ("review-a", "review-b")
        process_evidence_review_resolution(review_repository=reviews, resolution_repository=resolutions, bundle=bundle, resolution_payload=_resolution(bundle, ids, "APPROVED", "resolution-a"))
        process_evidence_review_resolution(review_repository=reviews, resolution_repository=resolutions, bundle=bundle, resolution_payload=_resolution(bundle, ids, "REJECTED", "resolution-b"))
        status = build_effective_evidence_review_status(review_repository=reviews, resolution_repository=resolutions, bundle=bundle)
        assert status.state is EffectiveEvidenceReviewState.RESOLUTION_CONFLICT
        assert status.effective_decision is None
        assert status.decision_source is EffectiveEvidenceReviewSource.NONE
