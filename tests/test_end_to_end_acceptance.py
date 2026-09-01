from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

import searchleads.acceptance.end_to_end as e2e
from searchleads.acceptance import load_fixture, run_end_to_end_acceptance

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "end_to_end_acceptance_v1.json"
EXPECTED_SHA256 = "ec1120c4a75058fe933353558ff8b88e605d0bf369c7008171e4c2e1d56671f8"


def fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_end_to_end_acceptance_passes_and_is_reproducible() -> None:
    result = run_end_to_end_acceptance(load_fixture(FIXTURE_PATH))
    assert result.technical_data_path == "PASS"
    assert result.reproducible is True
    assert result.first.export_json == result.second.export_json
    assert result.first.export_sha256 == result.second.export_sha256 == EXPECTED_SHA256
    assert hashlib.sha256(result.first.export_json.encode("utf-8")).hexdigest() == EXPECTED_SHA256
    assert result.first.persistence_replay_ok is True


def test_acceptance_metrics_cover_clean_data_path() -> None:
    run = run_end_to_end_acceptance(fixture()).first
    assert run.discovered_seeds == 1
    assert run.structured_snapshots == 2
    assert run.evidence_records == 6
    assert run.candidate_facts == 18
    assert run.canonical_facts == 1
    assert run.conflicts == 1
    assert run.company_contacts == 6
    assert run.validated_company_contacts == 1
    assert run.people == 1
    assert run.role_facts == 1
    assert run.review_items == 2
    assert run.gap_count == 3
    assert run.ready_actions == 1
    assert run.blocked_actions == 2
    assert run.er_disposition == "AUTO_MATCH"
    assert run.export_csv.startswith("schema_version,company_id,lead_id")


def test_external_and_business_gates_are_not_overclaimed() -> None:
    result = run_end_to_end_acceptance(fixture())
    assert result.live_network_smoke == "NOT_EXECUTED_BY_DETERMINISTIC_ACCEPTANCE"
    assert result.commercial_qualification == "BLOCKED_BY_UNDEFINED_ICP"
    assert result.multi_source_company_enrichment == "NOT_IMPLEMENTED_IN_CLEAN_STACK"


def test_naive_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        e2e._dt("2026-08-25T18:00:00")


def test_zero_discovered_seeds_is_rejected() -> None:
    data = fixture()
    data["directory_html"] = "<html><body><h2>Regional Brasília</h2><p>sem CNPJ</p></body></html>"
    with pytest.raises(AssertionError, match="exactly one discovered seed"):
        e2e._run_once(data)


def test_multiple_discovered_seeds_is_rejected() -> None:
    data = fixture()
    data["directory_html"] += "<h2>Regional Recife</h2><p>Recife / PE</p><p>CNPJ: 33.683.111/0003-60</p>"
    with pytest.raises(AssertionError, match="exactly one discovered seed"):
        e2e._run_once(data)


def test_failed_structured_acquisition_is_rejected() -> None:
    data = fixture()
    data["brasilapi_payloads"][0]["cnpj"] = "00.000.000/0000-00"
    with pytest.raises(AssertionError, match="structured acquisition boundary"):
        e2e._run_once(data)


def test_unexpected_extra_brasilapi_call_is_rejected() -> None:
    data = fixture()
    data["brasilapi_payloads"] = data["brasilapi_payloads"][:1]
    with pytest.raises(AssertionError, match="unexpected extra BrasilAPI transport call"):
        e2e._run_once(data)


def test_legal_name_disagreement_is_not_accepted_as_canonical() -> None:
    data = fixture()
    data["brasilapi_payloads"][1]["razao_social"] = "OUTRA EMPRESA"
    with pytest.raises(AssertionError, match="legal_name snapshots must fuse canonically"):
        e2e._run_once(data)


def test_trade_name_agreement_is_not_accepted_as_conflict() -> None:
    data = fixture()
    data["brasilapi_payloads"][1]["nome_fantasia"] = "SERPRO"
    with pytest.raises(AssertionError, match="trade_name snapshots must remain an explicit conflict"):
        e2e._run_once(data)


def test_nonindependent_contact_evidence_does_not_validate() -> None:
    data = fixture()
    data["contact_pages"][1]["url"] = data["contact_pages"][0]["url"]
    data["timestamps"]["contact_2"] = data["timestamps"]["contact_1"]
    with pytest.raises(AssertionError, match="independent official-page observations"):
        e2e._run_once(data)


def test_people_page_without_role_is_rejected() -> None:
    data = fixture()
    data["people_page"]["html"] = "<html><body><p>Wilton Itaiguara Gonçalves Mota</p></body></html>"
    with pytest.raises(AssertionError, match=r"Person \+ role fact"):
        e2e._run_once(data)


def test_technical_gate_fails_when_reproducibility_is_forced_off(monkeypatch: pytest.MonkeyPatch) -> None:
    original = e2e._run_once
    calls = 0

    # Construct via dataclass fields rather than mutating the frozen result.
    def safe_altered(data):
        nonlocal calls
        run = original(data)
        calls += 1
        if calls == 2:
            values = {name: getattr(run, name) for name in run.__dataclass_fields__}
            values["export_sha256"] = "0" * 64
            return e2e.AcceptanceRun(**values)
        return run

    monkeypatch.setattr(e2e, "_run_once", safe_altered)
    result = e2e.run_end_to_end_acceptance(fixture())
    assert result.reproducible is False
    assert result.technical_data_path == "FAIL"


def test_structured_acquisition_none_result_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    fake_run = SimpleNamespace(attempted=1, succeeded=1, items=(SimpleNamespace(result=None),))
    monkeypatch.setattr(e2e, "acquire_discovered_seeds", lambda discovery, acquire: fake_run)
    with pytest.raises(AssertionError, match="unexpectedly returned no result"):
        e2e._run_once(fixture())


@pytest.mark.parametrize("failed_call", [1, 2])
def test_legal_name_normalization_failure_is_rejected(
    monkeypatch: pytest.MonkeyPatch, failed_call: int
) -> None:
    from types import SimpleNamespace

    original = e2e.normalize_candidate_fact
    legal_calls = 0

    def fake_normalize(fact):
        nonlocal legal_calls
        if fact.field_name == "legal_name":
            legal_calls += 1
            if legal_calls == failed_call:
                return SimpleNamespace(status=e2e.NormalizationStatus.INVALID, normalized_fact=None)
        return original(fact)

    monkeypatch.setattr(e2e, "normalize_candidate_fact", fake_normalize)
    message = "first legal_name normalization failed" if failed_call == 1 else "second legal_name normalization failed"
    with pytest.raises(AssertionError, match=message):
        e2e._run_once(fixture())


def test_non_auto_match_er_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    monkeypatch.setattr(
        e2e,
        "triage_pair",
        lambda left, right: SimpleNamespace(disposition=e2e.ResolutionDisposition.REVIEW),
    )
    with pytest.raises(AssertionError, match="must AUTO_MATCH"):
        e2e._run_once(fixture())


def test_persistence_replay_mismatch_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(e2e.SQLiteRepository, "raw_evidence_bytes", lambda self, evidence_id: b"mismatch")
    with pytest.raises(AssertionError, match="did not replay byte-for-byte"):
        e2e._run_once(fixture())
