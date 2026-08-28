from __future__ import annotations

from pathlib import Path

from searchleads.contact_discovery import discover_nvidia_official_contacts
from searchleads.contact_validation import BASIC_SYNTAX_ONLY_V1, validate_contact_syntax, validate_contacts_syntax
from searchleads.domain import ContactPoint, ContactValidationStatus
from searchleads.person_discovery import discover_jensen_huang_profile

CONTACT_FIXTURE = Path(__file__).parent / "fixtures" / "nvidia_contact_sample.html"
PROFILE_FIXTURE = Path(__file__).parent / "fixtures" / "nvidia_jensen_profile_sample.html"


def _contact(kind: str, value: str) -> ContactPoint:
    return ContactPoint(
        id=f"contact:test:{kind}:{value}",
        owner_type="Company",
        owner_id="company:test",
        kind=kind,
        value=value,
        evidence_id="evidence:test",
        discovery_rule="TEST",
    )


def test_plausible_email_phone_and_url_remain_unknown() -> None:
    contacts = (
        _contact("EMAIL", "info@example.com"),
        _contact("PHONE", "+1 (408) 486-2000"),
        _contact("URL", "https://example.com/contact"),
    )

    validations = validate_contacts_syntax(contacts)

    assert {item.status for item in validations} == {ContactValidationStatus.UNKNOWN}
    assert all(item.rule == BASIC_SYNTAX_ONLY_V1 for item in validations)


def test_obviously_malformed_values_are_invalid() -> None:
    contacts = (
        _contact("EMAIL", "not-an-email"),
        _contact("PHONE", "abc"),
        _contact("URL", "javascript:alert(1)"),
    )

    assert {
        validate_contact_syntax(contact).status for contact in contacts
    } == {ContactValidationStatus.INVALID}


def test_syntax_only_never_produces_valid_or_stale() -> None:
    values = (
        _contact("EMAIL", "info@example.com"),
        _contact("PHONE", "+1 (408) 486-2000"),
        _contact("URL", "https://example.com"),
        _contact("EMAIL", "bad"),
    )

    statuses = {validate_contact_syntax(contact).status for contact in values}

    assert ContactValidationStatus.VALID not in statuses
    assert ContactValidationStatus.STALE not in statuses


def test_discovered_nvidia_contacts_plus_profile_produce_four_unknown_validations() -> None:
    company_contacts = discover_nvidia_official_contacts(CONTACT_FIXTURE.read_bytes()).contacts
    profile = discover_jensen_huang_profile(PROFILE_FIXTURE.read_bytes()).professional_profile

    validations = validate_contacts_syntax(company_contacts + (profile,))

    assert len(validations) == 4
    assert all(item.status is ContactValidationStatus.UNKNOWN for item in validations)
