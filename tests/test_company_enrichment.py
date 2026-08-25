from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace
import urllib.error
from unittest.mock import patch

import pytest

import searchleads.company_enrichment.official_location as mod
from searchleads.company_enrichment import (
    OFFICIAL_URL,
    CompanyEnrichmentAcquisitionError,
    CompanyEnrichmentExtractionError,
    CompanyEnrichmentResponseError,
    HTTPEnrichmentObservation,
    OfficialCompanyLocationSource,
    extract_official_location_facts,
    http_get,
)
from searchleads.domain import Company, ContactStatus, Evidence, Source
from searchleads.entity_resolution import CompanyRecord, ResolutionDisposition, triage_pair
from searchleads.field_fusion import FusionStatus, fuse_candidate_facts
from searchleads.normalization import NormalizationStatus, normalize_candidate_fact
from searchleads.persistence import SQLiteRepository
from searchleads.sources import BrasilAPISource, HTTPObservation

UTC = timezone.utc
NOW = datetime(2026, 8, 25, 18, 0, tzinfo=UTC)
FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "company_enrichment_v1.json").read_text(encoding="utf-8"))
BRASILIA = next(item for item in FIXTURE["valid_cases"] if item["name"] == "brasilia_current")


def _project(fact):
    result = normalize_candidate_fact(fact)
    return result.normalized_fact if result.status in {NormalizationStatus.NORMALIZED, NormalizationStatus.UNCHANGED} else fact


def _company(repo: SQLiteRepository, company_id: str = "company:brasilapi-cnpj:33683111000280") -> Company:
    company = Company(company_id)
    repo.save(company)
    return company


def _obs(html: str, *, status: int = 200, url: str = OFFICIAL_URL, at: datetime = NOW) -> HTTPEnrichmentObservation:
    return HTTPEnrichmentObservation(url, status, html, at, {"content-type": "text/html; charset=utf-8"})


def test_current_calibration_matches_all_12_verified_blocks() -> None:
    calibration = FIXTURE["current_calibration"]
    assert len(calibration["entries"]) == 12
    for entry in calibration["entries"]:
        extracted = extract_official_location_facts(calibration["html"], entry["expected_cnpj"])
        assert asdict(extracted) == entry["expected"]


@pytest.mark.parametrize("case", FIXTURE["valid_cases"], ids=lambda item: item["name"])
def test_curated_valid_extraction_cases(case: dict[str, object]) -> None:
    extracted = extract_official_location_facts(str(case["html"]), str(case["expected_cnpj"]))
    assert asdict(extracted) == case["expected"]


@pytest.mark.parametrize("case", FIXTURE["reject_cases"], ids=lambda item: item["name"])
def test_curated_reject_cases(case: dict[str, object]) -> None:
    with pytest.raises(CompanyEnrichmentExtractionError):
        extract_official_location_facts(str(case["html"]), str(case["expected_cnpj"]))


def test_extractor_rejects_non_text_and_invalid_cnpj() -> None:
    with pytest.raises(TypeError):
        extract_official_location_facts(b"html", "33.683.111/0002-80")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        extract_official_location_facts("<html></html>", "bad")


def test_url_boundary_accepts_only_known_canonical_page() -> None:
    assert mod._normalize_official_url(OFFICIAL_URL + "?utm=ignored#fragment") == OFFICIAL_URL
    explicit_443 = "https://www.transparencia.serpro.gov.br:443/acesso-a-informacao/institucional/enderecos"
    assert mod._normalize_official_url(explicit_443) == OFFICIAL_URL
    for bad in (
        OFFICIAL_URL.replace("https://", "http://"),
        "https://serpro.gov.br/acesso-a-informacao/institucional/enderecos",
        OFFICIAL_URL + "/other",
        "https://user:pass@www.transparencia.serpro.gov.br/acesso-a-informacao/institucional/enderecos",
        "https://www.transparencia.serpro.gov.br:444/acesso-a-informacao/institucional/enderecos",
    ):
        with pytest.raises(ValueError):
            mod._normalize_official_url(bad)
    with pytest.raises(TypeError):
        mod._normalize_official_url(123)  # type: ignore[arg-type]



def test_internal_parser_and_helper_defensive_branches() -> None:
    parser = mod._VisibleBlockParser()
    parser.handle_endtag("script")
    parser.handle_starttag("script", [])
    parser.handle_starttag("style", [])
    parser.handle_starttag("div", [])
    parser.handle_data("hidden")
    parser.handle_endtag("div")
    parser.handle_endtag("style")
    parser.handle_endtag("script")
    parser.handle_data("   ")
    parser.handle_starttag("h3", [])
    parser.handle_data("Title")
    parser.handle_endtag("h3")
    parser.handle_data("Visible")
    parser.close()
    assert parser.blocks[-1].heading == "Title"
    assert parser.blocks[-1].texts == ("Visible",)

    assert mod._parse_location("No slash here") is None
    assert mod._parse_location("/DF") is None
    assert mod._parse_location("Brasília/" + "X" * 41) is None
    assert mod._parse_location("Brasília/DF1") is None
    assert mod._street_address(("Rua Sem Número", "Bloco 2"), 2) is None
    assert mod._decode_body(b"x", object()) == "x"

    no_location = mod._Block("Only", ("CNPJ: 33.683.111/0002-80",))
    extracted = mod._extract_block(no_location, "33683111000280")
    assert extracted.city is None and extracted.street_address is None


