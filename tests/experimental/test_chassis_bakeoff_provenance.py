from __future__ import annotations

from datetime import datetime, timezone

import pytest

pytest.importorskip("followthemoney")

from followthemoney import Dataset, Statement, StatementEntity
from followthemoney.dataset import UndefinedDataset

from searchleads.domain.facts import CandidateFact, Conflict
from searchleads.domain.provenance import Evidence, Provenance


def test_ftm_statement_roundtrip_preserves_normalized_original_and_source_metadata() -> None:
    statement = Statement(
        entity_id="company:a",
        schema="Company",
        prop="name",
        value="Clinica Sao Jose Ltda",
        original_value="CLÍNICA SÃO JOSÉ LTDA.",
        dataset="brasilapi",
        origin="https://example.test/cnpj/1",
        first_seen="2026-08-30T12:00:00+00:00",
    )

    restored = Statement.from_dict(statement.to_dict())

    assert restored.value == "Clinica Sao Jose Ltda"
    assert restored.original_value == "CLÍNICA SÃO JOSÉ LTDA."
    assert restored.dataset == "brasilapi"
    assert restored.origin == "https://example.test/cnpj/1"
    assert restored.first_seen == "2026-08-30T12:00:00+00:00"
    assert restored.last_seen == "2026-08-30T12:00:00+00:00"


def test_ftm_statement_key_collapses_same_fact_from_two_origins_inside_one_dataset() -> None:
    first = Statement(
        entity_id="company:a",
        schema="Company",
        prop="name",
        value="Clinica A",
        dataset="official-web",
        origin="https://clinic.example/about",
    )
    second = Statement(
        entity_id="company:a",
        schema="Company",
        prop="name",
        value="Clinica A",
        dataset="official-web",
        origin="https://clinic.example/contact",
    )

    assert first.id == second.id
    entity = StatementEntity.from_statements(UndefinedDataset, [first, second])
    stored = entity.get_statements("name")

    # Statement identity excludes `origin`. This is efficient deduplication, but it
    # means two independent observations of the same value in one dataset collapse
    # to one statement unless the integration introduces stronger source identity.
    assert len(stored) == 1
    assert {item.origin for item in stored}.issubset(
        {"https://clinic.example/about", "https://clinic.example/contact"}
    )
    print("FTM_SAME_DATASET_MULTI_ORIGIN_COLLAPSE=true")
    print(f"statement_id={first.id}")


def test_ftm_preserves_same_value_as_independent_statements_when_dataset_differs() -> None:
    first = Statement(
        entity_id="company:a",
        schema="Company",
        prop="name",
        value="Clinica A",
        dataset="brasilapi",
        origin="https://brasilapi.example/cnpj/1",
    )
    second = Statement(
        entity_id="company:a",
        schema="Company",
        prop="name",
        value="Clinica A",
        dataset="official-site",
        origin="https://clinic.example/",
    )

    entity = StatementEntity.from_statements(UndefinedDataset, [first, second])
    stored = entity.get_statements("name")

    assert first.id != second.id
    assert len(stored) == 2
    assert {item.dataset for item in stored} == {"brasilapi", "official-site"}


def test_searchleads_can_attach_multiple_independent_evidence_envelopes_to_one_fact() -> None:
    captured = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
    evidence_a = Evidence(
        evidence_id="evidence:a",
        source_id="source:web",
        locator="https://clinic.example/about",
        captured_at=captured,
        raw_payload="<html>Clinica A</html>",
        content_digest="digest-a",
    )
    evidence_b = Evidence(
        evidence_id="evidence:b",
        source_id="source:web",
        locator="https://clinic.example/contact",
        captured_at=captured,
        raw_payload="<html>Clinica A</html>",
        content_digest="digest-b",
    )
    provenance = Provenance(
        provenance_id="prov:name",
        subject_id="company:a",
        field_name="name",
        evidence_ids=(evidence_a.evidence_id, evidence_b.evidence_id),
        activity="extract_company_name",
        generated_at=captured,
    )
    fact = CandidateFact(
        fact_id="fact:name",
        subject_id="company:a",
        field_name="name",
        raw_value="CLINICA A",
        normalized_value="clinica a",
        evidence_ids=(evidence_a.evidence_id, evidence_b.evidence_id),
        provenance_id=provenance.provenance_id,
        observed_at=captured,
    )

    assert len(fact.evidence_ids) == 2
    assert evidence_a.locator != evidence_b.locator
    assert evidence_a.raw_payload is not None
    assert evidence_b.raw_payload is not None


def test_ftm_keeps_competing_values_but_searchleads_models_conflict_decision_explicitly() -> None:
    dataset = Dataset.make({"name": "bakeoff", "title": "Bake-off"})
    entity = StatementEntity.from_data(
        dataset,
        {
            "id": "company:a",
            "schema": "Company",
            "properties": {"name": ["Clinica A", "Clinica A Odontologia"]},
        },
    )
    assert set(entity.get("name")) == {"Clinica A", "Clinica A Odontologia"}

    conflict = Conflict(
        conflict_id="conflict:name",
        subject_id="company:a",
        field_name="name",
        candidate_fact_ids=("fact:name:a", "fact:name:b"),
    )
    assert conflict.selected_fact_id is None
    assert len(conflict.candidate_fact_ids) == 2

    print("FTM_COMPETING_VALUES=NATIVE")
    print("FTM_EXPLICIT_CONFLICT_DECISION_STATE=NOT_NATIVE_IN_STATEMENT_ENTITY_PROBE")
    print("SEARCHLEADS_EXPLICIT_CONFLICT_STATE=NATIVE")


def test_provenance_scorecard_distinguishes_native_semantics_from_extensions() -> None:
    scorecard = {
        "normalized_value": "FTM_NATIVE",
        "original_value": "FTM_NATIVE",
        "dataset_per_statement": "FTM_NATIVE",
        "origin_per_statement": "FTM_NATIVE",
        "first_last_seen_per_statement": "FTM_NATIVE",
        "competing_values": "FTM_NATIVE",
        "raw_payload_envelope": "SEARCHLEADS_EXTENSION",
        "content_digest_envelope": "SEARCHLEADS_EXTENSION",
        "multiple_same_dataset_origins_for_identical_value": "SEARCHLEADS_STRONGER_AS_MODELED",
        "explicit_conflict_status_and_rationale": "SEARCHLEADS_EXTENSION",
    }

    print("PROVENANCE_CHASSIS_SCORECARD_V1")
    for capability, classification in scorecard.items():
        print(f"{capability}={classification}")

    assert sum(value == "FTM_NATIVE" for value in scorecard.values()) == 6
    assert sum(value.startswith("SEARCHLEADS") for value in scorecard.values()) == 4
