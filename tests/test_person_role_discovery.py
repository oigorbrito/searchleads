from __future__ import annotations

from pathlib import Path

import pytest

from searchleads.person_discovery import (
    JENSEN_PROFILE_URL,
    PersonDiscoveryContractError,
    discover_jensen_huang_profile,
)

FIXTURE = Path(__file__).parent / "fixtures" / "nvidia_jensen_profile_sample.html"


def test_official_profile_discovers_jensen_and_role() -> None:
    batch = discover_jensen_huang_profile(FIXTURE.read_bytes())

    assert batch.person.name == "Jensen Huang"
    assert batch.role.title == "Founder & CEO"
    assert batch.role.person_id == batch.person.id
    assert batch.role.company_id == "company:sec:cik:0001045810"


def test_person_and_role_are_supported_by_same_raw_evidence() -> None:
    raw = FIXTURE.read_bytes()
    batch = discover_jensen_huang_profile(raw)

    assert batch.evidence.raw_content == raw
    assert batch.person.evidence_id == batch.evidence.id
    assert batch.role.evidence_id == batch.evidence.id


def test_official_professional_profile_is_discovered_as_url_contact() -> None:
    batch = discover_jensen_huang_profile(FIXTURE.read_bytes())

    assert batch.professional_profile.owner_type == "Person"
    assert batch.professional_profile.owner_id == batch.person.id
    assert batch.professional_profile.kind == "URL"
    assert batch.professional_profile.value == JENSEN_PROFILE_URL


def test_no_personal_email_is_inferred() -> None:
    batch = discover_jensen_huang_profile(FIXTURE.read_bytes())

    assert batch.professional_profile.kind == "URL"
    assert "@" not in batch.professional_profile.value
    assert not hasattr(batch, "personal_email")


def test_profile_contract_fails_closed_without_expected_role() -> None:
    drifted = b"<html><body><h1>Jensen Huang</h1></body></html>"

    with pytest.raises(PersonDiscoveryContractError, match="no longer exposes"):
        discover_jensen_huang_profile(drifted)
