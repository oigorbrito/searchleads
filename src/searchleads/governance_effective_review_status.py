from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping

from .governance_evidence_review import EvidenceReviewDecision, EvidenceReviewRepository
from .governance_evidence_review_resolution import (
    EvidenceReviewResolutionRepository,
    EvidenceReviewResolutionState,
    build_evidence_review_resolution_status,
)
from .governance_evidence_review_status import (
    ConsolidatedEvidenceReviewState,
    consolidate_evidence_reviews,
)


class EffectiveEvidenceReviewState(StrEnum):
    NO_REVIEW = "NO_REVIEW"
    EFFECTIVE_REVIEW_DECISION = "EFFECTIVE_REVIEW_DECISION"
    EFFECTIVE_RESOLVED_DECISION = "EFFECTIVE_RESOLVED_DECISION"
    UNRESOLVED_CONFLICT = "UNRESOLVED_CONFLICT"
    STALE_RESOLUTION = "STALE_RESOLUTION"
    RESOLUTION_CONFLICT = "RESOLUTION_CONFLICT"


class EffectiveEvidenceReviewSource(StrEnum):
    NONE = "NONE"
    CONSOLIDATED_REVIEWS = "CONSOLIDATED_REVIEWS"
    HUMAN_CONFLICT_RESOLUTION = "HUMAN_CONFLICT_RESOLUTION"


@dataclass(frozen=True, slots=True)
class EffectiveEvidenceReviewStatus:
    audit_id: str
    bundle_sha256: str
    state: EffectiveEvidenceReviewState
    effective_decision: EvidenceReviewDecision | None
    decision_source: EffectiveEvidenceReviewSource
    review_ids: tuple[str, ...]
    applicable_resolution_ids: tuple[str, ...]
    stale_resolution_ids: tuple[str, ...]
    conflict: bool
    send_authorized: bool = False
    review_is_campaign_authorization: bool = False

    def __post_init__(self) -> None:
        if not self.audit_id.strip():
            raise ValueError("audit_id must not be blank")
        if len(self.bundle_sha256) != 64:
            raise ValueError("bundle_sha256 must be a SHA-256 hex digest")
        if self.send_authorized or self.review_is_campaign_authorization:
            raise ValueError("effective evidence-review status cannot authorize send or campaign")
        if self.effective_decision is None and self.decision_source is not EffectiveEvidenceReviewSource.NONE:
            raise ValueError("decision_source must be NONE when no effective decision exists")
        if self.effective_decision is not None and self.decision_source is EffectiveEvidenceReviewSource.NONE:
            raise ValueError("effective decision requires an explicit source")


def build_effective_evidence_review_status(
    *,
    review_repository: EvidenceReviewRepository,
    resolution_repository: EvidenceReviewResolutionRepository,
    bundle: Mapping[str, Any],
) -> EffectiveEvidenceReviewStatus:
    """Combine immutable reviews and explicit resolutions into one observational status."""
    consolidated = consolidate_evidence_reviews(repository=review_repository, bundle=bundle)
    review_ids = tuple(sorted(review.review_id for review in consolidated.reviews))

    if consolidated.state is ConsolidatedEvidenceReviewState.NO_REVIEW:
        return EffectiveEvidenceReviewStatus(
            audit_id=consolidated.audit_id,
            bundle_sha256=consolidated.bundle_sha256,
            state=EffectiveEvidenceReviewState.NO_REVIEW,
            effective_decision=None,
            decision_source=EffectiveEvidenceReviewSource.NONE,
            review_ids=review_ids,
            applicable_resolution_ids=(),
            stale_resolution_ids=(),
            conflict=False,
        )

    if consolidated.state is not ConsolidatedEvidenceReviewState.CONFLICT:
        return EffectiveEvidenceReviewStatus(
            audit_id=consolidated.audit_id,
            bundle_sha256=consolidated.bundle_sha256,
            state=EffectiveEvidenceReviewState.EFFECTIVE_REVIEW_DECISION,
            effective_decision=EvidenceReviewDecision(consolidated.state.value),
            decision_source=EffectiveEvidenceReviewSource.CONSOLIDATED_REVIEWS,
            review_ids=review_ids,
            applicable_resolution_ids=(),
            stale_resolution_ids=(),
            conflict=False,
        )

    resolution = build_evidence_review_resolution_status(
        review_repository=review_repository,
        resolution_repository=resolution_repository,
        bundle=bundle,
    )
    if resolution.state is EvidenceReviewResolutionState.RESOLVED:
        return EffectiveEvidenceReviewStatus(
            audit_id=consolidated.audit_id,
            bundle_sha256=consolidated.bundle_sha256,
            state=EffectiveEvidenceReviewState.EFFECTIVE_RESOLVED_DECISION,
            effective_decision=resolution.effective_decision,
            decision_source=EffectiveEvidenceReviewSource.HUMAN_CONFLICT_RESOLUTION,
            review_ids=review_ids,
            applicable_resolution_ids=resolution.applicable_resolution_ids,
            stale_resolution_ids=resolution.stale_resolution_ids,
            conflict=False,
        )
    if resolution.state is EvidenceReviewResolutionState.STALE_RESOLUTION:
        state = EffectiveEvidenceReviewState.STALE_RESOLUTION
    elif resolution.state is EvidenceReviewResolutionState.RESOLUTION_CONFLICT:
        state = EffectiveEvidenceReviewState.RESOLUTION_CONFLICT
    else:
        state = EffectiveEvidenceReviewState.UNRESOLVED_CONFLICT
    return EffectiveEvidenceReviewStatus(
        audit_id=consolidated.audit_id,
        bundle_sha256=consolidated.bundle_sha256,
        state=state,
        effective_decision=None,
        decision_source=EffectiveEvidenceReviewSource.NONE,
        review_ids=review_ids,
        applicable_resolution_ids=resolution.applicable_resolution_ids,
        stale_resolution_ids=resolution.stale_resolution_ids,
        conflict=True,
    )


def effective_evidence_review_status_to_mapping(status: EffectiveEvidenceReviewStatus) -> dict[str, Any]:
    return {
        "audit_id": status.audit_id,
        "bundle_sha256": status.bundle_sha256,
        "state": status.state.value,
        "effective_decision": status.effective_decision.value if status.effective_decision else None,
        "decision_source": status.decision_source.value,
        "review_ids": list(status.review_ids),
        "applicable_resolution_ids": list(status.applicable_resolution_ids),
        "stale_resolution_ids": list(status.stale_resolution_ids),
        "conflict": status.conflict,
        "send_authorized": False,
        "review_is_campaign_authorization": False,
        "changes_auth_campaign_001": False,
        "changes_preflight": False,
        "changes_pilot_release": False,
        "changes_legal_signoff": False,
        "changes_professional_verification": False,
        "changes_source_freshness": False,
        "status_is_observational_only": True,
    }


__all__ = [
    "EffectiveEvidenceReviewSource",
    "EffectiveEvidenceReviewState",
    "EffectiveEvidenceReviewStatus",
    "build_effective_evidence_review_status",
    "effective_evidence_review_status_to_mapping",
]
