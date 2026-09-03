from searchleads.company_enrichment.official_location import (
    HTTPEnrichmentObservation,
    OFFICIAL_URL,
    OfficialCompanyLocationSource,
)
from searchleads.live_network_smoke import DEFAULT_CNPJ, run_live_network_certification
from searchleads.sources.brasilapi import BrasilAPISource, HTTPObservation


def _brasil_source() -> BrasilAPISource:
    def transport(url: str) -> HTTPObservation:
        return HTTPObservation(
            url=url,
            status_code=200,
            raw_payload=(
                '{"cnpj":"33683111000280","razao_social":"SERVICO FEDERAL DE PROCESSAMENTO DE DADOS",'
                '"nome_fantasia":"SERPRO","descricao_situacao_cadastral":"ATIVA",'
                '"municipio":"BRASILIA","uf":"DF"}'
            ),
        )

    return BrasilAPISource(transport=transport)


def _official_source() -> OfficialCompanyLocationSource:
    def transport(url: str) -> HTTPEnrichmentObservation:
        assert url == OFFICIAL_URL
        return HTTPEnrichmentObservation(
            url=url,
            status_code=200,
            raw_html="""
                <html><body>
                  <h2>Brasília</h2>
                  <p>SGAN Quadra 601, Módulo V</p>
                  <p>Brasília / DF</p>
                  <p>CEP: 70836-900</p>
                  <p>CNPJ: 33.683.111/0002-80</p>
                  <p>Início das Atividades: 03/11/1970</p>
                </body></html>
            """,
        )

    return OfficialCompanyLocationSource(transport=transport)


def test_certification_composes_existing_adapters_and_persists_raw_evidence():
    result = run_live_network_certification(
        cnpj=DEFAULT_CNPJ,
        brasil_source_factory=_brasil_source,
        official_source_factory=_official_source,
    )

    assert result.passed is True
    assert result.company_id == "company:brasilapi-cnpj:33683111000280"
    assert result.brasilapi.source == "brasilapi_cnpj_v1"
    assert result.brasilapi.http_status == 200
    assert result.brasilapi.persisted_raw_payload is True
    assert "legal_name" in result.brasilapi.candidate_fields
    assert result.serpro_official_location.source == "serpro_official_company_location"
    assert result.serpro_official_location.locator == OFFICIAL_URL
    assert result.serpro_official_location.http_status == 200
    assert result.serpro_official_location.persisted_raw_payload is True
    assert "business_registry_id" in result.serpro_official_location.candidate_fields


def test_default_cnpj_is_the_documented_known_serpro_identifier():
    assert DEFAULT_CNPJ == "33683111000280"
