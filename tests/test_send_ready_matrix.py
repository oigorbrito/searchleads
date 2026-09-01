from datetime import datetime, timezone
import pytest

from searchleads.operational import (
    CampaignCompliancePolicy,
    ComplianceSignoffRecord,
    ContactClass,
    ContactUseDecision,
    ContactUseState,
    LegalSignoffDecision,
    ManualAuthorizationRecord,
    SendReadyInputs,
    SendReadyState,
    SuppressionRule,
    build_campaign_compliance_policy,
    evaluate_send_ready_proof,
)


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc)


@pytest.fixture
def policy() -> CampaignCompliancePolicy:
    return build_campaign_compliance_policy()


@pytest.fixture
def valid_signoff(policy: CampaignCompliancePolicy, now: datetime) -> ComplianceSignoffRecord:
    return ComplianceSignoffRecord(
        signoff_id="signoff-valid",
        review_authority="legal.counsel@example.test",
        policy_version=policy.version,
        jurisdiction=policy.jurisdiction,
        channel=policy.channel,
        decision=LegalSignoffDecision.APPROVED,
        approved_contact_classes=(ContactClass.COMPANY_GENERIC, ContactClass.BUSINESS_PERSONALIZED),
        conditions=(),
        reviewed_at=now,
        reference="REF-001",
    )


@pytest.fixture
def valid_auth(policy: CampaignCompliancePolicy, now: datetime) -> ManualAuthorizationRecord:
    return ManualAuthorizationRecord(
        authorization_id="auth-valid",
        campaign_id="campaign:pilot-v1",
        policy_id=policy.policy_id,
        version=policy.version,
        authorized_by="owner@example.test",
        timestamp=now,
        scope="campaign:pilot-v1",
        expires_at=None,
        reason="Manual pilot dry-run authorization",
    )


@pytest.fixture
def valid_inputs() -> SendReadyInputs:
    return SendReadyInputs(
        discovered=True,
        validated=True,
        qualified=True,
        compliance_cleared=True,
        live_certified=True,
    )


def test_positive_send_ready_proof_generation_and_integrity_digest(
    policy: CampaignCompliancePolicy,
    valid_signoff: ComplianceSignoffRecord,
    valid_auth: ManualAuthorizationRecord,
    valid_inputs: SendReadyInputs,
    now: datetime,
) -> None:
    proof = evaluate_send_ready_proof(
        evaluation_id="eval-pos-1",
        qualification_decision_id="qual-1",
        contact_validation_id="val-1",
        contact_use_decision=None,
        suppression_rule=None,
        certification_refs=("cert-brasilapi-1",),
        policy=policy,
        authorization=valid_auth,
        inputs=valid_inputs,
        timestamp=now,
        compliance_signoff=valid_signoff,
    )
    assert proof.result.ready is True
    assert proof.result.state is SendReadyState.SEND_READY
    assert proof.integrity_digest is not None
    assert proof.integrity_digest.startswith("sha256:")
    assert proof.integrity_digest == proof.compute_integrity_digest()


def test_negative_matrix_legal_signoff_missing(
    policy: CampaignCompliancePolicy,
    valid_auth: ManualAuthorizationRecord,
    valid_inputs: SendReadyInputs,
    now: datetime,
) -> None:
    proof = evaluate_send_ready_proof(
        evaluation_id="eval-neg-1",
        qualification_decision_id="qual-1",
        contact_validation_id="val-1",
        contact_use_decision=None,
        suppression_rule=None,
        certification_refs=("cert-1",),
        policy=policy,
        authorization=valid_auth,
        inputs=valid_inputs,
        timestamp=now,
        compliance_signoff=None,
    )
    assert proof.result.ready is False
    assert proof.result.state is SendReadyState.COMPLIANCE_BLOCKED
    assert "valid legal signoff required" in proof.result.blockers


def test_negative_matrix_legal_signoff_expired(
    policy: CampaignCompliancePolicy,
    valid_auth: ManualAuthorizationRecord,
    valid_inputs: SendReadyInputs,
    now: datetime,
) -> None:
    expired_signoff = ComplianceSignoffRecord(
        signoff_id="signoff-exp",
        review_authority="legal.counsel@example.test",
        policy_version=policy.version,
        jurisdiction=policy.jurisdiction,
        channel=policy.channel,
        decision=LegalSignoffDecision.APPROVED,
        approved_contact_classes=(ContactClass.COMPANY_GENERIC,),
        conditions=(),
        reviewed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        reference="REF-EXP",
        expires_at=datetime(2025, 12, 31, tzinfo=timezone.utc),
    )
    proof = evaluate_send_ready_proof(
        evaluation_id="eval-neg-2",
        qualification_decision_id="qual-1",
        contact_validation_id="val-1",
        contact_use_decision=None,
        suppression_rule=None,
        certification_refs=("cert-1",),
        policy=policy,
        authorization=valid_auth,
        inputs=valid_inputs,
        timestamp=now,
        compliance_signoff=expired_signoff,
    )
    assert proof.result.ready is False
    assert proof.result.state is SendReadyState.COMPLIANCE_BLOCKED
    assert "valid legal signoff required" in proof.result.blockers


