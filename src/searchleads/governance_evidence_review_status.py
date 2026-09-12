from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping

from .governance_evidence_bundle import verify_governance_evidence_bundle
from .governance_evidence_review import (
    EvidenceReviewDecision,
    EvidenceReviewRecord,
    EvidenceReviewRepository,
    evidence_review_to_mapping,
)


class ConsolidatedEvidenceReviewState(StrEnum):
    NO_REVIEW = "NO_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MORE_REVIEW_REQUIRED = "MORE_REVIEW_REQUIRED"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True, slots=True)
class ConsolidatedEvidenceReviewStatus:
    audit_id: str
    bundle_sha256: str
    state: ConsolidatedEvidenceReviewState
    reviews: tuple[EvidenceReviewRecord, ...]
    latest_review_id: str | None
    conflict: bool
    conflicting_decisions: tuple[EvidenceReviewDecision, ...]
    send_authorized: bool = False
    review_is_campaign_authorization: bool = False

    def __post_init__(self) -> None:
        if not self.audit_id.strip():
            raise ValueError("audit_id must not be blank")
        if len(self.bundle_sha256) != 64:
            raise ValueError("bundle_sha256 must be a SHA-256 hex digest")
        if self.send_authorized:
            raise ValueError("consolidated evidence review cannot authorize send")
        if self.review_is_campaign_authorization:
            raise ValueError("consolidated evidence review cannot authorize a campaign")


def _state_for_reviews(reviews: tuple[EvidenceReviewRecord, ...]) -> tuple[ConsolidatedEvidenceReviewState, bool, tuple[EvidenceReviewDecision, ...]]:
    if not reviews:
        return ConsolidatedEvidenceReviewState.NO_REVIEW, False, ()
    decisions = tuple(sorted({review.decision for review in reviews}, key=lambda item: item.value))
    if len(decisions) > 1:
        return ConsolidatedEvidenceReviewState.CONFLICT, True, decisions
    decision = decisions[0]
    return ConsolidatedEvidenceReviewState(decision.value), False, decisions


def consolidate_evidence_reviews(
    *,
    repository: EvidenceReviewRepository,
    bundle: Mapping[str, Any],
) -> ConsolidatedEvidenceReviewStatus:
    """Return read-only human-review state for one fully verified evidence bundle."""
    verify_governance_evidence_bundle(dict(bundle))
    audit_id = bundle.get("audit_id")
    bundle_sha256 = bundle.get("bundle_sha256")
    if not isinstance(audit_id, str) or not audit_id.strip():
        raise ValueError("verified bundle is missing audit_id")
    if not isinstance(bundle_sha256, str) or len(bundle_sha256) != 64:
        raise ValueError("verified bundle is missing bundle_sha256")

    reviews = repository.list_for_bundle(audit_id=audit_id, bundle_sha256=bundle_sha256)
    state, conflict, conflicting_decisions = _state_for_reviews(reviews)
    latest_review_id = max(reviews, key=lambda review: (review.reviewed_at, review.review_id)).review_id if reviews else None
    return ConsolidatedEvidenceReviewStatus(
        audit_id=audit_id,
        bundle_sha256=bundle_sha256,
        state=state,
        reviews=reviews,
        latest_review_id=latest_review_id,
        conflict=conflict,
        conflicting_decisions=conflicting_decisions,
        send_authorized=False,
        review_is_campaign_authorization=False,
    )


def consolidated_evidence_review_status_to_mapping(status: ConsolidatedEvidenceReviewStatus) -> dict[str, Any]:
    return {
        "audit_id": status.audit_id,
        "bundle_sha256": status.bundle_sha256,
        "state": status.state.value,
        "review_count": len(status.reviews),
        "latest_review_id": status.latest_review_id,
        "conflict": status.conflict,
        "conflicting_decisions": [decision.value for decision in status.conflicting_decisions],
        "reviews": [evidence_review_to_mapping(review) for review in status.reviews],
        "send_authorized": False,
        "review_is_campaign_authorization": False,
        "changes_preflight": False,
        "changes_pilot_release": False,
        "changes_legal_signoff": False,
        "changes_professional_verification": False,
        "changes_source_freshness": False,
    }


__all__ = [
    "ConsolidatedEvidenceReviewState",
    "ConsolidatedEvidenceReviewStatus",
    "consolidate_evidence_reviews",
    "consolidated_evidence_review_status_to_mapping",
]
