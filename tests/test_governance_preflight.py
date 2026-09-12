from __future__ import annotations

from datetime import datetime, timedelta, timezone

from searchleads.campaign_preflight import (
    CampaignAuthorizationRecord,
    CampaignPreflightState,
    ComplianceSignoffRecord,
    ProfessionalVerificationRecord,
    ReviewDecision,
    VerificationDecision,
    evaluate_campaign_preflight,
)
from searchleads.governance_persistence import GovernanceDecisionRepository
from searchleads.governance_preflight import (
    CampaignPreflightScope,
    build_campaign_preflight_inputs,
)

UTC = timezone.utc
NOW = datetime(2026, 9, 12, 1, 0, tzinfo=UTC)


def scope(**overrides):
    values = {
        "campaign_id": "campaign:1",
        "policy_id": "policy:1",
        "policy_version": "v1",
        "jurisdiction": "BR-RS",
        "channel": "EMAIL",
        "brasilapi_fresh": True,
        "professional_verification_required": True,
        "person_id": "person:1",
        "council": "CRO-RS",
    }
    values.update(overrides)
    return CampaignPreflightScope(**values)


def approved_signoff(*, signoff_id="legal:1", decision=ReviewDecision.APPROVED, decided_at=NOW):
    return ComplianceSignoffRecord(
        signoff_id=signoff_id,
        reviewer_reference="reviewer:legal",
        policy_id="policy:1",
        policy_version="v1",
        jurisdiction="BR-RS",
        channel="EMAIL",
        campaign_id="campaign:1",
        decision=decision,
        decided_at=decided_at,
        expires_at=NOW + timedelta(days=7),
        authority_evidence_refs=("evidence:legal:1",),
    )


def active_verification(*, verification_id="professional:1", decision=VerificationDecision.VERIFIED_ACTIVE, verified_at=NOW):
    return ProfessionalVerificationRecord(
        verification_id=verification_id,
        person_id="person:1",
        council="CRO-RS",
        registration_number="12345",
        decision=decision,
        verified_at=verified_at,
        evidence_refs=("evidence:cro:1",),
        reviewer_reference="reviewer:professional",
        expires_at=NOW + timedelta(days=7),
    )


def authorization(*, authorization_id="authorization:1", authorized_at=NOW):
    return CampaignAuthorizationRecord(
        authorization_id=authorization_id,
        campaign_id="campaign:1",
        policy_id="policy:1",
        policy_version="v1",
        authorizer_reference="owner:campaign",
        authorized_at=authorized_at,
        valid_until=NOW + timedelta(days=1),
    )


def test_assembly_recovers_exact_scope_records_and_preflight_can_be_ready():
    with GovernanceDecisionRepository() as repository:
        repository.save_compliance_signoff(approved_signoff())
        repository.save_professional_verification(active_verification())
        repository.save_campaign_authorization(authorization())

        inputs = build_campaign_preflight_inputs(repository=repository, scope=scope())
        result = evaluate_campaign_preflight(inputs=inputs, now=NOW)

    assert inputs.compliance_signoff is not None
    assert inputs.professional_verification is not None
    assert inputs.campaign_authorization is not None
    assert result.state is CampaignPreflightState.READY_FOR_AUTHORIZED_EXECUTION
    assert result.blockers == ()


def test_missing_persisted_decisions_remain_fail_closed():
    with GovernanceDecisionRepository() as repository:
        inputs = build_campaign_preflight_inputs(repository=repository, scope=scope())
        result = evaluate_campaign_preflight(inputs=inputs, now=NOW)

    assert result.state is CampaignPreflightState.BLOCKED
    assert result.blockers == ("LEGAL-001", "EXT-CFO-001", "AUTH-CAMPAIGN-001")


def test_scope_mismatch_does_not_leak_other_campaign_decisions():
    with GovernanceDecisionRepository() as repository:
        repository.save_compliance_signoff(approved_signoff())
        repository.save_professional_verification(active_verification())
        repository.save_campaign_authorization(authorization())

        inputs = build_campaign_preflight_inputs(
            repository=repository,
            scope=scope(campaign_id="campaign:2"),
        )
        result = evaluate_campaign_preflight(inputs=inputs, now=NOW)

    assert inputs.compliance_signoff is None
    assert inputs.professional_verification is not None
    assert inputs.campaign_authorization is None
    assert result.state is CampaignPreflightState.BLOCKED
    assert result.blockers == ("LEGAL-001", "AUTH-CAMPAIGN-001")


def test_latest_negative_decision_is_not_bypassed_by_older_approval():
    with GovernanceDecisionRepository() as repository:
        repository.save_compliance_signoff(
            approved_signoff(signoff_id="legal:approved", decided_at=NOW - timedelta(hours=2))
        )
        repository.save_compliance_signoff(
            approved_signoff(
                signoff_id="legal:rejected",
                decision=ReviewDecision.REJECTED,
                decided_at=NOW - timedelta(hours=1),
            )
        )
        repository.save_professional_verification(active_verification())
        repository.save_campaign_authorization(authorization())

        inputs = build_campaign_preflight_inputs(repository=repository, scope=scope())
        result = evaluate_campaign_preflight(inputs=inputs, now=NOW)

    assert inputs.compliance_signoff is not None
    assert inputs.compliance_signoff.decision is ReviewDecision.REJECTED
    assert result.state is CampaignPreflightState.BLOCKED
    assert result.blockers == ("LEGAL-001",)


def test_professional_lookup_is_skipped_when_policy_does_not_require_it():
    with GovernanceDecisionRepository() as repository:
        repository.save_compliance_signoff(approved_signoff())
        repository.save_campaign_authorization(authorization())

        inputs = build_campaign_preflight_inputs(
            repository=repository,
            scope=scope(
                professional_verification_required=False,
                person_id=None,
                council=None,
            ),
        )
        result = evaluate_campaign_preflight(inputs=inputs, now=NOW)

    assert inputs.professional_verification is None
    assert result.state is CampaignPreflightState.READY_FOR_AUTHORIZED_EXECUTION


def test_required_professional_verification_requires_person_id_at_assembly_boundary():
    try:
        CampaignPreflightScope(
            campaign_id="campaign:1",
            policy_id="policy:1",
            policy_version="v1",
            jurisdiction="BR-RS",
            channel="EMAIL",
            brasilapi_fresh=True,
            professional_verification_required=True,
            person_id=None,
        )
    except ValueError as exc:
        assert "person_id is required" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected fail-closed scope validation")
