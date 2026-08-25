from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from searchleads.domain import CandidateFact, DecisionClass, Evidence, Provenance, Source
from searchleads.normalization import (
    NormalizationResult,
    NormalizationStatus,
    normalize_candidate_fact,
    normalize_candidate_facts,
    normalize_persisted_candidate,
)
from searchleads.persistence import SQLiteRepository

NOW = datetime(2026, 8, 24, 21, 0, tzinfo=timezone.utc)

def fact(field_name: str, raw_value: object, **changes: object) -> CandidateFact:
    values: dict[str, object] = {
        "fact_id": f"fact-{field_name}",
        "subject_id": "company-1",
        "field_name": field_name,
        "raw_value": raw_value,
        "normalized_value": None,
        "evidence_ids": ("ev-1",),
        "provenance_id": "prov-1",
        "confidence": 0.8,
        "decision_class": DecisionClass.EVIDENCE_BACKED,
        "observed_at": NOW,
    }
    values.update(changes)
    return CandidateFact(**values)

def assert_success(result: NormalizationResult) -> CandidateFact:
    assert result.status in {NormalizationStatus.NORMALIZED, NormalizationStatus.UNCHANGED}
    assert result.normalized_fact is not None
    assert result.normalization_rule is not None
    assert result.reason is None
    return result.normalized_fact

def test_company_name_collapses_whitespace_without_removing_legal_suffix() -> None:
    source = fact("legal_name", "  ACME\tTecnologia   Ltda.  ")
    result = normalize_candidate_fact(source)
    projected = assert_success(result)
    assert result.status is NormalizationStatus.NORMALIZED
    assert projected.raw_value == source.raw_value
    assert projected.normalized_value == "ACME Tecnologia Ltda."
    assert result.normalization_rule == "company_name_nfkc_whitespace_v1"

def test_unicode_compatibility_is_normalized_for_company_name() -> None:
    result = normalize_candidate_fact(fact("trade_name", "ＡＣＭＥ"))
    assert assert_success(result).normalized_value == "ACME"

@pytest.mark.parametrize("field", ["company_name", "legal_name", "trade_name"])
def test_company_name_fields_use_same_conservative_rule(field: str) -> None:
    result = normalize_candidate_fact(fact(field, "Acme S.A."))
    assert result.status is NormalizationStatus.UNCHANGED
    assert result.normalization_rule == "company_name_nfkc_whitespace_v1"
    assert assert_success(result).normalized_value == "Acme S.A."

@pytest.mark.parametrize("value", ["", " \t\n "])
def test_blank_company_name_is_invalid(value: str) -> None:
    result = normalize_candidate_fact(fact("legal_name", value))
    assert result.status is NormalizationStatus.INVALID
    assert result.normalized_fact is None
    assert "blank" in result.reason

def test_non_text_company_name_is_invalid_instead_of_stringified() -> None:
    result = normalize_candidate_fact(fact("legal_name", 123))
    assert result.status is NormalizationStatus.INVALID
    assert result.reason == "company name must be text"

@pytest.mark.parametrize(
    "field",
    ["address", "street_address", "city", "location", "country", "industry", "industry_label", "registration_status", "primary_cnae_description"],
)
def test_generic_text_fields_apply_nfkc_and_whitespace_only(field: str) -> None:
    result = normalize_candidate_fact(fact(field, "  São   Paulo  "))
    assert assert_success(result).normalized_value == "São Paulo"
    assert result.normalization_rule == "text_nfkc_whitespace_v1"

def test_blank_generic_text_is_invalid() -> None:
    result = normalize_candidate_fact(fact("city", "   "))
    assert result.status is NormalizationStatus.INVALID
    assert result.reason == "text value is blank"

def test_non_text_generic_field_is_invalid() -> None:
    result = normalize_candidate_fact(fact("city", 3550308))
    assert result.status is NormalizationStatus.INVALID
    assert result.reason == "text value must be text"

def test_domain_extracts_and_lowercases_host_without_root_domain_collapse() -> None:
    result = normalize_candidate_fact(fact("domain", "HTTPS://WWW.Example.COM/path?q=1"))
    assert assert_success(result).normalized_value == "www.example.com"
    assert result.normalization_rule == "domain_lower_idna_v1"

def test_domain_accepts_scheme_less_host_because_no_scheme_is_invented_in_output() -> None:
    result = normalize_candidate_fact(fact("domain", "WWW.Example.COM."))
    assert assert_success(result).normalized_value == "www.example.com"

def test_domain_uses_idna_without_collapsing_subdomain() -> None:
    result = normalize_candidate_fact(fact("domain", "münich.example"))
    assert assert_success(result).normalized_value == "xn--mnich-kva.example"

