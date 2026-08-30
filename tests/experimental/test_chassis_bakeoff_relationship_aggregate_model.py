from __future__ import annotations

import pytest

pytest.importorskip("followthemoney")

from followthemoney import Dataset, StatementEntity

from searchleads.domain import Company, Evidence, Person, Source
from searchleads.persistence.sqlite import PersistenceConflictError, SQLiteRepository


def test_searchleads_company_person_ids_can_become_stale_under_immutable_persistence() -> None:
    source = Source(
        source_id="source:aggregate-bakeoff",
        source_type="official_web",
        locator="https://clinic-a.example.org/",
    )
    evidence = Evidence(
        evidence_id="evidence:aggregate-bakeoff",
        source_id=source.source_id,
        locator="https://clinic-a.example.org/team",
        raw_payload="Ana Silva - CFO",
    )
    initial_company = Company(company_id="company:clinic-a")
    person = Person(
        person_id="person:ana-silva",
        company_id=initial_company.company_id,
        relationship_evidence_ids=(evidence.evidence_id,),
    )
    company_with_person_snapshot = Company(
        company_id=initial_company.company_id,
        person_ids=(person.person_id,),
    )

    with SQLiteRepository() as repository:
        assert repository.save(source) is True
        assert repository.save(evidence) is True
        assert repository.save(initial_company) is True
        assert repository.save(person) is True

        loaded_company = repository.load(Company, initial_company.company_id)
        assert loaded_company is not None
        assert loaded_company.person_ids == ()

        with pytest.raises(PersistenceConflictError, match="already exists with different content"):
            repository.save(company_with_person_snapshot)

    print("SEARCHLEADS_COMPANY_PERSON_AGGREGATE_V1")
    print("company_saved_before_person=YES")
    print("person_can_be_added_later=YES")
    print("stored_company_person_ids_auto_updates=NO")
    print("same_company_id_snapshot_refresh=IMMUTABLE_CONFLICT")


def test_ftm_relationship_does_not_require_mutating_company_to_add_a_person_link() -> None:
    dataset = Dataset.make({"name": "aggregate_bakeoff", "title": "Aggregate bake-off"})
    company = StatementEntity.from_data(
        dataset,
        {
            "id": "company:clinic-a",
            "schema": "Company",
            "properties": {"name": ["Clinica A Ltda"]},
        },
    )
    before = company.to_dict()

    person = StatementEntity.from_data(
        dataset,
        {
            "id": "person:ana-silva",
            "schema": "Person",
            "properties": {"name": ["Ana Silva"]},
        },
    )
    relation = StatementEntity.from_data(
        dataset,
        {
            "id": "directorship:ana:clinic-a",
            "schema": "Directorship",
            "properties": {
                "director": [person.id],
                "organization": [company.id],
                "role": ["CFO"],
            },
        },
    )

    after = company.to_dict()
    assert before == after
    assert relation.get("director") == [person.id]
    assert relation.get("organization") == [company.id]

    print("FTM_RELATIONSHIP_AGGREGATE_V1")
    print("company_mutation_required_to_add_director=NO")
    print("relationship_entity_added_separately=YES")
    print("person_identity_mutation_required=NO")


def test_relationship_entity_candidate_reduces_bidirectional_snapshot_obligation() -> None:
    comparison = {
        "searchleads_current": {
            "company_contains_person_ids_snapshot": True,
            "person_contains_company_id": True,
            "relationship_record_is_separate": False,
        },
        "ftm_relation_model": {
            "company_contains_person_ids_snapshot": False,
            "person_contains_company_id": False,
            "relationship_record_is_separate": True,
        },
    }

    assert comparison["searchleads_current"]["company_contains_person_ids_snapshot"] is True
    assert comparison["searchleads_current"]["person_contains_company_id"] is True
    assert comparison["ftm_relation_model"]["relationship_record_is_separate"] is True

    print("RELATIONSHIP_REFERENCE_MODEL_V1")
    print("searchleads_bidirectional_embedded_references=YES")
    print("ftm_first_class_relation=YES")
    print("candidate_benefit=LESS_AGGREGATE_SNAPSHOT_SYNCHRONIZATION")
    print("production_decision=UNDECIDED_PENDING_EXECUTION_AND_MIGRATION_COST")
