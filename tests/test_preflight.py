from datetime import datetime, timezone
import pytest

from searchleads.operational import (
    ComplianceSignoffRecord,
    ContactClass,
    LegalSignoffDecision,
    ManualAuthorizationRecord,
    build_campaign_compliance_policy,
)
from searchleads.preflight import run_preflight_check


def test_preflight_check_without_signoff_returns_blocked() -> None:
    report = run_preflight_check()
    assert report.ready is False
    assert report.status == "BLOCKED"
    assert any("LEGAL-001" in b for b in report.blockers)
    assert any("AUTH-001" in b for b in report.blockers)


def test_preflight_check_with_valid_signoff_and_auth_returns_ready() -> None:
    now = datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc)
    policy = build_campaign_compliance_policy()
    signoff = ComplianceSignoffRecord(
        signoff_id="signoff-pref",
        review_authority="legal@example.test",
        policy_version=policy.version,
        jurisdiction=policy.jurisdiction,
        channel=policy.channel,
        decision=LegalSignoffDecision.APPROVED,
        approved_contact_classes=(ContactClass.COMPANY_GENERIC,),
        conditions=(),
        reviewed_at=now,
        reference="REF-PREF",
    )
    authorization = ManualAuthorizationRecord(
        authorization_id="auth-pref",
        campaign_id="campaign:pilot-v1",
        policy_id=policy.policy_id,
        version=policy.version,
        authorized_by="owner@example.test",
        timestamp=now,
        scope="campaign:pilot-v1",
        expires_at=None,
        reason="Preflight test authorization",
    )

    report = run_preflight_check(policy, signoff, authorization)
    assert report.ready is True
    assert report.status == "PILOT_PREFLIGHT_READY"
    assert len(report.blockers) == 0
