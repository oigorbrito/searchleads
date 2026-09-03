from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from searchleads.campaign_preflight import ReviewDecision
from searchleads.governance_decision_io import (
    campaign_authorization_from_mapping,
    campaign_authorization_to_mapping,
    compliance_signoff_from_mapping,
    compliance_signoff_to_mapping,
)


def compliance_payload(**overrides):
    payload = {
        "signoff_id": "legal:1",
        "reviewer_reference": "reviewer:legal",
        "policy_id": "policy:commercial-pilot:v1",
        "policy_version": "v1",
        "jurisdiction": "BR",
        "channel": "email",
        "campaign_id": "campaign:pilot-1",
        "decision": "APPROVED_WITH_CONDITIONS",
        "decided_at": "2026-09-03T19:00:00-03:00",
        "expires_at": "2026-09-10T19:00:00-03:00",
        "conditions": ["suppression check before batch"],
        "authority_evidence_refs": ["evidence:legal:1"],
        "revoked_at": None,
    }
    payload.update(overrides)
    return payload


def authorization_payload(**overrides):
    payload = {
        "authorization_id": "auth:1",
        "campaign_id": "campaign:pilot-1",
        "policy_id": "policy:commercial-pilot:v1",
        "policy_version": "v1",
        "authorizer_reference": "owner:campaign",
        "authorized_at": "2026-09-03T19:05:00-03:00",
        "valid_until": "2026-09-04T19:05:00-03:00",
        "revoked_at": None,
    }
    payload.update(overrides)
    return payload


def test_compliance_signoff_roundtrip_is_canonical():
    record = compliance_signoff_from_mapping(compliance_payload())
    assert record.decision is ReviewDecision.APPROVED_WITH_CONDITIONS
    assert compliance_signoff_to_mapping(record) == compliance_payload()


def test_campaign_authorization_roundtrip_is_canonical():
    record = campaign_authorization_from_mapping(authorization_payload())
    assert campaign_authorization_to_mapping(record) == authorization_payload()


@pytest.mark.parametrize(
    "payload",
    [
        compliance_payload(decision="UNKNOWN"),
        compliance_payload(decided_at="2026-09-03T19:00:00"),
        compliance_payload(decision="APPROVED_WITH_CONDITIONS", conditions=[]),
        compliance_payload(authority_evidence_refs=[""]),
        compliance_payload(reviewer_reference=" "),
    ],
)
def test_compliance_signoff_rejects_invalid_payload(payload):
    with pytest.raises(ValueError):
        compliance_signoff_from_mapping(payload)


@pytest.mark.parametrize(
    "payload",
    [
        authorization_payload(authorized_at="2026-09-03T19:05:00"),
        authorization_payload(authorizer_reference=""),
        authorization_payload(valid_until="not-a-date"),
    ],
)
def test_campaign_authorization_rejects_invalid_payload(payload):
    with pytest.raises(ValueError):
        campaign_authorization_from_mapping(payload)


def test_cli_success_and_invalid_exit_codes(tmp_path: Path):
    script = Path(__file__).parents[1] / "scripts" / "validate_governance_decision.py"

    valid = tmp_path / "valid.json"
    valid.write_text(json.dumps(compliance_payload()), encoding="utf-8")
    ok = subprocess.run(
        [sys.executable, str(script), "compliance-signoff", str(valid)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert ok.returncode == 0
    assert json.loads(ok.stdout) == compliance_payload()

    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps(compliance_payload(decision="UNKNOWN")), encoding="utf-8")
    bad = subprocess.run(
        [sys.executable, str(script), "compliance-signoff", str(invalid)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert bad.returncode == 2
    assert bad.stderr.startswith("INVALID: ")
