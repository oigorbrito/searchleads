from datetime import datetime, timedelta, timezone

from searchleads.campaign_preflight import (
    CampaignAuthorizationRecord,
    CampaignPreflightInputs,
    CampaignPreflightState,
    ComplianceSignoffRecord,
    ReviewDecision,
    evaluate_campaign_preflight,
)

# Development-only fixture. These values exercise the sequential preflight path
# and MUST NOT be treated as commercial authority or production evidence.
NOW = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
TEST_CAMPAIGN_ID = "campaign:test-pilot-v0"
TEST_POLICY_ID = "policy:test-pilot"
TEST_POLICY_VERSION = "0.0.0"
TEST_JURISDICTION = "BR"
TEST_CHANNEL = "email"
TEST_OWNER_REFERENCE = "test-owner:developer"
TEST_EVIDENCE_REF = "TEST-ONLY-NO-COMMERCIAL-AUTHORITY"


def test_pilot_v0_fixture_exercises_authorized_preflight_path():
    compliance_signoff = ComplianceSignoffRecord(
        signoff_id="legal:test-pilot-v0",
        reviewer_reference=TEST_OWNER_REFERENCE,
        policy_id=TEST_POLICY_ID,
        policy_version=TEST_POLICY_VERSION,
        jurisdiction=TEST_JURISDICTION,
        channel=TEST_CHANNEL,
        campaign_id=TEST_CAMPAIGN_ID,
        decision=ReviewDecision.APPROVED,
        decided_at=NOW - timedelta(minutes=10),
        expires_at=NOW + timedelta(hours=1),
        authority_evidence_refs=(TEST_EVIDENCE_REF,),
    )
    campaign_authorization = CampaignAuthorizationRecord(
        authorization_id="auth:test-pilot-v0",
        campaign_id=TEST_CAMPAIGN_ID,
        policy_id=TEST_POLICY_ID,
        policy_version=TEST_POLICY_VERSION,
        authorizer_reference=TEST_OWNER_REFERENCE,
        authorized_at=NOW - timedelta(minutes=5),
        valid_until=NOW + timedelta(hours=1),
    )

    result = evaluate_campaign_preflight(
        inputs=CampaignPreflightInputs(
            campaign_id=TEST_CAMPAIGN_ID,
            policy_id=TEST_POLICY_ID,
            policy_version=TEST_POLICY_VERSION,
            jurisdiction=TEST_JURISDICTION,
            channel=TEST_CHANNEL,
            brasilapi_fresh=True,
            professional_verification_required=False,
            compliance_signoff=compliance_signoff,
            campaign_authorization=campaign_authorization,
        ),
        now=NOW,
    )

    assert result.state is CampaignPreflightState.READY_FOR_AUTHORIZED_EXECUTION
    assert result.blockers == ()


def test_pilot_v0_fixture_remains_fail_closed_when_test_authority_is_missing():
    result = evaluate_campaign_preflight(
        inputs=CampaignPreflightInputs(
            campaign_id=TEST_CAMPAIGN_ID,
            policy_id=TEST_POLICY_ID,
            policy_version=TEST_POLICY_VERSION,
            jurisdiction=TEST_JURISDICTION,
            channel=TEST_CHANNEL,
            brasilapi_fresh=True,
            professional_verification_required=False,
            compliance_signoff=None,
            campaign_authorization=None,
        ),
        now=NOW,
    )

    assert result.state is CampaignPreflightState.BLOCKED
    assert result.blockers == ("LEGAL-001", "AUTH-CAMPAIGN-001")
