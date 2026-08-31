from __future__ import annotations

from datetime import datetime, timezone
from email.message import Message
from io import BytesIO
import json
from urllib.error import HTTPError, URLError

import pytest

from searchleads.domain import CandidateFact, Company, DecisionClass, Evidence, Provenance
from searchleads.persistence import SQLiteRepository
from searchleads.sources.brasilapi import (
    BASE_URL,
    SOURCE_ID,
    USER_AGENT,
    BrasilAPIAcquisitionError,
    BrasilAPIPayloadError,
    BrasilAPIResponseError,
    BrasilAPISource,
    HTTPObservation,
    _build_request,
    _headers_dict,
    http_get,
    normalize_cnpj_key,
)

NOW = datetime(2026, 8, 24, 20, 30, tzinfo=timezone.utc)
LATER = datetime(2026, 8, 24, 20, 31, tzinfo=timezone.utc)
CNPJ = "33683111000280"


def payload(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "cnpj": CNPJ,
        "razao_social": "SERVICO FEDERAL DE PROCESSAMENTO DE DADOS (SERPRO)",
        "nome_fantasia": "REGIONAL BRASILIA-DF",
        "descricao_situacao_cadastral": "ATIVA",
        "cnae_fiscal": 6204000,
        "cnae_fiscal_descricao": "Consultoria em tecnologia da informação",
        "municipio": "BRASILIA",
        "uf": "DF",
        "email": "ignored@example.test",
        "ddd_telefone_1": "ignored",
        "qsa": [{"nome_socio": "ignored"}],
    }
    value.update(overrides)
    return value


def observation(data: object | None = None, *, raw: str | None = None, status: int = 200, at: datetime = NOW) -> HTTPObservation:
    body = raw if raw is not None else json.dumps(payload() if data is None else data, ensure_ascii=False)
    return HTTPObservation(
        f"{BASE_URL}/{CNPJ}",
        status,
        body,
        at,
        {"content-type": "application/json", "x-test": "fixture"},
    )


@pytest.mark.parametrize(
    "value,expected",
    [
        ("33.683.111/0002-80", CNPJ),
        (CNPJ, CNPJ),
        ("12.ABC.345/01DE-67", "12ABC34501DE67"),
        ("12.abc.345/01de-67", "12ABC34501DE67"),
    ],
)
def test_normalize_cnpj_key_accepts_current_numeric_and_alphanumeric_contract(value: str, expected: str) -> None:
    assert normalize_cnpj_key(value) == expected


