from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from searchleads.governance_audit import GovernanceAuditRepository
from searchleads.governance_evidence_bundle import (
    build_governance_evidence_bundle,
    governance_evidence_bundle_to_mapping,
)
from searchleads.governance_evidence_review import EvidenceReviewRepository, process_evidence_review
from searchleads.governance_evidence_review_status import (
    ConsolidatedEvidenceReviewState,
    consolidate_evidence_reviews,
    consolidated_evidence_review_status_to_mapping,
)
from searchleads.governance_persistence import GovernanceDecisionRepository
from searchleads.governance_preflight import CampaignPreflightScope
from searchleads.governance_snapshot import build_governance_operational_snapshot


NOW = datetime(2026, 9, 12, 4, 0, tzinfo=timezone.utc)


def _bundle(tmp_path):
    db = tmp_path / "state.sqlite"
    scope = CampaignPreflightScope(
        campaign_id="cmp-1",
        policy_id="policy-1",
        policy_version="v1",
        jurisdiction="BR-RS",
        channel="email",
        brasilapi_fresh=False,
    )
    with GovernanceDecisionRepository(db) as repository:
        snapshot = build_governance_operational_snapshot(repository=repository, scope=scope, now=NOW)
    with GovernanceAuditRepository(db) as repository:
        repository.append_snapshot(audit_id="audit-1", snapshot=snapshot)
        bundle = build_governance_evidence_bundle(audit_repository=repository, audit_id="audit-1")
    return governance_evidence_bundle_to_mapping(bundle)


def _review(bundle, review_id, decision, reviewed_at, reviewer="reviewer:alice"):
    return {
        "review_id": review_id,
        "audit_id": bundle["audit_id"],
        "bundle_sha256": bundle["bundle_sha256"],
        "reviewer_reference": reviewer,
        "decision": decision,
        "reviewed_at": reviewed_at.isoformat(),
        "evidence_refs": [f"ticket:{review_id}"],
        "note": "reviewed exact exported artifact",
        "send_authorized": False,
        "review_is_campaign_authorization": False,
    }


def test_no_review(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as repository:
        status = consolidate_evidence_reviews(repository=repository, bundle=bundle)
    assert status.state is ConsolidatedEvidenceReviewState.NO_REVIEW
    assert status.latest_review_id is None
    assert status.conflict is False
    assert status.send_authorized is False


@pytest.mark.parametrize("decision", ["APPROVED", "REJECTED", "MORE_REVIEW_REQUIRED"])
def test_single_review_consolidates_to_its_decision(tmp_path, decision) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as repository:
        process_evidence_review(repository=repository, bundle=bundle, review_payload=_review(bundle, "review-1", decision, NOW))
        status = consolidate_evidence_reviews(repository=repository, bundle=bundle)
    assert status.state.value == decision
    assert status.latest_review_id == "review-1"
    assert status.conflict is False


def test_multiple_equal_reviews_preserve_history_without_conflict(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as repository:
        process_evidence_review(repository=repository, bundle=bundle, review_payload=_review(bundle, "review-1", "APPROVED", NOW))
        process_evidence_review(repository=repository, bundle=bundle, review_payload=_review(bundle, "review-2", "APPROVED", NOW + timedelta(minutes=1), "reviewer:bob"))
        status = consolidate_evidence_reviews(repository=repository, bundle=bundle)
    assert status.state is ConsolidatedEvidenceReviewState.APPROVED
    assert [review.review_id for review in status.reviews] == ["review-1", "review-2"]
    assert status.latest_review_id == "review-2"


def test_contradictory_reviews_are_conflict_and_never_auto_resolved(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as repository:
        process_evidence_review(repository=repository, bundle=bundle, review_payload=_review(bundle, "review-1", "APPROVED", NOW))
        process_evidence_review(repository=repository, bundle=bundle, review_payload=_review(bundle, "review-2", "REJECTED", NOW + timedelta(minutes=1), "reviewer:bob"))
        status = consolidate_evidence_reviews(repository=repository, bundle=bundle)
    assert status.state is ConsolidatedEvidenceReviewState.CONFLICT
    assert status.conflict is True
    assert status.latest_review_id == "review-2"
    assert {item.value for item in status.conflicting_decisions} == {"APPROVED", "REJECTED"}
    mapped = consolidated_evidence_review_status_to_mapping(status)
    assert mapped["send_authorized"] is False
    assert mapped["review_is_campaign_authorization"] is False
    assert mapped["changes_preflight"] is False


def test_latest_review_order_uses_timestamp_then_review_id(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as repository:
        process_evidence_review(repository=repository, bundle=bundle, review_payload=_review(bundle, "review-a", "APPROVED", NOW))
        process_evidence_review(repository=repository, bundle=bundle, review_payload=_review(bundle, "review-b", "APPROVED", NOW))
        status = consolidate_evidence_reviews(repository=repository, bundle=bundle)
    assert status.latest_review_id == "review-b"


def test_wrong_bundle_binding_cannot_appear_in_status(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as repository:
        with pytest.raises(ValueError, match="audit_id does not match"):
            process_evidence_review(
                repository=repository,
                bundle=bundle,
                review_payload={**_review(bundle, "review-1", "APPROVED", NOW), "audit_id": "audit-other"},
            )
        status = consolidate_evidence_reviews(repository=repository, bundle=bundle)
    assert status.state is ConsolidatedEvidenceReviewState.NO_REVIEW


def test_tampered_bundle_cannot_be_queried_as_valid(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    bundle["snapshot"]["campaign_id"] = "tampered"
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as repository:
        with pytest.raises(RuntimeError, match="bundle digest mismatch"):
            consolidate_evidence_reviews(repository=repository, bundle=bundle)
