from datetime import datetime, timezone
import pytest

from searchleads.operational import FreshnessPolicy, HumanVerificationRecord, HumanVerificationStatus


def test_human_verification_record_valid_active() -> None:
    record = HumanVerificationRecord(
        verification_id="hvr-001",
        registration_number="CRO-SP-12345",
        council="CRO-SP",
        subject_identity_ref="person:001",
        observed_status=HumanVerificationStatus.VERIFIED,
        verified_at=datetime(2026, 8, 30, 10, 0, tzinfo=timezone.utc),
        source_reference="https://crosp.org.br/consulta",
        evidence_refs=("evidence:001",),
        reviewer_authority="operator:jules",
        revalidation_policy=FreshnessPolicy.REVALIDATE_ON_EXPIRY,
        relationship_context="dental-clinic-owner",
        expires_at=datetime(2027, 8, 30, 10, 0, tzinfo=timezone.utc),
    )
    assert record.is_valid_active is True


def test_human_verification_record_inactive_statuses() -> None:
    for status in [
        HumanVerificationStatus.REQUESTED,
        HumanVerificationStatus.IN_PROGRESS,
        HumanVerificationStatus.NOT_FOUND,
        HumanVerificationStatus.CONFLICT,
        HumanVerificationStatus.EXPIRED,
        HumanVerificationStatus.REJECTED,
    ]:
        record = HumanVerificationRecord(
            verification_id="hvr-002",
            registration_number="CRO-SP-12345",
            council="CRO-SP",
            subject_identity_ref="person:001",
            observed_status=status,
            verified_at=datetime(2026, 8, 30, 10, 0, tzinfo=timezone.utc),
            source_reference="https://crosp.org.br/consulta",
            evidence_refs=("evidence:001",),
            reviewer_authority="operator:jules",
        )
        assert record.is_valid_active is False


def test_human_verification_record_expired() -> None:
    record = HumanVerificationRecord(
        verification_id="hvr-003",
        registration_number="CRO-SP-12345",
        council="CRO-SP",
        subject_identity_ref="person:001",
        observed_status=HumanVerificationStatus.VERIFIED,
        verified_at=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
        source_reference="https://crosp.org.br/consulta",
        evidence_refs=("evidence:001",),
        reviewer_authority="operator:jules",
        expires_at=datetime(2025, 12, 31, 10, 0, tzinfo=timezone.utc),
    )
    assert record.is_valid_active is False


def test_human_verification_record_rejects_blank_fields() -> None:
    with pytest.raises(ValueError):
        HumanVerificationRecord(
            verification_id="",
            registration_number="CRO-SP-12345",
            council="CRO-SP",
            subject_identity_ref="person:001",
            observed_status=HumanVerificationStatus.VERIFIED,
            verified_at=datetime(2026, 8, 30, 10, 0, tzinfo=timezone.utc),
            source_reference="https://crosp.org.br/consulta",
            evidence_refs=("evidence:001",),
            reviewer_authority="operator:jules",
        )