@pytest.mark.parametrize("value", ["123", "12_AB.345/01DE-67", "12ABC34501DE678", ""])
def test_normalize_cnpj_key_rejects_invalid_keys(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_cnpj_key(value)


def test_normalize_cnpj_key_requires_string() -> None:
    with pytest.raises(TypeError):
        normalize_cnpj_key(123)  # type: ignore[arg-type]


def test_url_for_uses_clean_current_key() -> None:
    assert BrasilAPISource.url_for("33.683.111/0002-80") == f"{BASE_URL}/{CNPJ}"


def test_request_has_explicit_user_agent_and_json_accept_header() -> None:
    request = _build_request(f"{BASE_URL}/{CNPJ}")
    assert request.get_method() == "GET"
    assert request.get_header("User-agent") == USER_AGENT
    assert request.get_header("Accept") == "application/json"


def test_http_observation_requires_valid_url_status_and_aware_time() -> None:
    with pytest.raises(ValueError):
        HTTPObservation(" ", 200, "{}", NOW)
    with pytest.raises(ValueError):
        HTTPObservation("x", 99, "{}", NOW)
    with pytest.raises(ValueError):
        HTTPObservation("x", 600, "{}", NOW)
    with pytest.raises(ValueError):
        HTTPObservation("x", 200, "{}", datetime(2026, 8, 24, 20, 30))


def test_successful_ingestion_persists_raw_evidence_before_source_facts() -> None:
    raw = '{\n  "cnpj": "33683111000280", "razao_social": "SERVICO FEDERAL DE PROCESSAMENTO DE DADOS (SERPRO)",\n  "uf": "DF"\n}'
    adapter = BrasilAPISource(lambda url: observation(raw=raw))
    with SQLiteRepository() as repo:
        result = adapter.ingest(CNPJ, repo)
        assert result.evidence.raw_payload == raw
        assert repo.raw_evidence_bytes(result.evidence.evidence_id) == raw.encode("utf-8")
        assert result.company.company_id == f"company:brasilapi-cnpj:{CNPJ}"
        assert {fact.field_name for fact in result.candidate_facts} == {"business_registry_id", "legal_name", "state"}


def test_ingestion_maps_only_bounded_company_fields_without_normalization() -> None:
    adapter = BrasilAPISource(lambda url: observation())
    with SQLiteRepository() as repo:
        result = adapter.ingest(CNPJ, repo)
        by_field = {fact.field_name: fact for fact in result.candidate_facts}
        assert set(by_field) == {
            "business_registry_id",
            "legal_name",
            "trade_name",
            "registration_status",
            "primary_cnae_code",
            "primary_cnae_description",
            "city",
            "state",
        }
        assert by_field["legal_name"].raw_value == payload()["razao_social"]
        assert by_field["primary_cnae_code"].raw_value == 6204000
        assert all(fact.normalized_value is None for fact in by_field.values())
        assert all(fact.decision_class is DecisionClass.EVIDENCE_BACKED for fact in by_field.values())
        assert "email" not in by_field
        assert "qsa" not in by_field


def test_candidate_facts_link_to_persisted_evidence_and_provenance() -> None:
    adapter = BrasilAPISource(lambda url: observation())
    with SQLiteRepository() as repo:
        result = adapter.ingest(CNPJ, repo)
        for provenance, fact in zip(result.provenances, result.candidate_facts, strict=True):
            assert provenance.evidence_ids == (result.evidence.evidence_id,)
            assert fact.evidence_ids == (result.evidence.evidence_id,)
            assert fact.provenance_id == provenance.provenance_id
            assert repo.load(Provenance, provenance.provenance_id) == provenance
            assert repo.load(CandidateFact, fact.fact_id) == fact


def test_optional_blank_source_fields_are_skipped() -> None:
    data = payload(nome_fantasia="  ", cnae_fiscal_descricao=None, municipio="")
    adapter = BrasilAPISource(lambda url: observation(data))
    with SQLiteRepository() as repo:
        fields = {fact.field_name for fact in adapter.ingest(CNPJ, repo).candidate_facts}
        assert "trade_name" not in fields
        assert "primary_cnae_description" not in fields
        assert "city" not in fields
        assert "legal_name" in fields


def test_alphanumeric_cnpj_response_matches_requested_key() -> None:
    cnpj = "12ABC34501DE67"
    body = payload(cnpj="12.ABC.345/01DE-67", razao_social="ALFA LTDA")
    obs = HTTPObservation(f"{BASE_URL}/{cnpj}", 200, json.dumps(body), NOW)
    adapter = BrasilAPISource(lambda url: obs)
    with SQLiteRepository() as repo:
        result = adapter.ingest("12.abc.345/01de-67", repo)
        assert result.company.company_id.endswith(cnpj)
        registry = next(fact for fact in result.candidate_facts if fact.field_name == "business_registry_id")
        assert registry.raw_value == "12.ABC.345/01DE-67"
        assert registry.normalized_value is None


def test_mismatched_response_cnpj_is_preserved_as_evidence_then_rejected() -> None:
    adapter = BrasilAPISource(lambda url: observation(payload(cnpj="00000000000000")))
    with SQLiteRepository() as repo:
        with pytest.raises(BrasilAPIPayloadError) as exc:
            adapter.ingest(CNPJ, repo)
        assert repo.load_evidence(exc.value.evidence_id) is not None
        assert repo.load(Company, f"company:brasilapi-cnpj:{CNPJ}") is None


@pytest.mark.parametrize("bad_cnpj", [None, 33683111000280, "bad"])
def test_invalid_response_cnpj_is_evidence_then_payload_error(bad_cnpj: object) -> None:
    adapter = BrasilAPISource(lambda url: observation(payload(cnpj=bad_cnpj)))
    with SQLiteRepository() as repo:
        with pytest.raises(BrasilAPIPayloadError) as exc:
            adapter.ingest(CNPJ, repo)
        assert repo.load_evidence(exc.value.evidence_id) is not None


@pytest.mark.parametrize("name", [None, "", "   ", 123])
def test_missing_or_invalid_legal_name_is_evidence_then_payload_error(name: object) -> None:
    adapter = BrasilAPISource(lambda url: observation(payload(razao_social=name)))
    with SQLiteRepository() as repo:
        with pytest.raises(BrasilAPIPayloadError) as exc:
            adapter.ingest(CNPJ, repo)
        assert repo.load_evidence(exc.value.evidence_id) is not None
        assert repo.load(Company, f"company:brasilapi-cnpj:{CNPJ}") is None


@pytest.mark.parametrize("raw", ["not-json", "[]", '"string"'])
def test_invalid_json_shape_is_persisted_before_rejection(raw: str) -> None:
    adapter = BrasilAPISource(lambda url: observation(raw=raw))
    with SQLiteRepository() as repo:
        with pytest.raises(BrasilAPIPayloadError) as exc:
            adapter.ingest(CNPJ, repo)
        evidence = repo.load_evidence(exc.value.evidence_id)
        assert evidence is not None
        assert evidence.raw_payload == raw


@pytest.mark.parametrize("status", [400, 403, 404, 429, 500])
def test_non_200_http_body_is_persisted_then_response_error(status: int) -> None:
    adapter = BrasilAPISource(lambda url: observation(raw=f"error-{status}", status=status))
    with SQLiteRepository() as repo:
        with pytest.raises(BrasilAPIResponseError) as exc:
            adapter.ingest(CNPJ, repo)
        assert exc.value.status_code == status
        evidence = repo.load_evidence(exc.value.evidence_id)
        assert evidence is not None
        assert evidence.raw_payload == f"error-{status}"
        assert evidence.metadata["http_status"] == status


def test_transport_url_mismatch_is_rejected_before_persistence() -> None:
    wrong = HTTPObservation("https://wrong.example", 200, "{}", NOW)
    adapter = BrasilAPISource(lambda url: wrong)
    with SQLiteRepository() as repo:
        with pytest.raises(BrasilAPIAcquisitionError):
            adapter.ingest(CNPJ, repo)
        assert repo.load(Company, f"company:brasilapi-cnpj:{CNPJ}") is None


def test_same_payload_is_content_idempotent_even_if_recaptured_later() -> None:
    body = json.dumps(payload(), ensure_ascii=False)
    observations = iter([
        HTTPObservation(f"{BASE_URL}/{CNPJ}", 200, body, NOW),
        HTTPObservation(f"{BASE_URL}/{CNPJ}", 200, body, LATER),
    ])
    adapter = BrasilAPISource(lambda url: next(observations))
    with SQLiteRepository() as repo:
        first = adapter.ingest(CNPJ, repo)
        second = adapter.ingest(CNPJ, repo)
        assert first.evidence.evidence_id == second.evidence.evidence_id
        assert first.evidence.captured_at == NOW
        assert second.evidence.captured_at == NOW
        assert first.evidence_was_new is True
        assert second.evidence_was_new is False
        assert first.company_was_new is True
        assert second.company_was_new is False
        assert first.candidate_facts == second.candidate_facts


def test_changed_payload_creates_new_evidence_and_facts_but_reuses_company() -> None:
    first_body = json.dumps(payload(nome_fantasia="REGIONAL BRASILIA-DF"), ensure_ascii=False)
    second_body = json.dumps(payload(nome_fantasia="REGIONAL BRASILIA"), ensure_ascii=False)
    observations = iter([
        HTTPObservation(f"{BASE_URL}/{CNPJ}", 200, first_body, NOW),
        HTTPObservation(f"{BASE_URL}/{CNPJ}", 200, second_body, LATER),
    ])
    adapter = BrasilAPISource(lambda url: next(observations))
    with SQLiteRepository() as repo:
        first = adapter.ingest(CNPJ, repo)
        second = adapter.ingest(CNPJ, repo)
        assert first.evidence.evidence_id != second.evidence.evidence_id
        assert first.company == second.company
        assert first.company_was_new is True
        assert second.company_was_new is False
        assert {fact.fact_id for fact in first.candidate_facts}.isdisjoint(
            {fact.fact_id for fact in second.candidate_facts}
        )


def test_records_survive_database_reopen(tmp_path) -> None:
    path = tmp_path / "source.sqlite3"
    adapter = BrasilAPISource(lambda url: observation())
    with SQLiteRepository(path) as repo:
        result = adapter.ingest(CNPJ, repo)
        evidence_id = result.evidence.evidence_id
        fact_ids = [fact.fact_id for fact in result.candidate_facts]
    with SQLiteRepository(path) as repo:
        assert repo.load_evidence(evidence_id) == result.evidence
        assert repo.load(Company, result.company.company_id) == result.company
        assert [repo.load(CandidateFact, fact_id) for fact_id in fact_ids] == list(result.candidate_facts)
        assert repo.load(type(result.source), SOURCE_ID) == result.source


def test_http_error_transport_returns_observation_for_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    headers = Message()
    headers["Content-Type"] = "application/json; charset=utf-8"
    error = HTTPError(
        f"{BASE_URL}/{CNPJ}", 429, "Too Many Requests", headers, BytesIO(b'{"message":"slow down"}')
    )
    monkeypatch.setattr("searchleads.sources.brasilapi.urlopen", lambda request, timeout: (_ for _ in ()).throw(error))
    result = http_get(f"{BASE_URL}/{CNPJ}", timeout=1)
    assert result.status_code == 429
    assert result.raw_payload == '{"message":"slow down"}'
    assert result.headers["content-type"].startswith("application/json")


def test_network_error_transport_raises_acquisition_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "searchleads.sources.brasilapi.urlopen",
        lambda request, timeout: (_ for _ in ()).throw(URLError("offline")),
    )
    with pytest.raises(BrasilAPIAcquisitionError):
        http_get(f"{BASE_URL}/{CNPJ}", timeout=1)


