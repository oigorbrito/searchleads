from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.chassis_bakeoff_report import build_report, load_claims, load_json_artifact, load_observations, load_raw_artifact
from scripts.empirical_observation import build_observation


def _write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _observation() -> dict[str, object]:
    return build_observation(
        observation_id="runtime-state-restored",
        research_question="Does the runtime preserve request lifecycle state across re-instantiation?",
        method="deterministic persistence functional probe",
        evidence_class="FUNCTIONAL_PROBE",
        payload={"request_state_restored": True},
        validity_limits=["single controlled local environment"],
    )


def _claim(**overrides: object) -> dict[str, object]:
    claim: dict[str, object] = {
        "claim_id": "runtime-persistence",
        "research_question": "Does the runtime preserve request lifecycle state across re-instantiation?",
        "method": "FUNCTIONAL_PROBE",
        "evidence_class": "FUNCTIONAL_PROBE",
        "input_artifacts": ["observations/runtime.json"],
        "observations": ["runtime-state-restored"],
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
    observation_path = _write_json(tmp_path / "observation.json", _observation())
    claim_path = _write_json(tmp_path / "claim.json", _claim(input_artifacts=[observation_path.as_posix()]))
    junit_path = tmp_path / "junit.xml"
    junit_path.write_text('<testsuite tests="1" failures="0" skipped="0"/>', encoding="utf-8")
    manifest = load_json_artifact(manifest_path)
    junit = [load_raw_artifact(junit_path)]
    observations = load_observations([observation_path])
    claims = load_claims([claim_path])
    first = build_report(study_id="study-1", manifest=manifest, junit=junit, observations=observations, claims=claims)
    second = build_report(study_id="study-1", manifest=manifest, junit=junit, observations=observations, claims=claims)
    assert first == second
    assert first["claims"][0]["evidence_state"] == "SUPPORTED"
    assert first["claims"][0]["decision_state"] == "DEFER"
    assert first["claims"][0]["decision_support"]["eligible_from_current_evidence"] is False
    assert first["junit_summaries"][0]["passed"] == 1
    assert len(first["report_sha256"]) == 64


def test_missing_claim_evidence_is_downgraded(tmp_path: Path) -> None:
    manifest_path = _write_json(tmp_path / "manifest.json", {"python": "3.12"})
    claim_path = _write_json(tmp_path / "claim.json", _claim())
    report = build_report(study_id="study-missing-evidence", manifest=load_json_artifact(manifest_path), junit=[], observations=[], claims=load_claims([claim_path]))
    claim = report["claims"][0]
    assert claim["declared_evidence_state"] == "SUPPORTED"
    assert claim["evidence_state"] == "INSUFFICIENT_EVIDENCE"
    assert claim["decision_support"]["eligible_from_current_evidence"] is False


def test_missing_observation_reference_downgrades_claim_even_when_file_is_present(tmp_path: Path) -> None:
    manifest_path = _write_json(tmp_path / "manifest.json", {"python": "3.12"})
    observation_path = _write_json(tmp_path / "observation.json", _observation())
    claim_path = _write_json(tmp_path / "claim.json", _claim(input_artifacts=[observation_path.as_posix()], observations=["different-observation-id"]))
    report = build_report(study_id="study-missing-observation", manifest=load_json_artifact(manifest_path), junit=[], observations=load_observations([observation_path]), claims=load_claims([claim_path]))
    claim = report["claims"][0]
    assert claim["evidence_state"] == "INSUFFICIENT_EVIDENCE"
    assert claim["traceability"]["all_inputs_present"] is True
    assert claim["traceability"]["all_observations_present"] is False


def test_claim_rejects_opaque_or_unknown_state(tmp_path: Path) -> None:
    claim_path = _write_json(tmp_path / "claim.json", _claim(decision_state="WINNER"))
    with pytest.raises(ValueError, match="unsupported decision_state"):
        load_claims([claim_path])


def test_duplicate_claim_ids_are_rejected(tmp_path: Path) -> None:
    claim_path = _write_json(tmp_path / "claims.json", [_claim(), _claim()])
    with pytest.raises(ValueError, match="duplicate claim_id"):
        load_claims([claim_path])
