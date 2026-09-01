from datetime import datetime, timezone
import pytest

from searchleads.operational import (
    ComplianceSignoffRecord,
    ContactClass,
    LegalSignoffDecision,
    ManualAuthorizationRecord,
    SendReadyState,
    build_campaign_compliance_policy,
)
from searchleads.pilot_dry_run import create_synthetic_pilot_dataset, run_pilot_dry_run


def test_pilot_dry_run_execution_with_synthetic_fixtures() -> None:
    now = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
    policy = build_campaign_compliance_policy()
    signoff = ComplianceSignoffRecord(
        signoff_id="signoff-dryrun",
        review_authority="legal.counsel@example.test",
        policy_version=policy.version,
        jurisdiction=policy.jurisdiction,
        channel=policy.channel,
        decision=LegalSignoffDecision.APPROVED,
        approved_contact_classes=(ContactClass.COMPANY_GENERIC, ContactClass.BUSINESS_PERSONALIZED),
        conditions=(),
        reviewed_at=now,
        reference="REF-DRYRUN",
    )
    authorization = ManualAuthorizationRecord(
        authorization_id="auth-dryrun",
        campaign_id="campaign:pilot-v1",
        policy_id=policy.policy_id,
        version=policy.version,
        authorized_by="owner@example.test",
        timestamp=now,
        scope="campaign:pilot-v1",
        expires_at=None,
        reason="Synthetic dry-run authorization",
    )

    dataset = create_synthetic_pilot_dataset(now)
    metrics, audit_records = run_pilot_dry_run(dataset, policy, signoff, authorization, now)

    assert metrics.total_candidates == 5
    assert metrics.auto_match_company == 4
    assert metrics.company_review == 1
    assert metrics.qualified == 4
    assert metrics.suppressed == 1
    assert metrics.send_ready == 1
    assert metrics.blocked == 4

    assert len(audit_records) == 5
    # First candidate is clean SEND_READY
    assert audit_records[0].final_gate_state == SendReadyState.SEND_READY.value
    assert audit_records[0].proof_digest is not None
