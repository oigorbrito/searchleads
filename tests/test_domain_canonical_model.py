from __future__ import annotations

from datetime import datetime, timezone

from searchleads.domain import (
    Company,
    ContactKind,
    ContactPoint,
    Evidence,
    Lead,
    LeadStage,
    Person,
    PersonCompanyRelationship,
    PersonIdentity,
    ProfessionalRegistration,
    Provenance,
    QualificationDecision,
    QualificationStatus,
    RelationshipContactLink,
    Source,
    Statement,
    StatementEvidenceLink,
    project_company_person_ids,
    project_legacy_person,
    relationship_id_for,
    split_legacy_person,
)
from searchleads.persistence import SQLiteRepository

NOW = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)


def test_canonical_domain_records_round_trip_through_persistence() -> None:
    source = Source("src-1", "website", "https://example.test", "Example")
    evidence = Evidence("ev-1", "src-1", "https://example.test/people", NOW, "raw payload")
    company = Company("company-1")
    identity = PersonIdentity("person-1")
    relationship = PersonCompanyRelationship(
        "relationship-1",
        identity.person_id,
        company.company_id,
        ("ev-1",),
        "Finance Director",
        "employment",
        "KNOWN",
        NOW,
    )
    contact = ContactPoint("contact-1", company.company_id, ContactKind.EMAIL, "ana@example.test", ("ev-1",))
    contact_link = RelationshipContactLink("contact-link-1", relationship.relationship_id, contact.contact_id, ("ev-1",))
    registration = ProfessionalRegistration("registration-1", identity.person_id, "CRO-SP", "123", "VERIFIED_ACTIVE", ("ev-1",))
    provenance = Provenance("prov-1", relationship.relationship_id, "professional_role_title", ("ev-1",), "structured-extraction", NOW)
    statement = Statement("statement-1", relationship.relationship_id, "professional_role_title", "Finance Director", provenance.provenance_id, "structured-extraction")
    statement_link = StatementEvidenceLink("statement-link-1", statement.statement_id, ("ev-1",))
    lead = Lead("lead-1", company.company_id, LeadStage.CANDIDATE, QualificationStatus.UNKNOWN)
    decision = QualificationDecision("decision-1", lead.lead_id, QualificationStatus.UNKNOWN, ("pending-review",), ("ev-1",), NOW)

    with SQLiteRepository() as repo:
        for record in (
            source,
            evidence,
            company,
            identity,
            relationship,
            contact,
            contact_link,
            registration,
            provenance,
            statement,
            statement_link,
            lead,
            decision,
        ):
            assert repo.save(record) is True

        assert repo.load(PersonIdentity, identity.person_id) == identity
        assert repo.load(PersonCompanyRelationship, relationship.relationship_id) == relationship
        assert repo.load(ProfessionalRegistration, registration.registration_id) == registration
        assert repo.load(RelationshipContactLink, contact_link.link_id) == contact_link
        assert repo.load(Statement, statement.statement_id) == statement
        assert repo.load(StatementEvidenceLink, statement_link.link_id) == statement_link
        assert repo.load(QualificationDecision, decision.decision_id) == decision


def test_relationship_scoped_contact_and_role_remain_explicit() -> None:
    company_a = Company("company-a")
    company_b = Company("company-b")
    person = PersonIdentity("person-ana")
    relationship_a = PersonCompanyRelationship("rel-a", person.person_id, company_a.company_id, ("ev-a",), "Finance Director")
    relationship_b = PersonCompanyRelationship("rel-b", person.person_id, company_b.company_id, ("ev-b",), "Board Member")
    contact = ContactPoint("contact-ana", company_a.company_id, ContactKind.EMAIL, "ana@empresa-a.test", ("ev-a",))
    contact_link = RelationshipContactLink("contact-link", relationship_a.relationship_id, contact.contact_id, ("ev-a",))

    assert relationship_a.company_id == company_a.company_id
    assert relationship_b.company_id == company_b.company_id
    assert relationship_a.relationship_id != relationship_b.relationship_id
    assert contact_link.relationship_id == relationship_a.relationship_id
    assert contact_link.relationship_id != relationship_b.relationship_id
    assert not hasattr(person, "company_id")


def test_statement_and_evidence_are_distinct_records() -> None:
    provenance = Provenance("prov-1", "subject-1", "field-1", ("ev-1",), "structured-extraction", NOW)
    statement = Statement("statement-1", "subject-1", "field-1", "value-1", provenance.provenance_id, "structured-extraction")
    link = StatementEvidenceLink("statement-link-1", statement.statement_id, ("ev-1", "ev-2"))

    assert statement.statement_id != "ev-1"
    assert link.statement_id == statement.statement_id
    assert link.evidence_ids == ("ev-1", "ev-2")


def test_legacy_person_migration_helpers_preserve_identity_and_company_scope() -> None:
    legacy = Person(
        "person-legacy",
        "company-legacy",
        ("ev-legacy",),
        ("candidate-legacy",),
        ("canonical-legacy",),
        ("contact-legacy",),
    )

    identity, relationship = split_legacy_person(legacy)
    projected = project_legacy_person(
        identity,
        relationship,
        candidate_fact_ids=legacy.candidate_fact_ids,
        canonical_fact_ids=legacy.canonical_fact_ids,
        contact_point_ids=legacy.contact_point_ids,
    )
    company = Company("company-legacy", person_ids=("person-legacy", "person-other"))
    other_relationship = PersonCompanyRelationship(
        "relationship-other",
        "person-other",
        company.company_id,
        ("ev-other",),
    )

    assert identity.person_id == legacy.person_id
    assert relationship.relationship_id == relationship_id_for(legacy.person_id, legacy.company_id)
    assert relationship.person_id == legacy.person_id
    assert relationship.company_id == legacy.company_id
    assert projected == legacy
    assert project_company_person_ids(company, (relationship, other_relationship)) == (
        "person-legacy",
        "person-other",
    )
