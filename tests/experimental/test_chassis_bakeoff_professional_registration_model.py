from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum

import pytest

pytest.importorskip("followthemoney")

from followthemoney import Dataset, StatementEntity


class ProfessionalRegistrationStatus(StrEnum):
    VERIFIED_ACTIVE = "VERIFIED_ACTIVE"
    INACTIVE = "INACTIVE"
    NOT_FOUND = "NOT_FOUND"
    PENDING = "PENDING"


@dataclass(frozen=True, slots=True)
class ProfessionalRegistrationCandidate:
    """Experimental SearchLeads registration status, independent of person identity/company relation."""

    registration_id: str
    person_id: str
    authority: str
    jurisdiction: str
    registration_number: str
    status: ProfessionalRegistrationStatus
    evidence_ids: tuple[str, ...]
    checked_at: datetime

    def __post_init__(self) -> None:
        strings = (
            self.registration_id,
            self.person_id,
            self.authority,
            self.jurisdiction,
            self.registration_number,
        )
        if any(not value.strip() for value in strings):
            raise ValueError("registration identity fields must not be blank")
        if not self.evidence_ids or any(not value.strip() for value in self.evidence_ids):
            raise ValueError("professional registration status requires evidence")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("professional registration evidence_ids must not contain duplicates")
        if self.checked_at.tzinfo is None:
            raise ValueError("checked_at must be timezone-aware")


def _dataset() -> Dataset:
    return Dataset.make(
        {
            "name": "searchleads_registration_bakeoff",
            "title": "SearchLeads registration bake-off",
        }
    )


def test_ftm_identification_natively_models_holder_number_authority_and_interval() -> None:
    identification = StatementEntity.from_data(
        _dataset(),
        {
            "id": "identification:cro-pr:22606",
            "schema": "Identification",
            "properties": {
                "holder": ["person:claudia"],
                "number": ["22606"],
                "type": ["CRO"],
                "authority": ["CRO-PR"],
                "country": ["br"],
                "startDate": ["2015-01-01"],
            },
        },
    )

    assert identification.schema.name == "Identification"
    assert identification.get("holder") == ["person:claudia"]
    assert identification.get("number") == ["22606"]
    assert identification.get("type") == ["CRO"]
    assert identification.get("authority") == ["CRO-PR"]
    assert identification.get("country") == ["br"]
    assert identification.get("startDate") == ["2015-01-01"]

    print("PROFESSIONAL_REGISTRATION_FTM_IDENTIFICATION_V1")
    print("holder_native=YES")
    print("registration_number_native=YES")
    print("authority_native=YES")
    print("temporal_interval_native=YES")


def test_generic_ftm_identification_does_not_enforce_searchleads_operational_status() -> None:
    identification = StatementEntity.from_data(
        _dataset(),
        {
            "id": "identification:cro-pr:22606",
            "schema": "Identification",
            "properties": {
                "holder": ["person:claudia"],
                "number": ["22606"],
                "type": ["CRO"],
                "authority": ["CRO-PR"],
            },
        },
    )

    # The generic schema is valid without VERIFIED_ACTIVE/INACTIVE/NOT_FOUND/PENDING.
    # Therefore it cannot by itself satisfy SearchLeads issue #39's operational gate.
    assert identification.schema.name == "Identification"
    assert "status" not in identification.schema.properties

    print("PROFESSIONAL_REGISTRATION_STATUS_GAP_V1")
    print("ftm_identification_valid_without_searchleads_status=YES")
    print("searchleads_status_extension_required=YES")