def test_invalid_port_syntax_is_rejected() -> None:
    with pytest.raises(ValueError, match="url is invalid"):
        mod._normalize_official_url(
            "https://www.transparencia.serpro.gov.br:bad/acesso-a-informacao/institucional/enderecos"
        )

def test_observation_invariants() -> None:
    with pytest.raises(ValueError):
        HTTPEnrichmentObservation(OFFICIAL_URL, 99, "x", NOW)
    with pytest.raises(TypeError):
        HTTPEnrichmentObservation(OFFICIAL_URL, 200, b"x", NOW)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        HTTPEnrichmentObservation(OFFICIAL_URL, 200, "x", datetime(2026, 8, 25))


class _Headers(dict):
    def __init__(self, *args, charset: str | None = "utf-8", **kwargs):
        super().__init__(*args, **kwargs)
        self.charset = charset

    def get_content_charset(self):
        return self.charset


class _Response:
    def __init__(self, body: bytes, status: int = 200, headers=None):
        self._body = body
        self.status = status
        self.headers = headers if headers is not None else _Headers({"X-Test": "yes"})

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None


def test_http_get_success_and_header_normalization() -> None:
    with patch.object(mod, "urlopen", return_value=_Response("Brasília".encode())):
        observation = http_get(OFFICIAL_URL + "?ignored=1")
    assert observation.url == OFFICIAL_URL
    assert observation.status_code == 200
    assert observation.raw_html == "Brasília"
    assert observation.headers == {"x-test": "yes"}


def test_http_get_http_error_returns_persistable_observation() -> None:
    error = urllib.error.HTTPError(
        OFFICIAL_URL, 503, "down", _Headers({"Content-Type": "text/html"}), BytesIO(b"maintenance")
    )
    with patch.object(mod, "urlopen", side_effect=error):
        observation = http_get(OFFICIAL_URL)
    assert observation.status_code == 503
    assert observation.raw_html == "maintenance"


def test_http_get_network_and_decode_failures_are_acquisition_errors() -> None:
    with patch.object(mod, "urlopen", side_effect=urllib.error.URLError("dns")):
        with pytest.raises(CompanyEnrichmentAcquisitionError):
            http_get(OFFICIAL_URL)
    bad_headers = _Headers(charset="does-not-exist")
    with patch.object(mod, "urlopen", return_value=_Response(b"x", headers=bad_headers)):
        with pytest.raises(CompanyEnrichmentAcquisitionError):
            http_get(OFFICIAL_URL)


def test_headers_helper_handles_non_mapping_header_object() -> None:
    assert mod._headers(object()) == {}


def test_ingest_requires_existing_company_and_matching_transport_url() -> None:
    with SQLiteRepository() as repo:
        source = OfficialCompanyLocationSource(lambda _: _obs(str(BRASILIA["html"])))
        with pytest.raises(ValueError):
            source.ingest("missing", str(BRASILIA["expected_cnpj"]), repo)
        company = _company(repo)
        wrong = SimpleNamespace(
            url=OFFICIAL_URL + "/other", status_code=200, raw_html=str(BRASILIA["html"]),
            captured_at=NOW, headers={}
        )
        with pytest.raises(CompanyEnrichmentAcquisitionError):
            OfficialCompanyLocationSource(lambda _: wrong).ingest(company.company_id, str(BRASILIA["expected_cnpj"]), repo)


def test_non_200_and_extraction_failure_preserve_raw_evidence_first() -> None:
    for observation, expected_error in (
        (_obs("maintenance", status=503), CompanyEnrichmentResponseError),
        (_obs("<html><body><h3>Other</h3><p>CNPJ: 33.683.111/0005-22</p></body></html>"), CompanyEnrichmentExtractionError),
    ):
        with SQLiteRepository() as repo:
            company = _company(repo)
            with pytest.raises(expected_error):
                OfficialCompanyLocationSource(lambda _: observation).ingest(
                    company.company_id, "33.683.111/0002-80", repo
                )
            evidence = tuple(repo.iter_evidence())
            assert len(evidence) == 1
            assert evidence[0].raw_payload == observation.raw_html