def test_domain_normalizes_ipv4_literal() -> None:
    result = normalize_candidate_fact(fact("domain", "192.168.001.001"))
    assert result.status is NormalizationStatus.INVALID

def test_domain_normalizes_valid_ipv6_literal() -> None:
    result = normalize_candidate_fact(fact("domain", "[2001:0db8::1]"))
    assert assert_success(result).normalized_value == "2001:db8::1"

@pytest.mark.parametrize("value", ["", "   ", "http://", "foo..example"])
def test_invalid_domains_are_explicit(value: str) -> None:
    result = normalize_candidate_fact(fact("domain", value))
    assert result.status is NormalizationStatus.INVALID
    assert result.normalized_fact is None
    assert result.normalization_rule is None

def test_domain_rejects_host_that_becomes_blank_after_trailing_dot_cleanup() -> None:
    result = normalize_candidate_fact(fact("domain", "."))
    assert result.status is NormalizationStatus.INVALID
    assert result.reason == "host is blank"

def test_domain_rejects_total_host_length_over_dns_limit() -> None:
    oversized = ".".join(["abcdefghij"] * 24)
    assert len(oversized) > 253
    result = normalize_candidate_fact(fact("domain", oversized))
    assert result.status is NormalizationStatus.INVALID
    assert result.reason == "host is invalid"

def test_domain_rejects_malformed_bracketed_host() -> None:
    result = normalize_candidate_fact(fact("domain", "http://[broken"))
    assert result.status is NormalizationStatus.INVALID
    assert result.reason == "domain is invalid"

@pytest.mark.parametrize("value", ["foo_bar.example", "-foo.example", "foo-.example"])
def test_domain_rejects_non_dns_hostname_labels(value: str) -> None:
    result = normalize_candidate_fact(fact("domain", value))
    assert result.status is NormalizationStatus.INVALID
    assert result.reason == "host is invalid"

def test_non_text_domain_is_invalid() -> None:
    result = normalize_candidate_fact(fact("domain", 123))
    assert result.status is NormalizationStatus.INVALID
    assert result.reason == "domain must be text"

def test_url_lowercases_scheme_host_removes_default_port_and_fragment() -> None:
    result = normalize_candidate_fact(
        fact("website_url", "HTTPS://Example.COM:443/Contact?A=1#team")
    )
    assert assert_success(result).normalized_value == "https://example.com/Contact?A=1"
    assert result.normalization_rule == "url_scheme_host_fragment_v1"

def test_http_default_port_is_removed_but_non_default_port_is_preserved() -> None:
    default = normalize_candidate_fact(fact("website", "http://EXAMPLE.com:80/a"))
    custom = normalize_candidate_fact(fact("website", "http://EXAMPLE.com:8080/a"))
    assert assert_success(default).normalized_value == "http://example.com/a"
    assert assert_success(custom).normalized_value == "http://example.com:8080/a"

def test_url_preserves_path_query_case_and_empty_path() -> None:
    result = normalize_candidate_fact(fact("url", "https://EXAMPLE.com?Q=Case#frag"))
    assert assert_success(result).normalized_value == "https://example.com?Q=Case"

def test_url_idna_host_and_ipv6_literals_are_supported() -> None:
    idna = normalize_candidate_fact(fact("website_url", "https://münich.example/"))
    ipv6 = normalize_candidate_fact(fact("website_url", "https://[2001:0db8::1]:443/a"))
    assert assert_success(idna).normalized_value == "https://xn--mnich-kva.example/"
    assert assert_success(ipv6).normalized_value == "https://[2001:db8::1]/a"

@pytest.mark.parametrize(
    "value",
    [
        "example.com/contact",
        "ftp://example.com/a",
        "https://",
        "https://user:pass@example.com/a",
        "https://example.com:99999/a",
        "https://foo..example/a",
    ],
)
def test_invalid_or_unsafe_urls_are_not_silently_coerced(value: str) -> None:
    result = normalize_candidate_fact(fact("website_url", value))
    assert result.status is NormalizationStatus.INVALID
    assert result.normalized_fact is None

def test_blank_url_is_invalid() -> None:
    result = normalize_candidate_fact(fact("website_url", "   "))
    assert result.status is NormalizationStatus.INVALID
    assert result.reason == "URL is blank"

def test_malformed_bracketed_url_is_invalid() -> None:
    result = normalize_candidate_fact(fact("website_url", "https://[broken"))
    assert result.status is NormalizationStatus.INVALID
    assert result.reason == "URL is invalid"

def test_url_rejects_non_dns_hostname_label() -> None:
    result = normalize_candidate_fact(fact("website_url", "https://foo_bar.example/a"))
    assert result.status is NormalizationStatus.INVALID
    assert result.reason == "host is invalid"

