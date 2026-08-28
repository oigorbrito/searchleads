from __future__ import annotations

from pathlib import Path

import pytest

from searchleads.contact_discovery import (
    ContactDiscoveryContractError,
    NVIDIA_CONTACT_URL,
    discover_nvidia_official_contacts,
)

FIXTURE = Path(__file__).parent / "fixtures" / "nvidia_contact_sample.html"


def test_official_nvidia_page_discovers_email_phone_and_contact_url() -> None:
    batch = discover_nvidia_official_contacts(FIXTURE.read_bytes())
    by_kind = {contact.kind: contact for contact in batch.contacts}

    assert len(batch.contacts) == 3
    assert by_kind["EMAIL"].value == "info@nvidia.com"
    assert by_kind["PHONE"].value == "+1 (408) 486-2000"
    assert by_kind["URL"].value == NVIDIA_CONTACT_URL


def test_discovered_contacts_retain_raw_evidence_and_rule() -> None:
    raw = FIXTURE.read_bytes()
    batch = discover_nvidia_official_contacts(raw)

    assert batch.evidence.raw_content == raw
    assert all(contact.evidence_id == batch.evidence.id for contact in batch.contacts)
    assert all(contact.discovery_rule for contact in batch.contacts)


def test_contact_found_is_not_contact_valid() -> None:
    batch = discover_nvidia_official_contacts(FIXTURE.read_bytes())

    assert all(discovery.status == "DISCOVERED" for discovery in batch.discoveries)
    assert not hasattr(batch, "validations")


def test_known_page_contract_fails_closed_when_expected_contacts_disappear() -> None:
    drifted = b"<html><body><h1>Contact NVIDIA</h1></body></html>"

    with pytest.raises(ContactDiscoveryContractError, match="no longer exposes"):
        discover_nvidia_official_contacts(drifted)
