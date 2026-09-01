from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.chassis_bakeoff_report import load_observations
from scripts.empirical_observation import build_observation, write_observation


def _observation(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "observation_id": "runtime-restart",
        "research_question": "Does runtime state survive re-instantiation?",
        "method": "deterministic fault-injection functional probe",
        "evidence_class": "FUNCTIONAL_PROBE",
        "payload": {"restart_preserves_state": False},
        "validity_limits": ["single-process controlled environment"],
    }
    value.update(overrides)
    return build_observation(**value)  # type: ignore[arg-type]


def test_observation_writer_is_opt_in_and_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEARCHLEADS_EMPIRICAL_OBSERVATION_DIR", raising=False)
    assert write_observation(**{
        "observation_id": "runtime-restart",
        "research_question": "Does runtime state survive re-instantiation?",
        "method": "deterministic fault-injection functional probe",
        "evidence_class": "FUNCTIONAL_PROBE",
        "payload": {"restart_preserves_state": False},
        "validity_limits": ["single-process controlled environment"],
    }) is None

    output_dir = tmp_path / "observations"
    monkeypatch.setenv("SEARCHLEADS_EMPIRICAL_OBSERVATION_DIR", str(output_dir))
    first = write_observation(**{
        "observation_id": "runtime-restart",
        "research_question": "Does runtime state survive re-instantiation?",
        "method": "deterministic fault-injection functional probe",
        "evidence_class": "FUNCTIONAL_PROBE",
        "payload": {"restart_preserves_state": False},
        "validity_limits": ["single-process controlled environment"],
    })
    second = write_observation(**{
        "observation_id": "runtime-restart",
        "research_question": "Does runtime state survive re-instantiation?",
        "method": "deterministic fault-injection functional probe",
        "evidence_class": "FUNCTIONAL_PROBE",
        "payload": {"restart_preserves_state": False},
        "validity_limits": ["single-process controlled environment"],
    })

    assert first == second
    assert first is not None
    payload = json.loads(first.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "searchleads_empirical_observation_v1"
    assert payload["payload"]["restart_preserves_state"] is False


def test_observation_writer_rejects_same_id_with_different_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEARCHLEADS_EMPIRICAL_OBSERVATION_DIR", str(tmp_path))
    common = {
        "observation_id": "runtime-restart",
        "research_question": "Does runtime state survive re-instantiation?",
        "method": "deterministic fault-injection functional probe",
        "evidence_class": "FUNCTIONAL_PROBE",
        "validity_limits": ["single-process controlled environment"],
    }
    write_observation(**common, payload={"restart_preserves_state": False})
    with pytest.raises(ValueError, match="observation_id collision"):
        write_observation(**common, payload={"restart_preserves_state": True})


def test_report_loader_validates_observation_contract_and_duplicate_ids(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(json.dumps(_observation()), encoding="utf-8")
    second.write_text(json.dumps(_observation()), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate observation_id"):
        load_observations([first, second])

    invalid = tmp_path / "invalid.json"
    payload = _observation()
    payload["schema_version"] = "unknown"
    invalid.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported observation schema_version"):
        load_observations([invalid])
