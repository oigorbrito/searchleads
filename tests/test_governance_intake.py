from __future__ import annotations

from datetime import datetime, timezone

import pytest

from searchleads.campaign_preflight import CampaignPreflightState
from searchleads.governance_intake import (
    GovernanceDecisionKind,
    GovernanceStorageAction,
    governance_intake_receipt_to_mapping,
    process_governance_intake,
)
from searchleads.governance_persistence import GovernanceDecisionRepository
from searchleads.governance_preflight import CampaignPreflightScope


NOW = datetime(2026, 9, 12, 3, 0, tzinfo=timezone.utc)


def _scope(*, brasilapi_fresh: bool = True) -> CampaignPreflightScope:
    return CampaignPreflightScope(
        campaign_id="campaign-1",
        policy_id="policy-1",
        policy_version="v1",
        jurisdiction="BR-RS",
        channel="email",
        brasilapi_fresh=brasilapi_fresh,
        professional_verification_required=True,
        person_id="person-1",
        council="CRO-RS",
    )


def _compliance(*, campaign_id: str = "campaign-1") -> dict[str, object]:
    return {
        "signoff_id": "legal-1",
        "reviewer_reference": "legal-reviewer-1",
        "policy_id": "policy-1",
        "policy_version": "v1",
        "jurisdiction": "BR-RS",
        "channel": "email",
        "campaign_id": campaign_id,
        "decision": "APPROVED",
        "decided_at": "2026-09-12T02:00:00+00:00",
        "expires_at": "2026-09-13T02:00:00+00:00",
        "conditions": [],
        "authority_evidence_refs": ["legal-evidence-1"],
        "revoked_at": None,
    }


def _professional(*, person_id: str = "person-1", decision: str = "VERIFIED_ACTIVE") -> dict[str, object]:
    return {
        "verification_id": "professional-1",
        "person_id": person_id,
        "council": "CRO-RS",
        "registration_number": "12345",
        "decision": decision,
        "verified_at": "2026-09-12T02:10:00+00:00",
        "evidence_refs": ["professional-evidence-1"],
        "reviewer_reference": "professional-reviewer-1",
        "expires_at": "2026-09-13T02:10:00+00:00",
    }


def _authorization(*, campaign_id: str = "campaign-1") -> dict[str, object]:
    return {
        "authorization_id": "authorization-1",
        "campaign_id": campaign_id,
        "policy_id": "policy-1",
        "policy_version": "v1",
        "authorizer_reference": "campaign-owner-1",
        "authorized_at": "2026-09-12T02:20:00+00:00",
        "valid_until": "2026-09-13T02:20:00+00:00",
        "revoked_at": None,
    }


def test_intake_closes_governance_chain_without_authorizing_send() -> None:
    with GovernanceDecisionRepository() as repository:
        first = process_governance_intake(
            repository=repository,
            kind=GovernanceDecisionKind.COMPLIANCE_SIGNOFF,
            payload=_compliance(),
            scope=_scope(),
            now=NOW,
        )
        assert first.preflight.state is CampaignPreflightState.BLOCKED
        assert first.preflight.blockers == ("EXT-CFO-001", "AUTH-CAMPAIGN-001")

        second = process_governance_intake(
            repository=repository,
            kind=GovernanceDecisionKind.PROFESSIONAL_VERIFICATION,
            payload=_professional(),
            scope=_scope(),
            now=NOW,
        )
        assert second.preflight.blockers == ("AUTH-CAMPAIGN-001",)

        third = process_governance_intake(
            repository=repository,
            kind=GovernanceDecisionKind.CAMPAIGN_AUTHORIZATION,
            payload=_authorization(),
            scope=_scope(),
            now=NOW,
        )
        assert third.preflight.state is CampaignPreflightState.READY_FOR_AUTHORIZED_EXECUTION
        assert third.preflight.blockers == ()
        receipt = governance_intake_receipt_to_mapping(third)
        assert receipt["send_authorized"] is False
        assert receipt["preflight_state"] == "READY_FOR_AUTHORIZED_EXECUTION"
        assert len(receipt["payload_sha256"]) == 64


def test_replay_is_idempotent_and_receipt_reports_existing_record() -> None:
    with GovernanceDecisionRepository() as repository:
        first = process_governance_intake(
            repository=repository,
            kind="compliance-signoff",
            payload=_compliance(),
            scope=_scope(),
            now=NOW,
        )
        second = process_governance_intake(
            repository=repository,
            kind="compliance-signoff",
            payload=_compliance(),
            scope=_scope(),
            now=NOW,
        )
        assert first.storage_action is GovernanceStorageAction.INSERTED
        assert second.storage_action is GovernanceStorageAction.ALREADY_PRESENT
        assert first.payload_sha256 == second.payload_sha256


def test_scope_mismatch_is_rejected_before_persistence() -> None:
    with GovernanceDecisionRepository() as repository:
        with pytest.raises(ValueError, match="campaign_id does not match preflight scope"):
            process_governance_intake(
                repository=repository,
                kind="compliance-signoff",
                payload=_compliance(campaign_id="other-campaign"),
                scope=_scope(),
                now=NOW,
            )
        assert repository.load_compliance_signoff("legal-1") is None


def test_professional_person_mismatch_is_rejected_before_persistence() -> None:
    with GovernanceDecisionRepository() as repository:
        with pytest.raises(ValueError, match="person_id does not match preflight scope"):
            process_governance_intake(
                repository=repository,
                kind="professional-verification",
                payload=_professional(person_id="person-2"),
                scope=_scope(),
                now=NOW,
            )
        assert repository.load_professional_verification("professional-1") is None


def test_negative_professional_decision_is_persisted_and_remains_blocking() -> None:
    with GovernanceDecisionRepository() as repository:
        process_governance_intake(
            repository=repository,
            kind="compliance-signoff",
            payload=_compliance(),
            scope=_scope(),
            now=NOW,
        )
        receipt = process_governance_intake(
            repository=repository,
            kind="professional-verification",
            payload=_professional(decision="CONFLICT"),
            scope=_scope(),
            now=NOW,
        )
        assert receipt.storage_action is GovernanceStorageAction.INSERTED
        assert "EXT-CFO-001" in receipt.preflight.blockers


def test_stale_source_gate_cannot_be_closed_by_human_governance_intake() -> None:
    with GovernanceDecisionRepository() as repository:
        process_governance_intake(
            repository=repository,
            kind="compliance-signoff",
            payload=_compliance(),
            scope=_scope(brasilapi_fresh=False),
            now=NOW,
        )
        process_governance_intake(
            repository=repository,
            kind="professional-verification",
            payload=_professional(),
            scope=_scope(brasilapi_fresh=False),
            now=NOW,
        )
        receipt = process_governance_intake(
            repository=repository,
            kind="campaign-authorization",
            payload=_authorization(),
            scope=_scope(brasilapi_fresh=False),
            now=NOW,
        )
        assert receipt.preflight.state is CampaignPreflightState.BLOCKED
        assert receipt.preflight.blockers == ("EXT-BRASILAPI-001",)


def test_naive_evaluation_time_is_rejected_without_persistence() -> None:
    with GovernanceDecisionRepository() as repository:
        with pytest.raises(ValueError, match="now must be timezone-aware"):
            process_governance_intake(
                repository=repository,
                kind="campaign-authorization",
                payload=_authorization(),
                scope=_scope(),
                now=datetime(2026, 9, 12, 3, 0),
            )
        assert repository.load_campaign_authorization("authorization-1") is None
