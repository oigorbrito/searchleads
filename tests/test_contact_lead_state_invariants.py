from datetime import datetime, timezone

import pytest

from searchleads.domain import (
    ContactKind,
    ContactPoint,
    ContactStatus,
    Lead,
    LeadStage,
    QualificationStatus,
)

NOW = datetime(2026, 8, 28, 22, 0, tzinfo=timezone.utc)


def test_discovered_contact_cannot_carry_validation_evidence_or_timestamp() -> None:
    with pytest.raises(ValueError, match="DISCOVERED contact cannot carry validation metadata"):
        ContactPoint(
            "contact-1",
            "company-1",
            ContactKind.EMAIL,
            "hello@example.test",
            ("ev-discovery",),
            ContactStatus.DISCOVERED,
            NOW,
            ("ev-validation",),
            NOW,
        )


def test_assessed_contact_still_requires_validation_evidence_and_timestamp() -> None:
    with pytest.raises(ValueError, match="requires validation evidence"):
        ContactPoint(
            "contact-1",
            "company-1",
            ContactKind.EMAIL,
            "hello@example.test",
            ("ev-discovery",),
            ContactStatus.VALIDATED,
            NOW,
        )

    with pytest.raises(ValueError, match="requires validated_at"):
        ContactPoint(
            "contact-2",
            "company-1",
            ContactKind.EMAIL,
            "hello@example.test",
            ("ev-discovery",),
            ContactStatus.INVALID,
            NOW,
            ("ev-validation",),
        )


def test_valid_contact_state_examples_remain_supported() -> None:
    discovered = ContactPoint(
        "contact-discovered",
        "company-1",
        ContactKind.EMAIL,
        "hello@example.test",
        ("ev-discovery",),
        ContactStatus.DISCOVERED,
        NOW,
    )
    validated = ContactPoint(
        "contact-validated",
        "company-1",
        ContactKind.EMAIL,
        "hello@example.test",
        ("ev-discovery",),
        ContactStatus.VALIDATED,
        NOW,
        ("ev-validation",),
        NOW,
    )
    assert discovered.validation_evidence_ids == ()
    assert validated.validation_evidence_ids == ("ev-validation",)


@pytest.mark.parametrize(
    ("stage", "status"),
    [
        (LeadStage.CANDIDATE, QualificationStatus.QUALIFIED),
        (LeadStage.CANDIDATE, QualificationStatus.NOT_QUALIFIED),
        (LeadStage.REVIEW, QualificationStatus.QUALIFIED),
        (LeadStage.REVIEW, QualificationStatus.NOT_QUALIFIED),
        (LeadStage.QUALIFIED, QualificationStatus.UNKNOWN),
        (LeadStage.DISQUALIFIED, QualificationStatus.UNKNOWN),
    ],
)
def test_lead_rejects_incoherent_stage_status_pairs(stage, status) -> None:
    with pytest.raises(ValueError, match="stage requires"):
        Lead("lead-1", "company-1", stage, status, created_at=NOW)


@pytest.mark.parametrize(
    ("stage", "status"),
    [
        (LeadStage.CANDIDATE, QualificationStatus.UNKNOWN),
        (LeadStage.REVIEW, QualificationStatus.UNKNOWN),
        (LeadStage.QUALIFIED, QualificationStatus.QUALIFIED),
        (LeadStage.DISQUALIFIED, QualificationStatus.NOT_QUALIFIED),
    ],
)
def test_lead_accepts_only_coherent_stage_status_pairs(stage, status) -> None:
    lead = Lead("lead-1", "company-1", stage, status, created_at=NOW)
    assert lead.stage is stage
    assert lead.qualification_status is status