def test_searchleads_candidate_requires_explicit_status_and_evidence() -> None:
    registration = ProfessionalRegistrationCandidate(
        registration_id="professional-registration:cro-pr:22606",
        person_id="person:claudia",
        authority="CRO-PR",
        jurisdiction="PR",
        registration_number="22606",
        status=ProfessionalRegistrationStatus.VERIFIED_ACTIVE,
        evidence_ids=("evidence:cfo-cro-current-check",),
        checked_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
    )

    assert registration.status is ProfessionalRegistrationStatus.VERIFIED_ACTIVE
    assert registration.evidence_ids == ("evidence:cfo-cro-current-check",)

    with pytest.raises(ValueError, match="requires evidence"):
        ProfessionalRegistrationCandidate(
            registration_id="professional-registration:cro-pr:22606:no-evidence",
            person_id="person:claudia",
            authority="CRO-PR",
            jurisdiction="PR",
            registration_number="22606",
            status=ProfessionalRegistrationStatus.VERIFIED_ACTIVE,
            evidence_ids=(),
            checked_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
        )


def test_registration_status_is_not_inferred_from_missing_end_date() -> None:
    # Absence of an end date is not treated as proof of current official activity.
    # SearchLeads requires an explicit operational status backed by current Evidence.
    identification = StatementEntity.from_data(
        _dataset(),
        {
            "id": "identification:cro-pr:historical",
            "schema": "Identification",
            "properties": {
                "holder": ["person:claudia"],
                "number": ["22606"],
                "type": ["CRO"],
                "authority": ["CRO-PR"],
                "startDate": ["2015-01-01"],
            },
        },
    )

    assert identification.get("endDate") == []

    pending = ProfessionalRegistrationCandidate(
        registration_id="professional-registration:cro-pr:22606:pending",
        person_id="person:claudia",
        authority="CRO-PR",
        jurisdiction="PR",
        registration_number="22606",
        status=ProfessionalRegistrationStatus.PENDING,
        evidence_ids=("evidence:historical-identification-only",),
        checked_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
    )
    assert pending.status is ProfessionalRegistrationStatus.PENDING

    print("PROFESSIONAL_REGISTRATION_NO_ACTIVITY_INFERENCE_V1")
    print("missing_end_date_implies_verified_active=NO")
    print("explicit_current_official_check_required=YES")


def test_person_identity_company_relationship_and_registration_are_independent_axes() -> None:
    person_id = "person:claudia"
    company_relationship_ids = (
        "person-company:claudia:clinic-a",
        "person-company:claudia:clinic-b",
    )
    registrations = (
        ProfessionalRegistrationCandidate(
            registration_id="professional-registration:cro-pr:22606",
            person_id=person_id,
            authority="CRO-PR",
            jurisdiction="PR",
            registration_number="22606",
            status=ProfessionalRegistrationStatus.VERIFIED_ACTIVE,
            evidence_ids=("evidence:cro-pr-current",),
            checked_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
        ),
    )

    assert len({registration.person_id for registration in registrations}) == 1
    assert len(company_relationship_ids) == 2
    assert registrations[0].registration_number == "22606"

    print("PERSON_RELATIONSHIP_REGISTRATION_SEPARATION_V1")
    print("person_identity_axes=1")
    print("company_relationship_axes=2")
    print("professional_registration_axes=1")
    print("registration_status_not_part_of_person_identity=YES")


def test_professional_registration_capability_scorecard() -> None:
    capabilities = {
        "holder_reference": "FTM_NATIVE",
        "registration_number": "FTM_NATIVE",
        "issuing_authority": "FTM_NATIVE",
        "start_end_dates": "FTM_NATIVE",
        "explicit_searchleads_activity_status": "SEARCHLEADS_EXTENSION",
        "mandatory_raw_evidence_reference": "SEARCHLEADS_EXTENSION",
        "checked_at_current_verification_time": "SEARCHLEADS_EXTENSION",
    }

    assert sum(value == "FTM_NATIVE" for value in capabilities.values()) == 4
    assert sum(value == "SEARCHLEADS_EXTENSION" for value in capabilities.values()) == 3

    print("PROFESSIONAL_REGISTRATION_CAPABILITY_SCORECARD_V1")
    for capability, classification in capabilities.items():
        print(f"{capability}={classification}")