def test_http_success_transport_reads_body_and_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    headers = Message()
    headers["Content-Type"] = "application/json; charset=utf-8"

    class Response:
        status = 200

        def __init__(self) -> None:
            self.headers = headers

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return "{\"ok\":\"ç\"}".encode("utf-8")

    monkeypatch.setattr("searchleads.sources.brasilapi.urlopen", lambda request, timeout: Response())
    result = http_get(f"{BASE_URL}/{CNPJ}", timeout=1)
    assert result.status_code == 200
    assert result.raw_payload == '{"ok":"ç"}'
    assert result.headers["content-type"].startswith("application/json")



def test_http_transport_rejects_non_decodable_text(monkeypatch: pytest.MonkeyPatch) -> None:
    headers = Message()
    headers["Content-Type"] = "application/json; charset=utf-8"

    class Response:
        status = 200

        def __init__(self) -> None:
            self.headers = headers

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b"\xff"

    monkeypatch.setattr("searchleads.sources.brasilapi.urlopen", lambda request, timeout: Response())
    with pytest.raises(BrasilAPIAcquisitionError):
        http_get(f"{BASE_URL}/{CNPJ}", timeout=1)


def test_headers_dict_handles_object_without_items() -> None:
    assert _headers_dict(object()) == {}


def test_same_generic_http_error_body_for_different_cnpjs_does_not_collide() -> None:
    generic = "Too Many Requests"

    def transport(url: str) -> HTTPObservation:
        return HTTPObservation(url, 429, generic, NOW)

    adapter = BrasilAPISource(transport)
    with SQLiteRepository() as repo:
        with pytest.raises(BrasilAPIResponseError) as first:
            adapter.ingest("33683111000280", repo)
        with pytest.raises(BrasilAPIResponseError) as second:
            adapter.ingest("00000000000191", repo)
        assert first.value.evidence_id != second.value.evidence_id
        assert repo.load_evidence(first.value.evidence_id).raw_payload == generic
        assert repo.load_evidence(second.value.evidence_id).raw_payload == generic


def test_content_address_collision_guard_rejects_inconsistent_existing_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    obs = observation(raw="same")
    adapter = BrasilAPISource(lambda url: obs)
    with SQLiteRepository() as repo:
        fake = Evidence("fake", SOURCE_ID, "https://wrong.example", NOW, "same")
        monkeypatch.setattr(repo, "load_evidence", lambda evidence_id: fake)
        with pytest.raises(BrasilAPIAcquisitionError):
            adapter.ingest(CNPJ, repo)
