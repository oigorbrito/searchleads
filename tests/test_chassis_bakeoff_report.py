from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.chassis_bakeoff_report import (
    ArtifactRecord,
    build_report,
    load_claims,
    load_json_artifact,
    load_raw_artifact,
)


def _write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _claim(**overrides: object) -> dict[str, object]:
    claim: dict[str, object] = {
        "claim_id": "runtime-persistence",
        "research_question": "Does the runtime preserve request lifecycle state across re-instantiation?",
        "method": "FUNCTIONAL_PROBE",
        "evidence_class": "FUNCTIONAL_PROBE",
        "input_artifacts": ["observations/runtime.json"],
        "observations": ["request state restored"],
        "analysis": "Observed state restoration under the declared probe conditions.",
        "validity_limits": ["single controlled local environment"],
        "supported_conclusion": "Persistence is demonstrated under the probe conditions.",
        "unsupported_conclusions": ["production reliability improvement"],
        "evidence_state": "SUPPORTED",
        "decision_state": "DEFER",
    }
    claim.update(overrides)
    return claim


def test_report_is_deterministic_and_traceable(tmp_path: Path) -> None:
    manifest_path = _write_json(tmp_path / "manifest.json", {"python": "3.12", "sha": "abc"})
    observation_path = _write_json(tmp_path / "observation.json", {"attempts": [1, 2, 3]})
    claim_path = _write_json(tmp_path / "claim.json", _claim())
    junit_path = tmp_path / "junit.xml"
    junit_path.write_text('<testsuite tests="1" failures="0" skipped="0"/>', encoding="utf-8")

    manifest = load_json_artifact(manifest_path)
    junit = [load_raw_artifact(junit_path)]
    observations = [load_json_artifact(observation_path)]
    claims = load_claims([claim_path])

    first = build_report(
        study_id="study-1",
        manifest=manifest,
        junit=junit,
        observations=observations,
        claims=claims,
    )
    second = build_report(
        study_id="study-1",
        manifest=manifest,
        junit=junit,
        observations=observations,
        claims=claims,
    )

    assert first == second
    assert first["claims"][0]["evidence_state"] == "SUPPORTED"
    assert first["claims"][0]["decision_state"] == "DEFER"
    paths = {item["path"] for item in first["artifacts"]}
    assert manifest.path in paths
    assert junit[0].path in paths
    assert observations[0].path in paths
    assert claims[0].path in paths
    assert len(first["report_sha256"]) == 64


def test_claim_rejects_opaque_or_unknown_state(tmp_path: Path) -> None:
    claim_path = _write_json(tmp_path / "claim.json", _claim(decision_state="WINNER"))
    with pytest.raises(ValueError, match="unsupported decision_state"):
        load_claims([claim_path])


def test_missing_required_claim_field_is_insufficient_input(tmp_path: Path) -> None:
    claim = _claim()
    del claim["validity_limits"]
    claim_path = _write_json(tmp_path / "claim.json", claim)
    with pytest.raises(ValueError, match="claim missing required fields"):
        load_claims([claim_path])


def test_duplicate_claim_ids_are_rejected(tmp_path: Path) -> None:
    claim_path = _write_json(tmp_path / "claims.json", [_claim(), _claim()])
    with pytest.raises(ValueError, match="duplicate claim_id"):
        load_claims([claim_path])