def test_ingest_persists_provenance_facts_and_is_idempotent() -> None:
    with SQLiteRepository() as repo:
        company = _company(repo)
        adapter = OfficialCompanyLocationSource(lambda _: _obs(str(BRASILIA["html"])))
        first = adapter.ingest(company.company_id, str(BRASILIA["expected_cnpj"]), repo)
        second = adapter.ingest(company.company_id, str(BRASILIA["expected_cnpj"]), repo)
        assert first.evidence_was_new is True
        assert second.evidence_was_new is False
        assert first.evidence == second.evidence
        assert len(first.candidate_facts) == 6
        assert len(first.provenances) == 6
        assert {f.field_name for f in first.candidate_facts} == {
            "business_registry_id", "street_address", "city", "state", "postal_code", "activity_start_date"
        }
        registry = next(f for f in first.candidate_facts if f.field_name == "business_registry_id")
        assert registry.raw_value == "33.683.111/0002-80"
        assert registry.normalized_value == "33683111000280"
        assert repo.raw_evidence_bytes(first.evidence.evidence_id) == str(BRASILIA["html"]).encode()
        assert all(repo.load(type(p), p.provenance_id) == p for p in first.provenances)
        assert all(repo.load(type(f), f.fact_id) == f for f in first.candidate_facts)


def test_content_address_collision_is_rejected() -> None:
    source = OfficialCompanyLocationSource.source_record()
    observation = _obs(str(BRASILIA["html"]))
    digest = mod.hashlib.sha256(f"{OFFICIAL_URL}\0{observation.status_code}\0{observation.raw_html}".encode()).hexdigest()
    bad = Evidence(
        f"evidence:official-company-location:{digest}", source.source_id, OFFICIAL_URL, NOW,
        "different", "sha256:bad", {"http_status": 200}
    )
    fake = SimpleNamespace(load=lambda *_: bad, save=lambda *_: True)
    with pytest.raises(CompanyEnrichmentAcquisitionError):
        mod.OfficialCompanyLocationSource._persist_observation(source, observation, fake)


def test_multisource_integration_measures_agreement_and_conflict() -> None:
    payload = {
        "cnpj": "33683111000280",
        "razao_social": "SERVICO FEDERAL DE PROCESSAMENTO DE DADOS (SERPRO)",
        "nome_fantasia": "SERPRO REGIONAL BRASILIA",
        "descricao_situacao_cadastral": "ATIVA",
        "cnae_fiscal": 6204000,
        "cnae_fiscal_descricao": "Consultoria em tecnologia da informação",
        "municipio": "BRASILIA",
        "uf": "DF",
    }
    api_body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    api_transport = lambda url: HTTPObservation(url, 200, api_body, NOW, {"content-type": "application/json"})
    with SQLiteRepository() as repo:
        api = BrasilAPISource(api_transport).ingest("33.683.111/0002-80", repo)
        official = OfficialCompanyLocationSource(lambda _: _obs(str(BRASILIA["html"]), at=NOW)).ingest(
            api.company.company_id, "33.683.111/0002-80", repo
        )
        assert api.source.source_id != official.source.source_id
        assert api.evidence.source_id != official.evidence.source_id

        api_by_field = {fact.field_name: _project(fact) for fact in api.candidate_facts}
        official_by_field = {fact.field_name: _project(fact) for fact in official.candidate_facts}
        overlap = sorted(set(api_by_field) & set(official_by_field))
        assert overlap == ["business_registry_id", "city", "state"]

        registry = fuse_candidate_facts((api_by_field["business_registry_id"], official_by_field["business_registry_id"]))
        city = fuse_candidate_facts((api_by_field["city"], official_by_field["city"]))
        state = fuse_candidate_facts((api_by_field["state"], official_by_field["state"]))
        assert registry.status is FusionStatus.CANONICAL
        assert registry.canonical_fact is not None and registry.canonical_fact.value == "33683111000280"
        assert city.status is FusionStatus.CONFLICT
        assert state.status is FusionStatus.CONFLICT
        assert {fact.field_name for fact in official.candidate_facts} - set(api_by_field) == {
            "street_address", "postal_code", "activity_start_date"
        }

        er = triage_pair(
            CompanyRecord("api", registry_namespace="br:cnpj", registry_id="33683111000280"),
            CompanyRecord("official", registry_namespace="br:cnpj", registry_id="33.683.111/0002-80"),
        )
        assert er.disposition is ResolutionDisposition.AUTO_MATCH


def test_extract_field_values_omit_missing_optionals() -> None:
    case = next(item for item in FIXTURE["valid_cases"] if item["name"] == "optional_fields_absent")
    extracted = extract_official_location_facts(str(case["html"]), str(case["expected_cnpj"]))
    assert extracted.as_field_values() == (
        ("business_registry_id", "33.683.111/0008-75", "33683111000875"),
        ("city", "Rio de Janeiro", None),
        ("state", "RJ", None),
    )
