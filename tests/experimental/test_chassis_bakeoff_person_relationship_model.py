from __future__ import annotations

import pytest

pytest.importorskip("followthemoney")

from followthemoney import Dataset, StatementEntity

from searchleads.domain import Company, Evidence, Person, Source
from searchleads.persistence.sqlite import PersistenceConflictError, SQLiteRepository


def _dataset() -> Dataset:
    return Dataset.make({"name": "searchleads_relationship_bakeoff", "title": "SearchLeads relationship bake-off"})


def test_ftm_directorship_separates_person_identity_from_company_relationship() -> None:
    dataset = _dataset()
    person = StatementEntity.from_data(
        dataset,
        {
            "id": "person:ana-silva",
            "schema": "Person",
            "properties": {"name": ["Ana Silva"]},
        },
    )
    company = StatementEntity.from_data(
        dataset,
        {
            "id": "company:clinic-a",
            "schema": "Company",
            "properties": {"name": ["Clinica A Ltda"]},
        },
    )
    relationship = StatementEntity.from_data(
        dataset,
        {
            "id": "directorship:ana:clinic-a",
            "schema": "Directorship",
            "properties": {
                "director": ["person:ana-silva"],
                "organization": ["company:clinic-a"],
                "role": ["Chief Financial Officer"],
                "startDate": ["2025-01-01"],
                "sourceUrl": ["https://clinic-a.example.org/team"],
            },
        },
    )

    assert person.schema.name == "Person"
    assert company.schema.name == "Company"
    assert relationship.schema.name == "Directorship"
    assert relationship.get("director") == ["person:ana-silva"]
    assert relationship.get("organization") == ["company:clinic-a"]
    assert relationship.get("role") == ["Chief Financial Officer"]
    assert relationship.get("startDate") == ["2025-01-01"]
    assert relationship.get("sourceUrl") == ["https://clinic-a.example.org/team"]

    print("PERSON_RELATIONSHIP_MODEL_FTM_V1")
    print("person_identity_independent_of_company=YES")
    print("relationship_is_first_class_entity=YES")
    print("relationship_role_native=YES")
    print("relationship_temporal_bounds_native=YES")
    print("relationship_source_url_native=YES")


def test_ftm_one_person_identity_can_hold_multiple_company_roles_without_duplication() -> None:
    dataset = _dataset()
    person = StatementEntity.from_data(
        dataset,
        {
            "id": "person:ana-silva",
            "schema": "Person",
            "properties": {"name": ["Ana Silva"]},
        },
    )
    first = StatementEntity.from_data(
        dataset,
        {
            "id": "directorship:ana:clinic-a",
            "schema": "Directorship",
            "properties": {
                "director": ["person:ana-silva"],
                "organization": ["company:clinic-a"],
                "role": ["CFO"],
                "startDate": ["2025-01-01"],
            },
        },
    )
    second = StatementEntity.from_data(
        dataset,
        {
            "id": "directorship:ana:clinic-b",
            "schema": "Directorship",
            "properties": {
                "director": ["person:ana-silva"],
                "organization": ["company:clinic-b"],
                "role": ["Board Director"],
                "startDate": ["2026-02-01"],
            },
        },
    )

    assert person.id == "person:ana-silva"
    assert first.get("director") == [person.id]
    assert second.get("director") == [person.id]
    assert first.get("organization") != second.get("organization")
    assert first.id != second.id

    print("PERSON_MULTI_ORGANIZATION_FTM_V1")
    print("person_entities=1")
    print("relationship_entities=2")
    print("companies=2")
    print("same_person_id_reused_without_mutating_person=YES")


def test_searchleads_current_persistence_couples_person_id_to_one_company_relationship() -> None:
    source = Source(
        source_id="source:relationship-bakeoff",
        source_type="official_web",
        locator="https://example.org/",
    )
    evidence_a = Evidence(
        evidence_id="evidence:relationship:a",
        source_id=source.source_id,
        locator="https://example.org/company-a/team",
        raw_payload="Ana Silva - CFO - Company A",
    )
    evidence_b = Evidence(
        evidence_id="evidence:relationship:b",
        source_id=source.source_id,
        locator="https://example.org/company-b/board",
        raw_payload="Ana Silva - Board Director - Company B",
    )
    company_a = Company(company_id="company:a")
    company_b = Company(company_id="company:b")
    person_at_a = Person(
        person_id="person:ana-silva",
        company_id=company_a.company_id,
        relationship_evidence_ids=(evidence_a.evidence_id,),
    )
    person_at_b = Person(
        person_id="person:ana-silva",
        company_id=company_b.company_id,
        relationship_evidence_ids=(evidence_b.evidence_id,),
    )

    with SQLiteRepository() as repository:
        assert repository.save(source) is True
        assert repository.save(evidence_a) is True
        assert repository.save(evidence_b) is True
        assert repository.save(company_a) is True
        assert repository.save(company_b) is True
        assert repository.save(person_at_a) is True
        with pytest.raises(PersistenceConflictError, match="already exists with different content"):
            repository.save(person_at_b)

    print("PERSON_MULTI_ORGANIZATION_SEARCHLEADS_V1")
    print("same_person_id_first_company_persisted=YES")
    print("same_person_id_second_company_persistence_conflict=YES")
    print("cause=company_relationship_embedded_in_person_record")


def test_person_relationship_concept_scorecard_does_not_protect_searchleads_model() -> None:
    capabilities = {
        "person_identity_independent_of_company_context": {
            "searchleads_current": "NO_EMBEDDED_COMPANY_ID",
            "ftm_4_10_2": "YES_RELATION_ENTITY",
        },
        "one_person_multiple_organizations": {
            "searchleads_current": "PERSISTENCE_CONFLICT_SAME_PERSON_ID",
            "ftm_4_10_2": "NATIVE_MULTIPLE_RELATIONS",
        },
        "role_on_relationship": {
            "searchleads_current": "SEPARATE_CANDIDATE_FACT_POLICY",
            "ftm_4_10_2": "NATIVE_RELATION_PROPERTY",
        },
        "relationship_start_end_dates": {
            "searchleads_current": "NOT_NATIVE_ON_PERSON_RELATIONSHIP",
            "ftm_4_10_2": "NATIVE_INTERVAL_PROPERTIES",
        },
        "relationship_evidence_requirement": {
            "searchleads_current": "ENFORCED_AT_PERSON_CONSTRUCTION",
            "ftm_4_10_2": "LINEAGE_AVAILABLE_BUT_NOT_HARD_REQUIRED_BY_SCHEMA",
        },
    }

    print("PERSON_RELATIONSHIP_CONCEPT_SCORECARD_V1")
    for capability, values in capabilities.items():
        print(
            f"{capability} searchleads={values['searchleads_current']} "
            f"ftm={values['ftm_4_10_2']}"
        )
    print("winner=UNDECIDED_PENDING_EXECUTION_AND_LINEAGE_POLICY_TEST")
    print("searchleads_person_model_is_not_protected=YES")

    assert len(capabilities) == 5