def test_non_text_url_is_invalid() -> None:
    result = normalize_candidate_fact(fact("website_url", 123))
    assert result.status is NormalizationStatus.INVALID
    assert result.reason == "URL must be text"

def test_phone_strips_punctuation_without_inventing_country_code() -> None:
    domestic = normalize_candidate_fact(fact("phone", "(11) 99999-0000"))
    international = normalize_candidate_fact(fact("phone", "+55 (11) 99999-0000"))
    assert assert_success(domestic).normalized_value == "11999990000"
    assert assert_success(international).normalized_value == "+5511999990000"
    assert domestic.normalization_rule == "phone_punctuation_only_v1"

@pytest.mark.parametrize("field", ["phone", "company_phone"])
def test_phone_aliases_share_rule(field: str) -> None:
    result = normalize_candidate_fact(fact(field, "+1 212 555 0100"))
    assert assert_success(result).normalized_value == "+12125550100"

@pytest.mark.parametrize("value", ["", "123-45", 11999990000])
def test_invalid_phone_values_are_explicit(value: object) -> None:
    result = normalize_candidate_fact(fact("phone", value))
    assert result.status is NormalizationStatus.INVALID

def test_state_two_letter_code_is_uppercased() -> None:
    result = normalize_candidate_fact(fact("state", " sp "))
    assert assert_success(result).normalized_value == "SP"
    assert result.normalization_rule == "state_two_letter_upper_v1"

def test_state_full_text_is_not_mapped_to_code() -> None:
    result = normalize_candidate_fact(fact("state", "  São   Paulo "))
    assert assert_success(result).normalized_value == "São Paulo"
    assert result.normalization_rule == "text_nfkc_whitespace_v1"

@pytest.mark.parametrize("value", ["", 35])
def test_invalid_state_values_are_explicit(value: object) -> None:
    result = normalize_candidate_fact(fact("state", value))
    assert result.status is NormalizationStatus.INVALID

@pytest.mark.parametrize("value", [6204000, "6204-0/00", " 6204000 "])
def test_cnae_code_becomes_seven_digit_string(value: object) -> None:
    result = normalize_candidate_fact(fact("primary_cnae_code", value))
    assert assert_success(result).normalized_value == "6204000"
    assert result.normalization_rule == "cnae_digits7_v1"

def test_cnae_alias_uses_same_rule() -> None:
    result = normalize_candidate_fact(fact("cnae_code", "62.04-0-00"))
    assert assert_success(result).normalized_value == "6204000"

@pytest.mark.parametrize("value", [True, None, 620400, "6204-0/0", 6204000.0])
def test_invalid_cnae_values_are_explicit(value: object) -> None:
    result = normalize_candidate_fact(fact("primary_cnae_code", value))
    assert result.status is NormalizationStatus.INVALID

@pytest.mark.parametrize("field", ["linkedin_url", "instagram_url", "social_profile_url"])
def test_social_profile_urls_use_url_rule(field: str) -> None:
    result = normalize_candidate_fact(fact(field, "https://WWW.LinkedIn.com/company/Acme/#about"))
    assert assert_success(result).normalized_value == "https://www.linkedin.com/company/Acme/"
    assert result.normalization_rule == "url_scheme_host_fragment_v1"

def test_unknown_field_is_explicitly_unsupported() -> None:
    source = fact("employee_count", 42)
    result = normalize_candidate_fact(source)
    assert result.status is NormalizationStatus.UNSUPPORTED
    assert result.source_fact is source
    assert result.normalized_fact is None
    assert result.normalization_rule is None
    assert "employee_count" in result.reason

def test_projection_preserves_fact_identity_evidence_provenance_confidence_decision_and_time() -> None:
    source = fact("city", "  São   Paulo ")
    result = normalize_candidate_fact(source)
    projected = assert_success(result)
    assert projected.fact_id == source.fact_id
    assert projected.subject_id == source.subject_id
    assert projected.field_name == source.field_name
    assert projected.raw_value == source.raw_value
    assert projected.evidence_ids == source.evidence_ids
    assert projected.provenance_id == source.provenance_id
    assert projected.confidence == source.confidence
    assert projected.decision_class is source.decision_class
    assert projected.observed_at == source.observed_at
    assert source.normalized_value is None

def test_existing_normalized_value_is_recomputed_from_raw_without_mutating_source() -> None:
    source = fact("city", " São   Paulo ", normalized_value="stale-normalization")
    result = normalize_candidate_fact(source)
    projected = assert_success(result)
    assert projected.normalized_value == "São Paulo"
    assert source.normalized_value == "stale-normalization"

def test_unchanged_status_still_records_rule_and_projection() -> None:
    source = fact("city", "São Paulo")
    result = normalize_candidate_fact(source)
    assert result.status is NormalizationStatus.UNCHANGED
    assert result.normalization_rule == "text_nfkc_whitespace_v1"
    assert assert_success(result).normalized_value == "São Paulo"

