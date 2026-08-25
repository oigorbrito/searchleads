from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from searchleads.company_enrichment import HTTPEnrichmentObservation, OFFICIAL_URL, OfficialCompanyLocationSource, extract_official_location_facts
from searchleads.entity_resolution import CompanyRecord, triage_pair
from searchleads.field_fusion import fuse_candidate_facts
from searchleads.normalization import NormalizationStatus, normalize_candidate_fact
from searchleads.persistence import SQLiteRepository
from searchleads.sources import BrasilAPISource, HTTPObservation

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "tests" / "fixtures" / "company_enrichment_v1.json").read_text(encoding="utf-8"))
NOW = datetime(2026, 8, 25, 18, 0, tzinfo=timezone.utc)


def project(fact):
    result = normalize_candidate_fact(fact)
    return result.normalized_fact if result.status in {NormalizationStatus.NORMALIZED, NormalizationStatus.UNCHANGED} else fact


def main() -> None:
    current = DATA["current_calibration"]
    current_exact = sum(
        asdict(extract_official_location_facts(current["html"], entry["expected_cnpj"])) == entry["expected"]
        for entry in current["entries"]
    )
    valid_exact = sum(
        asdict(extract_official_location_facts(case["html"], case["expected_cnpj"])) == case["expected"]
        for case in DATA["valid_cases"]
    )
    rejected = 0
    for case in DATA["reject_cases"]:
        try:
            extract_official_location_facts(case["html"], case["expected_cnpj"])
        except Exception:
            rejected += 1

    brasilia = next(case for case in DATA["valid_cases"] if case["name"] == "brasilia_current")
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
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    with SQLiteRepository() as repo:
        api = BrasilAPISource(lambda url: HTTPObservation(url, 200, body, NOW, {})).ingest("33683111000280", repo)
        official = OfficialCompanyLocationSource(
            lambda url: HTTPEnrichmentObservation(url, 200, brasilia["html"], NOW, {})
        ).ingest(api.company.company_id, "33683111000280", repo)
        api_fields = {f.field_name: project(f) for f in api.candidate_facts}
        official_fields = {f.field_name: project(f) for f in official.candidate_facts}
        overlap = sorted(set(api_fields) & set(official_fields))
        statuses = {
            field: fuse_candidate_facts((api_fields[field], official_fields[field])).status.value
            for field in overlap
        }
        agreement = sum(value == "CANONICAL" for value in statuses.values())
        conflicts = sum(value == "CONFLICT" for value in statuses.values())
        enrichment_only = sorted(set(official_fields) - set(api_fields))
        er = triage_pair(
            CompanyRecord("api", registry_namespace="br:cnpj", registry_id="33683111000280"),
            CompanyRecord("official", registry_namespace="br:cnpj", registry_id="33.683.111/0002-80"),
        )

    print(f"current_calibration={current_exact}/{len(current['entries'])}")
    print(f"curated_valid_exact={valid_exact}/{len(DATA['valid_cases'])}")
    print(f"curated_reject_exact={rejected}/{len(DATA['reject_cases'])}")
    print(f"source_count=2")
    print(f"overlap_fields={len(overlap)} fields={','.join(overlap)}")
    print(f"canonical_agreements={agreement}")
    print(f"explicit_conflicts={conflicts}")
    print(f"enrichment_only_fields={len(enrichment_only)} fields={','.join(enrichment_only)}")
    print(f"company_er={er.disposition.value}")
    print(f"official_url={OFFICIAL_URL}")


if __name__ == "__main__":
    main()
