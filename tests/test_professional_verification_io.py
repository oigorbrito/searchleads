from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from searchleads.campaign_preflight import VerificationDecision
from searchleads.professional_verification_io import (
    professional_verification_from_mapping,
    professional_verification_to_mapping,
)


def payload(**overrides):
    values = {
        "verification_id": "verification:cfo:1",
        "person_id": "person:1",
        "council": "CRO-SP",
        "registration_number": "12345",
        "decision": "VERIFIED_ACTIVE",
        "verified_at": "2026-09-03T12:00:00-03:00",
        "evidence_refs": ["evidence:cfo:official:1"],
        "reviewer_reference": "reviewer:human",
        "expires_at": "2026-09-10T12:00:00-03:00",
    }
    values.update(overrides)
    return values


def test_payload_roundtrip_uses_domain_contract():
    record = professional_verification_from_mapping(payload())
    assert record.decision is VerificationDecision.VERIFIED_ACTIVE
    assert record.verified_at.tzinfo is not None
    assert professional_verification_to_mapping(record) == payload()


@pytest.mark.parametrize(
    "overrides",
    [
        {"decision": "PENDING"},
        {"decision": "UNKNOWN"},
        {"verified_at": "2026-09-03T12:00:00"},
        {"evidence_refs": []},
        {"evidence_refs": [""]},
        {"reviewer_reference": ""},
    ],
)
def test_invalid_or_non_verifiable_payloads_fail_closed(overrides):
    with pytest.raises(ValueError):
        professional_verification_from_mapping(payload(**overrides))


def test_cli_outputs_canonical_json(tmp_path: Path):
    source = tmp_path / "verification.json"
    source.write_text(json.dumps(payload()), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_professional_verification.py", str(source)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout) == payload()
    assert result.stderr == ""


def test_cli_returns_two_for_pending_payload(tmp_path: Path):
    source = tmp_path / "verification.json"
    source.write_text(json.dumps(payload(decision="PENDING")), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/validate_professional_verification.py", str(source)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "INVALID:" in result.stderr