def test_batch_normalization_preserves_input_order_and_does_not_fuse() -> None:
    facts = [fact("city", " São  Paulo ", fact_id="f1"), fact("employee_count", 10, fact_id="f2")]
    results = normalize_candidate_facts(facts)
    assert [item.source_fact.fact_id for item in results] == ["f1", "f2"]
    assert results[0].status is NormalizationStatus.NORMALIZED
    assert results[1].status is NormalizationStatus.UNSUPPORTED

def test_normalization_result_rejects_inconsistent_success_shape() -> None:
    with pytest.raises(ValueError):
        NormalizationResult(fact("city", "x"), None, NormalizationStatus.NORMALIZED)
    with pytest.raises(ValueError):
        NormalizationResult(
            fact("city", "x"),
            fact("city", "x", normalized_value="x"),
            NormalizationStatus.UNCHANGED,
            normalization_rule=None,
        )

def test_normalization_result_rejects_projection_on_unsuccessful_status() -> None:
    source = fact("employee_count", 1)
    projected = replace(source, normalized_value=1)
    with pytest.raises(ValueError):
        NormalizationResult(
            source,
            projected,
            NormalizationStatus.UNSUPPORTED,
            normalization_rule="invented-rule",
        )

def test_persisted_raw_candidate_can_be_normalized_after_database_reopen(tmp_path) -> None:
    path = tmp_path / "leads.sqlite3"
    source = Source("src-1", "dataset", "https://example.test/company")
    evidence = Evidence(
        "ev-1",
        source.source_id,
        "https://example.test/company/1",
        NOW,
        '{"municipio":"  São   Paulo "}',
    )
    provenance = Provenance("prov-1", "company-1", "city", ("ev-1",), "extract", NOW)
    candidate = fact("city", "  São   Paulo ")

    with SQLiteRepository(path) as repository:
        repository.save(source)
        repository.save(evidence)
        repository.save(provenance)
        repository.save(candidate)

    with SQLiteRepository(path) as reopened:
        result = normalize_persisted_candidate(reopened, candidate.fact_id)
        persisted = reopened.load(CandidateFact, candidate.fact_id)

    assert result is not None
    assert assert_success(result).normalized_value == "São Paulo"
    assert result.source_fact.raw_value == "  São   Paulo "
    assert persisted == candidate
    assert persisted.normalized_value is None

def test_normalize_persisted_candidate_returns_none_when_fact_is_missing(tmp_path) -> None:
    with SQLiteRepository(tmp_path / "missing.sqlite3") as repository:
        assert normalize_persisted_candidate(repository, "missing") is None

def test_wu3_brasilapi_candidates_feed_normalization_without_fusion() -> None:
    import json

    from searchleads.sources.brasilapi import BASE_URL, BrasilAPISource, HTTPObservation

    cnpj = "33683111000280"
    data = {
        "cnpj": cnpj,
        "razao_social": "  SERVICO   FEDERAL DE PROCESSAMENTO DE DADOS (SERPRO) ",
        "nome_fantasia": "REGIONAL BRASILIA-DF",
        "descricao_situacao_cadastral": " ATIVA ",
        "cnae_fiscal": 6204000,
        "cnae_fiscal_descricao": "Consultoria em tecnologia da informação",
        "municipio": " BRASILIA ",
        "uf": "df",
    }
    observation = HTTPObservation(
        f"{BASE_URL}/{cnpj}",
        200,
        json.dumps(data, ensure_ascii=False),
        NOW,
    )
    adapter = BrasilAPISource(lambda url: observation)

    with SQLiteRepository() as repository:
        ingestion = adapter.ingest(cnpj, repository)
        results = normalize_candidate_facts(ingestion.candidate_facts)

    by_field = {result.source_fact.field_name: result for result in results}
    assert by_field["business_registry_id"].status is NormalizationStatus.UNSUPPORTED
    assert assert_success(by_field["legal_name"]).normalized_value == "SERVICO FEDERAL DE PROCESSAMENTO DE DADOS (SERPRO)"
    assert assert_success(by_field["trade_name"]).normalized_value == "REGIONAL BRASILIA-DF"
    assert assert_success(by_field["registration_status"]).normalized_value == "ATIVA"
    assert assert_success(by_field["primary_cnae_code"]).normalized_value == "6204000"
    assert assert_success(by_field["primary_cnae_description"]).normalized_value == "Consultoria em tecnologia da informação"
    assert assert_success(by_field["city"]).normalized_value == "BRASILIA"
    assert assert_success(by_field["state"]).normalized_value == "DF"
    assert len(results) == len(ingestion.candidate_facts) == 8
