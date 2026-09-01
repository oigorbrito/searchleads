from datetime import datetime, timezone
import pytest

from searchleads.operational import (
    ComplianceSignoffRecord,
    ContactClass,
    LegalSignoffDecision,
    ManualAuthorizationRecord,
    SendReadyInputs,
    SendReadyState,
    build_campaign_compliance_policy,
    evaluate_send_ready_proof,
)


def test_two_key_authority_both_valid_passes() -> None:
    now = datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc)
    policy = build_campaign_compliance_policy()
    signoff = ComplianceSignoffRecord(
        signoff_id="signoff-1",
        review_authority="legal.counsel@example.test",
        policy_version=policy.version,
        jurisdiction=policy.jurisdiction,
        channel=policy.channel,
        decision=LegalSignoffDecision.APPROVED,
        approved_contact_classes=(ContactClass.COMPANY_GENERIC, ContactClass.BUSINESS_PERSONALIZED),
        conditions=(),
        reviewed_at=now,
        reference="REF-1",
    )
    authorization = ManualAuthorizationRecord(
        authorization_id="auth-1",
        campaign_id="campaign:1",
        policy_id=policy.policy_id,
        version=policy.version,
        authorized_by="owner@example.test",
        timestamp=now,
        scope="campaign:1",
        expires_at=None,
        reason="Approved for dry-run pilot testing",
    )
    inputs = SendReadyInputs(
        discovered=True,
        validated=True,
        qualified=True,
        compliance_cleared=True,
        live_certified=True,
    )
    proof = evaluate_send_ready_proof(
        evaluation_id="eval-1",
        qualification_decision_id="qual-1",
        contact_validation_id="val-1",
        contact_use_decision=None,
        suppression_rule=None,
        certification_refs=("cert-1",),
        policy=policy,
        authorization=authorization,
        inputs=inputs,
        timestamp=now,
        compliance_signoff=signoff,
    )
    assert proof.result.ready is True
    assert proof.result.state is SendReadyState.SEND_READY


def test_two_key_authority_missing_legal_signoff_blocks() -> None:
    now = datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc)
    policy = build_campaign_compliance_policy()
    authorization = ManualAuthorizationRecord(
        authorization_id="auth-1",
        campaign_id="campaign:1",
        policy_id=policy.policy_id,
        version=policy.version,
        authorized_by="owner@example.test",
        timestamp=now,
        scope="campaign:1",
        expires_at=None,
        reason="Approved for dry-run pilot testing",
    )
    inputs = SendReadyInputs(
        discovered=True,
        validated=True,
        qualified=True,
        compliance_cleared=True,
        live_certified=True,
    )
    proof = evaluate_send_ready_proof(
        evaluation_id="eval-2",
        qualification_decision_id="qual-1",
        contact_validation_id="val-1",
        contact_use_decision=None,
        suppression_rule=None,
        certification_refs=("cert-1",),
        policy=policy,
        authorization=authorization,
        inputs=inputs,
        timestamp=now,
        compliance_signoff=None,
    )
    assert proof.result.ready is False
    assert proof.result.state is SendReadyState.COMPLIANCE_BLOCKED
    assert "valid legal signoff required" in proof.result.blockers


def test_two_key_authority_missing_authorization_blocks() -> None:
    now = datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc)
    policy = build_campaign_compliance_policy()
    signoff = ComplianceSignoffRecord(
        signoff_id="signoff-1",
        review_authority="legal.counsel@example.test",
        policy_version=policy.version,
        jurisdiction=policy.jurisdiction,
        channel=policy.channel,
        decision=LegalSignoffDecision.APPROVED,
        approved_contact_classes=(ContactClass.COMPANY_GENERIC, ContactClass.BUSINESS_PERSONALIZED),
        conditions=(),
        reviewed_at=now,
        reference="REF-1",
    )
    inputs = SendReadyInputs(
        discovered=True,
        validated=True,
        qualified=True,
        compliance_cleared=True,
        live_certified=True,
    )
    proof = evaluate_send_ready_proof(
        evaluation_id="eval-3",
        qualification_decision_id="qual-1",
        contact_validation_id="val-1",
        contact_use_decision=None,
        suppression_rule=None,
        certification_refs=("cert-1",),
        policy=policy,
        authorization=None,
        inputs=inputs,
        timestamp=now,
        compliance_signoff=signoff,
    )
    assert proof.result.ready is False
    assert proof.result.state is SendReadyState.COMPLIANCE_BLOCKED
    assert "valid campaign authorization required" in proof.result.blockers