def test_negative_matrix_authorization_missing(
    policy: CampaignCompliancePolicy,
    valid_signoff: ComplianceSignoffRecord,
    valid_inputs: SendReadyInputs,
    now: datetime,
) -> None:
    proof = evaluate_send_ready_proof(
        evaluation_id="eval-neg-3",
        qualification_decision_id="qual-1",
        contact_validation_id="val-1",
        contact_use_decision=None,
        suppression_rule=None,
        certification_refs=("cert-1",),
        policy=policy,
        authorization=None,
        inputs=valid_inputs,
        timestamp=now,
        compliance_signoff=valid_signoff,
    )
    assert proof.result.ready is False
    assert proof.result.state is SendReadyState.COMPLIANCE_BLOCKED
    assert "valid campaign authorization required" in proof.result.blockers


def test_negative_matrix_authorization_revoked(
    policy: CampaignCompliancePolicy,
    valid_signoff: ComplianceSignoffRecord,
    valid_inputs: SendReadyInputs,
    now: datetime,
) -> None:
    revoked_auth = ManualAuthorizationRecord(
        authorization_id="auth-rev",
        campaign_id="campaign:pilot-v1",
        policy_id=policy.policy_id,
        version=policy.version,
        authorized_by="owner@example.test",
        timestamp=now,
        scope="campaign:pilot-v1",
        expires_at=None,
        reason="Revoked due to policy update",
        revoked_at=now,
    )
    proof = evaluate_send_ready_proof(
        evaluation_id="eval-neg-4",
        qualification_decision_id="qual-1",
        contact_validation_id="val-1",
        contact_use_decision=None,
        suppression_rule=None,
        certification_refs=("cert-1",),
        policy=policy,
        authorization=revoked_auth,
        inputs=valid_inputs,
        timestamp=now,
        compliance_signoff=valid_signoff,
    )
    assert proof.result.ready is False
    assert proof.result.state is SendReadyState.COMPLIANCE_BLOCKED
    assert "valid campaign authorization required" in proof.result.blockers


def test_negative_matrix_wrong_campaign_authorization_scope(
    policy: CampaignCompliancePolicy,
    valid_signoff: ComplianceSignoffRecord,
    valid_inputs: SendReadyInputs,
    now: datetime,
) -> None:
    wrong_scope_auth = ManualAuthorizationRecord(
        authorization_id="auth-wrong",
        campaign_id="campaign:other-v1",
        policy_id="policy:other:v2",
        version="v2",
        authorized_by="owner@example.test",
        timestamp=now,
        scope="campaign:other-v1",
        expires_at=None,
        reason="Wrong campaign scope",
    )
    proof = evaluate_send_ready_proof(
        evaluation_id="eval-neg-5",
        qualification_decision_id="qual-1",
        contact_validation_id="val-1",
        contact_use_decision=None,
        suppression_rule=None,
        certification_refs=("cert-1",),
        policy=policy,
        authorization=wrong_scope_auth,
        inputs=valid_inputs,
        timestamp=now,
        compliance_signoff=valid_signoff,
    )
    assert proof.result.ready is False
    assert proof.result.state is SendReadyState.COMPLIANCE_BLOCKED
    assert "campaign authorization scope mismatch" in proof.result.blockers


def test_negative_matrix_qualification_failed(
    policy: CampaignCompliancePolicy,
    valid_signoff: ComplianceSignoffRecord,
    valid_auth: ManualAuthorizationRecord,
    now: datetime,
) -> None:
    unqualified_inputs = SendReadyInputs(
        discovered=True,
        validated=True,
        qualified=False,
        compliance_cleared=True,
        live_certified=True,
    )
    proof = evaluate_send_ready_proof(
        evaluation_id="eval-neg-6",
        qualification_decision_id="qual-unqual",
        contact_validation_id="val-1",
        contact_use_decision=None,
        suppression_rule=None,
        certification_refs=("cert-1",),
        policy=policy,
        authorization=valid_auth,
        inputs=unqualified_inputs,
        timestamp=now,
        compliance_signoff=valid_signoff,
    )
    assert proof.result.ready is False
    assert proof.result.state is SendReadyState.QUALIFIED
    assert "qualified" in proof.result.missing_inputs


def test_negative_matrix_suppression_present(
    policy: CampaignCompliancePolicy,
    valid_signoff: ComplianceSignoffRecord,
    valid_auth: ManualAuthorizationRecord,
    now: datetime,
) -> None:
    suppressed_inputs = SendReadyInputs(
        discovered=True,
        validated=True,
        qualified=True,
        compliance_cleared=False,
        live_certified=True,
        compliance_blockers=("contact is suppressed",),
    )
    suppression = SuppressionRule(
        suppression_id="sup-1",
        scope="contact",
        subject_id="contact:001",
        reason="Opt-out requested",
        active=True,
    )
    proof = evaluate_send_ready_proof(
        evaluation_id="eval-neg-7",
        qualification_decision_id="qual-1",
        contact_validation_id="val-1",
        contact_use_decision=None,
        suppression_rule=suppression,
        certification_refs=("cert-1",),
        policy=policy,
        authorization=valid_auth,
        inputs=suppressed_inputs,
        timestamp=now,
        compliance_signoff=valid_signoff,
    )
    assert proof.result.ready is False
    assert proof.result.state is SendReadyState.COMPLIANCE_BLOCKED
    assert "contact is suppressed" in proof.result.blockers
    assert proof.suppression_decision_id == "sup-1"
