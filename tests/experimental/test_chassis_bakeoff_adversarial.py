from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("followthemoney")
pytest.importorskip("nomenklatura")

from followthemoney import EntityProxy
from nomenklatura.matching.logic_v2.model import LogicV2

from searchleads.entity_resolution import CompanyRecord, Strategy, resolve_pair


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "company_er_v1.json"


def _record(record_id: str, raw: dict[str, object]) -> CompanyRecord:
    values = dict(raw)
    if values.get("registry_id") is not None:
        values["registry_namespace"] = "br:cnpj"
    return CompanyRecord(record_id=record_id, **values)


def _website(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    return value if value.startswith(("http://", "https://")) else f"https://{value}"


def _ftm(record: CompanyRecord) -> EntityProxy:
    props: dict[str, list[str]] = {"name": [record.name or record.record_id]}
    if record.registry_id:
        props["registrationNumber"] = [record.registry_id]
    if website := _website(record.domain):
        props["website"] = [website]
    if record.phone:
        props["phone"] = [record.phone]
    address_parts = [record.address, record.city, record.state]
    address = ", ".join(str(value) for value in address_parts if value)
    if address:
        props["address"] = [address]
    return EntityProxy.from_dict(
        {"id": record.record_id, "schema": "Company", "properties": props},
        cleaned=False,
    )


def _cases() -> list[tuple[str, bool, str, CompanyRecord, CompanyRecord]]:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return [
        (
            item["id"],
            item["label"],
            item["category"],
            _record(f"{item['id']}:left", item["left"]),
            _record(f"{item['id']}:right", item["right"]),
        )
        for item in raw
    ]


def test_registry_conflict_is_a_first_class_contradiction() -> None:
    model = LogicV2()
    config = model.default_config()
    conflict_cases = [case for case in _cases() if case[2] == "registry_conflict"]
    assert conflict_cases

    print("ADVERSARIAL_REGISTRY_CONFLICT_V1")
    for pair_id, label, category, left, right in conflict_cases:
        assert label is False
        baseline = resolve_pair(left, right, strategy=Strategy.WEIGHTED, threshold=0.78)
        external = model.compare(_ftm(left), _ftm(right), config)
        print(
            f"{pair_id} category={category} searchleads_match={baseline.is_match} "
            f"searchleads_reasons={baseline.reasons} nomenklatura_score={float(external.score):.4f}"
        )
        # Current SearchLeads treats conflicting CNPJ as a veto. The external score
        # is intentionally not constrained: this probe determines whether its more
        # generic identifier semantics would require a Brazil-specific qualifier.
        assert baseline.is_match is False
        assert "registry_conflict" in baseline.reasons


def test_domain_phone_and_address_evidence_patterns_are_compared_not_assumed() -> None:
    model = LogicV2()
    config = model.default_config()
    selected_categories = {
        "domain_name",
        "domain_phone",
        "phone_name",
        "phone_address",
        "shared_domain",
        "shared_domain_similar_name",
        "shared_phone",
        "shared_phone_address_unit",
        "shared_address",
        "same_address_cnae",
    }
    cases = [case for case in _cases() if case[2] in selected_categories]
    assert cases

    print("ADVERSARIAL_EVIDENCE_PATTERNS_V1")
    for pair_id, label, category, left, right in cases:
        baseline = resolve_pair(left, right, strategy=Strategy.WEIGHTED, threshold=0.78)
        external = model.compare(_ftm(left), _ftm(right), config)
        print(
            f"{pair_id} truth={int(label)} category={category} "
            f"searchleads_score={baseline.score:.4f} searchleads_match={int(baseline.is_match)} "
            f"nomenklatura_score={float(external.score):.4f} "
            f"domain_left={left.domain or '-'} domain_right={right.domain or '-'} "
            f"phone_left={left.phone or '-'} phone_right={right.phone or '-'}"
        )

    # No winner is encoded. These rows specifically expose whether domain/phone
    # signals, which are explicit in SearchLeads but not principal LogicV2 features,
    # improve or damage decisions on this corpus.
    assert len(cases) >= 8
