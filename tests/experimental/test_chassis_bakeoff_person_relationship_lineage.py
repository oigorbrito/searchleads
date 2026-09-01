from __future__ import annotations

import pytest

pytest.importorskip("followthemoney")

from followthemoney import Statement, StatementEntity
from followthemoney.dataset import UndefinedDataset

from searchleads.domain import Person


def test_ftm_directorship_statements_preserve_per_property_dataset_and_origin() -> None:
    relation_id = "directorship:ana:clinic-a"
    statements = [
        Statement(
            entity_id=relation_id,
            schema="Directorship",
            prop="director",
            value="person:ana-silva",
            dataset="official-company-site",
            origin="https://clinic-a.example.org/team",
        ),
        Statement(
            entity_id=relation_id,
            schema="Directorship",
            prop="organization",
            value="company:clinic-a",
            dataset="official-company-site",
            origin="https://clinic-a.example.org/team",
        ),
        Statement(
            entity_id=relation_id,
            schema="Directorship",
            prop="role",
            value="Chief Financial Officer",
            dataset="official-company-site",
            origin="https://clinic-a.example.org/team",
        ),
        Statement(
            entity_id=relation_id,
            schema="Directorship",
            prop="role",
            value="Finance Director",
            dataset="professional-registry",
            origin="https://registry.example.org/person/ana-silva",
        ),
    ]
    relation = StatementEntity.from_statements(UndefinedDataset, statements)

    role_statements = relation.get_statements("role")
    assert relation.schema.name == "Directorship"
    assert relation.get("director") == ["person:ana-silva"]
    assert relation.get("organization") == ["company:clinic-a"]
    assert set(relation.get("role")) == {"Chief Financial Officer", "Finance Director"}
    assert {statement.dataset for statement in role_statements} == {
        "official-company-site",
        "professional-registry",
    }
    assert {statement.origin for statement in role_statements} == {
        "https://clinic-a.example.org/team",
        "https://registry.example.org/person/ana-silva",
    }

    print("FTM_RELATIONSHIP_LINEAGE_V1")
    print("relationship_property_dataset_lineage=YES")
    print("relationship_property_origin_lineage=YES")
    print("competing_role_values_preserved=YES")


def test_ftm_lineage_is_available_but_not_a_hard_raw_evidence_envelope_requirement() -> None:
    statement = Statement(
        entity_id="directorship:ana:clinic-a",
        schema="Directorship",
        prop="role",
        value="Chief Financial Officer",
        dataset="dataset-without-origin",
    )
    relation = StatementEntity.from_statements(UndefinedDataset, [statement])

    assert relation.get("role") == ["Chief Financial Officer"]
    assert relation.get_statements("role")[0].origin is None

    print("FTM_RELATIONSHIP_LINEAGE_POLICY_V1")
    print("statement_without_origin_accepted=YES")
    print("raw_evidence_envelope_hard_required=NO")


def test_searchleads_hard_relationship_evidence_policy_is_independent_of_embedded_company_model() -> None:
    # SearchLeads currently enforces evidence by embedding the relationship in
    # Person. The requirement itself can survive even if that representation is
    # replaced by a first-class relationship entity.
    with pytest.raises(ValueError, match="relationship evidence"):
        Person(
            person_id="person:ana-silva",
            company_id="company:clinic-a",
            relationship_evidence_ids=(),
        )

    print("RELATIONSHIP_EVIDENCE_POLICY_SEPARATION_V1")
    print("hard_evidence_requirement_is_policy=YES")
    print("embedding_company_id_in_person_is_required_for_that_policy=NO_CONCEPTUALLY")
    print("candidate=FIRST_CLASS_RELATIONSHIP_PLUS_HARD_EVIDENCE")


def test_composed_relationship_candidate_keeps_the_best_properties_without_declaring_a_winner() -> None:
    candidate_contract = {
        "identity_separate_from_company": "FTM_IDEA",
        "multiple_relationships_per_person": "FTM_IDEA",
        "role_and_temporal_context_on_relationship": "FTM_IDEA",
        "per_property_dataset_origin_lineage": "FTM_IDEA",
        "raw_evidence_required_before_commercial_relationship_acceptance": "SEARCHLEADS_POLICY",
        "raw_payload_preserved_for_reprocessing": "SEARCHLEADS_POLICY",
    }

    assert len(candidate_contract) == 6
    assert sum(value == "FTM_IDEA" for value in candidate_contract.values()) == 4
    assert sum(value == "SEARCHLEADS_POLICY" for value in candidate_contract.values()) == 2

    print("COMPOSED_PERSON_RELATIONSHIP_CANDIDATE_V1")
    for property_name, source in candidate_contract.items():
        print(f"{property_name}={source}")
    print("production_adoption=NOT_AUTHORIZED")
    print("winner=UNDECIDED_PENDING_EXECUTED_TESTS_AND_MIGRATION_COST")
