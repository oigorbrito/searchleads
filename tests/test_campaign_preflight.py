from datetime import datetime, timedelta, timezone

import pytest

from searchleads.campaign_preflight import (
    CampaignAuthorizationRecord,
    CampaignPreflightInputs,
    CampaignPreflightState,
    ComplianceSignoffRecord,
    ProfessionalVerificationRecord,
    ReviewDecision,
    VerificationDecision,
    evaluate_campaign_preflight,
)

NOW = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)


def signoff(**overrides):
    values = dict(
        signoff_id="legal:1",
        reviewer_reference="reviewer:legal",
        policy_id="policy:commercial-pilot:v1",
        policy_version="v1",
        jurisdiction="BR",
        channel="email",
        campaign_id="campaign:pilot-1",
        decision=ReviewDecision.APPROVED,
        decided_at=NOW - timedelta(hours=1),
        expires_at=NOW + timedelta(days=7),
        authority_evidence_refs=("AUTH-LGPD-001", "AUTH-ANPD-001"),
    )
    values.update(overrides)
    return ComplianceSignoffRecord(**values)


def authorization(**overrides):
    values = dict(
        authorization_id="auth:1",
        campaign_id="campaign:pilot-1",
        policy_id="policy:commercial-pilot:v1",
        policy_version="v1",
        authorizer_reference="owner:campaign",
        authorized_at=NOW - timedelta(minutes=30),
        valid_until=NOW + timedelta(days=1),
    )
    values.update(overrides)
    return CampaignAuthorizationRecord(**values)


def verification(**overrides):
    values = dict(
        verification_id="verification:1",
        person_id="person:1",
        council="CRO-SP",
        registration_number="12345",
        decision=VerificationDecision.VERIFIED_ACTIVE,
        verified_at=NOW - timedelta(hours=2),
        evidence_refs=("evidence:cfo:1",),
        reviewer_reference="reviewer:human",
        expires_at=NOW + timedelta(days=1),
    )
    values.update(overrides)
    return ProfessionalVerificationRecord(**values)


def inputs(**overrides):
    values = dict(
        campaign_id="campaign:pilot-1",
        policy_id="policy:commercial-pilot:v1",
        policy_version="v1",
        jurisdiction="BR",
        channel="email",
        brasilapi_fresh=True,
        compliance_signoff=signoff(),
        campaign_authorization=authorization(),
    )
    values.update(overrides)
    return CampaignPreflightInputs(**values)


def test_preflight_ready_without_professional_requirement():
    result = evaluate_campaign_preflight(inputs=inputs(), now=NOW)
    assert result.state is CampaignPreflightState.READY_FOR_AUTHORIZED_EXECUTION
    assert result.ready is True
    assert result.blockers == ()


def test_preflight_requires_professional_verification_only_when_policy_requires_it():
    blocked = evaluate_campaign_preflight(
        inputs=inputs(professional_verification_required=True, person_id="person:1"),
        now=NOW,
    )
    assert blocked.blockers == ("EXT-CFO-001",)

    ready = evaluate_campaign_preflight(
        inputs=inputs(
            professional_verification_required=True,
            person_id="person:1",
            professional_verification=verification(),
        ),
        now=NOW,
    )
    assert ready.ready is True


@pytest.mark.parametrize(
    ("field", "value", "blocker"),
    [
        ("brasilapi_fresh", False, "EXT-BRASILAPI-001"),
        ("compliance_signoff", None, "LEGAL-001"),
        ("campaign_authorization", None, "AUTH-CAMPAIGN-001"),
    ],
)
def test_preflight_fail_closed_for_missing_authority(field, value, blocker):
    result = evaluate_campaign_preflight(inputs=inputs(**{field: value}), now=NOW)
    assert result.state is CampaignPreflightState.BLOCKED
    assert blocker in result.blockers


def test_legal_signoff_rejects_wrong_scope_expiry_revocation_and_nonapproval():
    for record in (
        signoff(campaign_id="campaign:other"),
        signoff(expires_at=NOW),
        signoff(revoked_at=NOW - timedelta(seconds=1)),
        signoff(decision=ReviewDecision.REJECTED),
        signoff(decision=ReviewDecision.MORE_REVIEW_REQUIRED),
    ):
        result = evaluate_campaign_preflight(inputs=inputs(compliance_signoff=record), now=NOW)
        assert "LEGAL-001" in result.blockers


def test_conditional_approval_requires_conditions_and_is_valid_when_scoped():
    with pytest.raises(ValueError):
        signoff(decision=ReviewDecision.APPROVED_WITH_CONDITIONS, conditions=())
    record = signoff(
        decision=ReviewDecision.APPROVED_WITH_CONDITIONS,
        conditions=("suppression check before batch",),
    )
    assert evaluate_campaign_preflight(inputs=inputs(compliance_signoff=record), now=NOW).ready


def test_campaign_authorization_is_campaign_and_policy_specific_and_revocable():
    for record in (
        authorization(campaign_id="campaign:other"),
        authorization(policy_version="v2"),
        authorization(valid_until=NOW),
        authorization(revoked_at=NOW - timedelta(seconds=1)),
    ):
        result = evaluate_campaign_preflight(inputs=inputs(campaign_authorization=record), now=NOW)
        assert "AUTH-CAMPAIGN-001" in result.blockers


def test_professional_verification_is_person_specific_current_and_evidence_backed():
    for record in (
        verification(person_id="person:other"),
        verification(decision=VerificationDecision.VERIFIED_INACTIVE),
        verification(decision=VerificationDecision.NOT_FOUND),
        verification(decision=VerificationDecision.CONFLICT),
        verification(expires_at=NOW),
    ):
        result = evaluate_campaign_preflight(
            inputs=inputs(
                professional_verification_required=True,
                person_id="person:1",
                professional_verification=record,
            ),
            now=NOW,
        )
        assert "EXT-CFO-001" in result.blockers

    with pytest.raises(ValueError):
        verification(evidence_refs=())


def test_preflight_can_report_all_remaining_minimum_blockers_together():
    result = evaluate_campaign_preflight(
        inputs=inputs(
            brasilapi_fresh=False,
            compliance_signoff=None,
            campaign_authorization=None,
            professional_verification_required=True,
            person_id="person:1",
            professional_verification=None,
        ),
        now=NOW,
    )
    assert result.blockers == (
        "EXT-BRASILAPI-001",
        "LEGAL-001",
        "EXT-CFO-001",
        "AUTH-CAMPAIGN-001",
    )
