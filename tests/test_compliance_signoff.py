from datetime import datetime, timezone
import pytest

from searchleads.operational import ComplianceSignoffRecord, ContactClass, LegalSignoffDecision


def test_compliance_signoff_record_valid_active() -> None:
    record = ComplianceSignoffRecord(
        signoff_id="signoff-001",
        review_authority="legal.counsel@example.test",
        policy_version="policy:v1",
        jurisdiction="BR",
        channel="email",
        decision=LegalSignoffDecision.APPROVED,
        approved_contact_classes=(ContactClass.COMPANY_GENERIC, ContactClass.BUSINESS_PERSONALIZED),
        conditions=("Must respect suppression",),
        reviewed_at=datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc),
        reference="LEGAL-OP-001",
        expires_at=datetime(2027, 8, 31, 10, 0, tzinfo=timezone.utc),
    )
    assert record.is_valid_active is True


def test_compliance_signoff_record_rejected_or_more_review() -> None:
    for decision in [LegalSignoffDecision.REJECTED, LegalSignoffDecision.MORE_REVIEW_REQUIRED]:
        record = ComplianceSignoffRecord(
            signoff_id="signoff-002",
            review_authority="legal.counsel@example.test",
            policy_version="policy:v1",
            jurisdiction="BR",
            channel="email",
            decision=decision,
            approved_contact_classes=(ContactClass.COMPANY_GENERIC,),
            conditions=(),
            reviewed_at=datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc),
            reference="LEGAL-OP-002",
        )
        assert record.is_valid_active is False


def test_compliance_signoff_record_revoked_or_expired() -> None:
    record_expired = ComplianceSignoffRecord(
        signoff_id="signoff-003",
        review_authority="legal.counsel@example.test",
        policy_version="policy:v1",
        jurisdiction="BR",
        channel="email",
        decision=LegalSignoffDecision.APPROVED,
        approved_contact_classes=(ContactClass.COMPANY_GENERIC,),
        conditions=(),
        reviewed_at=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
        reference="LEGAL-OP-003",
        expires_at=datetime(2025, 12, 31, 10, 0, tzinfo=timezone.utc),
    )
    assert record_expired.is_valid_active is False

    record_revoked = ComplianceSignoffRecord(
        signoff_id="signoff-004",
        review_authority="legal.counsel@example.test",
        policy_version="policy:v1",
        jurisdiction="BR",
        channel="email",
        decision=LegalSignoffDecision.APPROVED,
        approved_contact_classes=(ContactClass.COMPANY_GENERIC,),
        conditions=(),
        reviewed_at=datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc),
        reference="LEGAL-OP-004",
        revoked_at=datetime(2026, 8, 31, 11, 0, tzinfo=timezone.utc),
    )
    assert record_revoked.is_valid_active is False
