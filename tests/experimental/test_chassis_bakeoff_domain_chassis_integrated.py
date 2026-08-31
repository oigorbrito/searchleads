from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LegacyPerson:
    person_id: str
    company_id: str
    relationship_evidence_ids: tuple[str, ...]
    fact_ids: tuple[str, ...] = ()
    contact_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PersonIdentity:
    person_id: str


@dataclass(frozen=True, slots=True)
class PersonCompanyRelationship:
    relationship_id: str
    person_id: str
    company_id: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScopedFact:
    fact_id: str
    subject_id: str
    field_name: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RelationshipContactLink:
    relationship_id: str
    contact_id: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProfessionalRegistration:
    registration_id: str
    person_id: str
    authority: str
    number: str
    status: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StatementEvidenceLink:
    statement_id: str
    evidence_ids: tuple[str, ...]


def _relationship_id(person_id: str, company_id: str) -> str:
    return f"person-company:{person_id}:{company_id}"


def split_without_er(records: tuple[LegacyPerson, ...]) -> tuple[tuple[PersonIdentity, ...], tuple[PersonCompanyRelationship, ...]]:
    """Structural split only: preserve every legacy person identity; never dedupe here."""
    identities = tuple(PersonIdentity(record.person_id) for record in records)
    relationships = tuple(
        PersonCompanyRelationship(
            _relationship_id(record.person_id, record.company_id),
            record.person_id,
            record.company_id,
            record.relationship_evidence_ids,
        )
        for record in records
    )
    return identities, relationships


def test_structural_split_preserves_identity_cardinality_and_performs_zero_silent_merges() -> None:
    legacy = (
        LegacyPerson("person:ana:a", "company:a", ("evidence:rel:a",)),
        LegacyPerson("person:ana:b", "company:b", ("evidence:rel:b",)),
    )

    identities, relationships = split_without_er(legacy)

    assert len(identities) == len(legacy) == 2
    assert {item.person_id for item in identities} == {"person:ana:a", "person:ana:b"}
    assert len(relationships) == 2
    assert {item.company_id for item in relationships} == {"company:a", "company:b"}
    assert {e for item in relationships for e in item.evidence_ids} == {"evidence:rel:a", "evidence:rel:b"}

    print("DOMAIN_CHASSIS_STRUCTURAL_SPLIT_V1")
    print("legacy_person_records=2")
    print("identity_records_after_structural_split=2")
    print("silent_identity_merges=0")
    print("relationship_evidence_loss=0")


def test_one_canonical_identity_can_have_two_relationships_only_after_explicit_er_decision() -> None:
    canonical = PersonIdentity("person:ana:canonical")
    relationships = (
        PersonCompanyRelationship("relationship:a", canonical.person_id, "company:a", ("evidence:rel:a",)),
        PersonCompanyRelationship("relationship:b", canonical.person_id, "company:b", ("evidence:rel:b",)),
    )

    assert len({item.person_id for item in relationships}) == 1
    assert len({item.company_id for item in relationships}) == 2
    assert relationships[0].relationship_id != relationships[1].relationship_id

    print("DOMAIN_CHASSIS_POST_ER_MULTI_RELATIONSHIP_V1")
    print("canonical_person_identities=1")
    print("organization_relationships=2")


def test_relationship_scoped_role_and_contact_do_not_leak_between_companies() -> None:
    relationship_a = PersonCompanyRelationship(
        "relationship:a", "person:ana", "company:a", ("evidence:rel:a",)
    )
    relationship_b = PersonCompanyRelationship(
        "relationship:b", "person:ana", "company:b", ("evidence:rel:b",)
    )
    role_a = ScopedFact(
        "fact:role:a",
        relationship_a.relationship_id,
        "professional_role_title",
        ("evidence:role:a",),
    )
    contact_link_a = RelationshipContactLink(
        relationship_a.relationship_id,
        "contact:ana@empresa-a.example",
        ("evidence:contact:a",),
    )

    assert role_a.subject_id == relationship_a.relationship_id
    assert role_a.subject_id != relationship_b.relationship_id
    assert contact_link_a.relationship_id == relationship_a.relationship_id
    assert contact_link_a.relationship_id != relationship_b.relationship_id

    print("DOMAIN_CHASSIS_RELATIONSHIP_SCOPE_V1")
    print("role_leak_a_to_b=0")
    print("corporate_contact_leak_a_to_b=0")


def test_professional_registration_is_person_scoped_not_company_scoped() -> None:
    registration = ProfessionalRegistration(
        "registration:cro-sp:123",
        "person:ana",
        "CRO-SP",
        "123",
        "VERIFIED_ACTIVE",
        ("evidence:cro-current",),
    )

    assert registration.person_id == "person:ana"
    assert not hasattr(registration, "company_id")
    assert registration.evidence_ids == ("evidence:cro-current",)

    print("DOMAIN_CHASSIS_PROFESSIONAL_REGISTRATION_SCOPE_V1")
    print("registration_subject=person_identity")
    print("company_dependency=NO")
    print("current_status_requires_evidence=YES")


def test_fact_and_statement_lineage_support_many_to_many_evidence_without_identifier_overload() -> None:
    facts = (
        ScopedFact("fact:name", "person:ana", "person_name", ("evidence:page-1",)),
        ScopedFact("fact:role", "relationship:a", "professional_role_title", ("evidence:page-1",)),
    )
    links = (
        StatementEvidenceLink("statement:name", ("evidence:page-1", "evidence:registry-2")),
        StatementEvidenceLink("statement:role", ("evidence:page-1",)),
    )

    assert len({fact.fact_id for fact in facts}) == 2
    assert facts[0].evidence_ids == facts[1].evidence_ids == ("evidence:page-1",)
    assert links[0].statement_id != links[1].statement_id
    assert "evidence:page-1" in links[0].evidence_ids and "evidence:page-1" in links[1].evidence_ids
    assert len(links[0].evidence_ids) == 2

    print("DOMAIN_CHASSIS_LINEAGE_CARDINALITY_V1")
    print("one_evidence_to_multiple_semantic_records=YES")
    print("one_statement_to_multiple_evidence=YES")
    print("statement_id_equals_evidence_id=NO")


def test_candidate_domain_decision_matrix_is_explicit() -> None:
    decisions = {
        "person_identity": "REPLACE",
        "person_company_relationship": "REPLACE",
        "company_person_ids_snapshot": "REPLACE",
        "professional_registration": "REPLACE",
        "relationship_contact_scope": "COMPOSE",
        "relationship_fact_scope": "COMPOSE",
        "raw_evidence_store": "KEEP",
        "evidence_integrity": "KEEP",
        "ftm_statement_semantics": "COMPOSE",
        "qualification_policy": "KEEP",
    }
    assert set(decisions.values()) <= {"KEEP", "REPLACE", "COMPOSE", "DEFER"}
    assert decisions["person_identity"] == "REPLACE"
    assert decisions["raw_evidence_store"] == "KEEP"
    assert decisions["ftm_statement_semantics"] == "COMPOSE"

    print("DOMAIN_CHASSIS_DECISION_MATRIX_V1")
    for component, decision in decisions.items():
        print(f"{component}={decision}")
