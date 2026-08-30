from __future__ import annotations

import pytest

pytest.importorskip("followthemoney")
pytest.importorskip("nomenklatura")

from followthemoney import Dataset, Statement, StatementEntity
from followthemoney.dataset import UndefinedDataset
from nomenklatura import settings
from nomenklatura.db import close_db, make_session
from nomenklatura.judgement import Judgement
from nomenklatura.resolver import Resolver

from searchleads.domain.entities import ContactPoint, Person
from searchleads.domain.enums import ContactKind
from searchleads.domain.facts import CandidateFact


@pytest.fixture()
def resolver():
    previous_testing = settings.TESTING
    previous_db_url = settings.DB_URL
    settings.TESTING = True
    settings.DB_URL = "sqlite:///:memory:"
    session = make_session()
    instance = Resolver(session, create=True)
    try:
        yield instance
    finally:
        session.close()
        close_db()
        settings.TESTING = previous_testing
        settings.DB_URL = previous_db_url


def test_ftm_natively_models_company_and_person_identity_fields() -> None:
    dataset = Dataset.make({"name": "searchleads_bakeoff", "title": "SearchLeads bake-off"})
    company = StatementEntity.from_data(
        dataset,
        {
            "id": "company:clinic-a",
            "schema": "Company",
            "properties": {
                "name": ["Clinica Facial A Ltda"],
                "registrationNumber": ["12345678000190"],
                "jurisdiction": ["br"],
            },
        },
    )
    person = StatementEntity.from_data(
        dataset,
        {
            "id": "person:ana-silva",
            "schema": "Person",
            "properties": {
                "name": ["Ana Silva"],
                "email": ["ana@example.org"],
            },
        },
    )

    assert company.schema.name == "Company"
    assert company.get("name") == ["Clinica Facial A Ltda"]
    assert company.get("registrationNumber") == ["12345678000190"]
    assert company.get("jurisdiction") == ["br"]
    assert person.schema.name == "Person"
    assert person.get("name") == ["Ana Silva"]
    assert person.get("email") == ["ana@example.org"]


def test_ftm_statement_layer_preserves_per_fact_dataset_and_origin() -> None:
    statements = [
        Statement(
            entity_id="company:clinic-a",
            schema="Company",
            prop="name",
            value="Clinica Facial A Ltda",
            dataset="brasilapi",
            origin="https://brasilapi.com.br/api/cnpj/v1/12345678000190",
        ),
        Statement(
            entity_id="company:clinic-a",
            schema="Company",
            prop="name",
            value="Clinica Facial A",
            dataset="official-site",
            origin="https://clinic-a.example.org/",
        ),
    ]
    entity = StatementEntity.from_statements(UndefinedDataset, statements)
    name_statements = entity.get_statements("name")

    assert {statement.dataset for statement in name_statements} == {
        "brasilapi",
        "official-site",
    }
    assert {statement.origin for statement in name_statements} == {
        "https://brasilapi.com.br/api/cnpj/v1/12345678000190",
        "https://clinic-a.example.org/",
    }
    assert entity.get("name") == ["Clinica Facial A Ltda", "Clinica Facial A"]


def test_searchleads_person_relationship_evidence_is_stricter_than_ftm_person() -> None:
    dataset = Dataset.make({"name": "searchleads_bakeoff", "title": "SearchLeads bake-off"})

    # FollowTheMoney accepts a standalone Person. That is useful generically, but it
    # does not natively enforce SearchLeads' B2B relationship-evidence invariant.
    ftm_person = StatementEntity.from_data(
        dataset,
        {
            "id": "person:standalone",
            "schema": "Person",
            "properties": {"name": ["Standalone Person"]},
        },
    )
    assert ftm_person.schema.name == "Person"

    with pytest.raises(ValueError, match="relationship evidence"):
        Person(
            person_id="person:standalone",
            company_id="company:clinic-a",
            relationship_evidence_ids=(),
        )


def test_searchleads_candidate_fact_requires_evidence_while_ftm_statement_does_not() -> None:
    statement = Statement(
        entity_id="company:clinic-a",
        schema="Company",
        prop="name",
        value="Clinica Facial A Ltda",
        dataset="source-without-searchleads-evidence-envelope",
    )
    assert statement.value == "Clinica Facial A Ltda"

    with pytest.raises(ValueError, match="requires evidence"):
        CandidateFact(
            fact_id="fact:name:1",
            subject_id="company:clinic-a",
            field_name="company_name",
            raw_value="Clinica Facial A Ltda",
            normalized_value="clinica facial a ltda",
            evidence_ids=(),
            provenance_id="prov:name:1",
        )


def test_searchleads_contact_lifecycle_is_stricter_than_ftm_contact_property() -> None:
    dataset = Dataset.make({"name": "searchleads_bakeoff", "title": "SearchLeads bake-off"})
    ftm_person = StatementEntity.from_data(
        dataset,
        {
            "id": "person:ana-silva",
            "schema": "Person",
            "properties": {"name": ["Ana Silva"], "email": ["ana@example.org"]},
        },
    )
    assert ftm_person.get("email") == ["ana@example.org"]

    with pytest.raises(ValueError, match="discovery evidence"):
        ContactPoint(
            contact_id="contact:ana-email",
            owner_id="person:ana-silva",
            kind=ContactKind.EMAIL,
            value="ana@example.org",
            discovery_evidence_ids=(),
        )


def test_nomenklatura_resolver_natively_preserves_identity_judgements(resolver) -> None:
    canonical = resolver.decide("company:a", "company:a-alias", Judgement.POSITIVE)
    assert canonical.canonical
    assert resolver.get_judgement("company:a", "company:a-alias") is Judgement.POSITIVE
    assert resolver.get_canonical("company:a") == resolver.get_canonical("company:a-alias")

    resolver.decide("company:a", "company:b", Judgement.NEGATIVE)
    assert resolver.get_judgement("company:a", "company:b") is Judgement.NEGATIVE

    resolver.decide("person:a", "person:b", Judgement.UNSURE)
    assert resolver.get_judgement("person:a", "person:b") is Judgement.UNSURE


def test_chassis_bakeoff_capability_scorecard() -> None:
    # Each item below is backed by an executable probe above. The score is not a
    # product-quality metric; it is a narrow chassis-fit measurement for the
    # invariants selected in this experiment.
    capabilities = {
        "company_person_entity_model": "NATIVE",
        "per_fact_dataset_origin": "NATIVE",
        "identity_positive_negative_unsure": "NATIVE",
        "person_company_relationship_evidence_required": "SEARCHLEADS_EXTENSION",
        "raw_evidence_required_for_candidate_fact": "SEARCHLEADS_EXTENSION",
        "contact_discovery_validation_lifecycle": "SEARCHLEADS_EXTENSION",
    }
    native = sum(value == "NATIVE" for value in capabilities.values())
    extension = sum(value == "SEARCHLEADS_EXTENSION" for value in capabilities.values())

    assert native == 3
    assert extension == 3
    assert native + extension == len(capabilities)

    print("CHASSIS_BAKEOFF_V1")
    print(f"capabilities={len(capabilities)} native={native} searchleads_extension={extension}")
    for capability, classification in capabilities.items():
        print(f"{capability}={classification}")
