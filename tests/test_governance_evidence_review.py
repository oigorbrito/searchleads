from __future__ import annotations

from datetime import datetime, timezone

import pytest

from searchleads.governance_audit import GovernanceAuditRepository
from searchleads.governance_evidence_bundle import (
    build_governance_evidence_bundle,
    governance_evidence_bundle_to_mapping,
)
from searchleads.governance_evidence_review import (
    EvidenceReviewConflictError,
    EvidenceReviewDecision,
    EvidenceReviewIntegrityError,
    EvidenceReviewRepository,
    evidence_review_to_mapping,
    process_evidence_review,
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


def _review(bundle, **overrides):
    payload = {
        "review_id": "review-1",
        "audit_id": bundle["audit_id"],
        "bundle_sha256": bundle["bundle_sha256"],
        "reviewer_reference": "reviewer:alice",
        "decision": "APPROVED",
        "reviewed_at": NOW.isoformat(),
        "evidence_refs": ["ticket:REV-1"],
        "note": "reviewed exact exported artifact",
        "send_authorized": False,
        "review_is_campaign_authorization": False,
    }
    payload.update(overrides)
    return payload


def test_review_is_bound_to_exact_verified_bundle(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as repository:
        record, inserted = process_evidence_review(
            repository=repository,
            bundle=bundle,
            review_payload=_review(bundle),
        )
        assert inserted is True
        assert record.decision is EvidenceReviewDecision.APPROVED
        assert record.audit_id == bundle["audit_id"]
        assert record.bundle_sha256 == bundle["bundle_sha256"]
        assert record.send_authorized is False
        assert repository.load("review-1") == record
        assert repository.list_for_bundle(
            audit_id=bundle["audit_id"], bundle_sha256=bundle["bundle_sha256"]
        ) == (record,)


def test_exact_replay_is_idempotent_but_changed_review_conflicts(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as repository:
        first, inserted = process_evidence_review(repository=repository, bundle=bundle, review_payload=_review(bundle))
        replay, inserted_replay = process_evidence_review(repository=repository, bundle=bundle, review_payload=_review(bundle))
        assert inserted is True
        assert inserted_replay is False
        assert replay == first
        with pytest.raises(EvidenceReviewConflictError):
            process_evidence_review(
                repository=repository,
                bundle=bundle,
                review_payload=_review(bundle, decision="REJECTED"),
            )


def test_mismatched_bundle_digest_is_rejected_before_persistence(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as repository:
        with pytest.raises(ValueError, match="bundle_sha256 does not match"):
            process_evidence_review(
                repository=repository,
                bundle=bundle,
                review_payload=_review(bundle, bundle_sha256="0" * 64),
            )
        with pytest.raises(KeyError):
            repository.load("review-1")


def test_mismatched_audit_id_is_rejected_before_persistence(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as repository:
        with pytest.raises(ValueError, match="audit_id does not match"):
            process_evidence_review(
                repository=repository,
                bundle=bundle,
                review_payload=_review(bundle, audit_id="audit-other"),
            )


def test_tampered_bundle_is_rejected_even_when_review_fields_match(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    bundle["snapshot"]["campaign_id"] = "tampered"
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as repository:
        with pytest.raises(RuntimeError, match="bundle digest mismatch"):
            process_evidence_review(repository=repository, bundle=bundle, review_payload=_review(bundle))


def test_review_cannot_authorize_send_or_campaign(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    with EvidenceReviewRepository(tmp_path / "reviews.sqlite") as repository:
        with pytest.raises(ValueError, match="must not authorize send"):
            process_evidence_review(
                repository=repository,
                bundle=bundle,
                review_payload=_review(bundle, send_authorized=True),
            )
        with pytest.raises(ValueError, match="must not be campaign authorization"):
            process_evidence_review(
                repository=repository,
                bundle=bundle,
                review_payload=_review(bundle, review_is_campaign_authorization=True),
            )


def test_persisted_review_tampering_is_detected(tmp_path) -> None:
    bundle = _bundle(tmp_path)
    review_db = tmp_path / "reviews.sqlite"
    with EvidenceReviewRepository(review_db) as repository:
        record, _ = process_evidence_review(repository=repository, bundle=bundle, review_payload=_review(bundle))
        payload = evidence_review_to_mapping(record)
        payload["decision"] = "REJECTED"
        repository._connection.execute(
            "UPDATE governance_evidence_reviews SET payload_json = ? WHERE review_id = ?",
            (str(payload), "review-1"),
        )
        repository._connection.commit()
        with pytest.raises(EvidenceReviewIntegrityError, match="digest mismatch"):
            repository.load("review-1")
