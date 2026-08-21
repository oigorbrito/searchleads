from __future__ import annotations

import unittest
from datetime import datetime, timezone

from searchleads.domain import (
    CandidateFact,
    CanonicalFact,
    Company,
    Conflict,
    ConflictStatus,
    ContactKind,
    ContactPoint,
    ContactStatus,
    EntityRef,
    EntityType,
    Evidence,
    Lead,
    LeadStatus,
    Person,
    ProfessionalRole,
    Provenance,
    Source,
    SourceType,
)


NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)


class DomainModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = Source(
            source_id="src-1",
            source_type=SourceType.WEBSITE,
            locator="https://example.com/contact",
            label="Example contact page",
        )
        self.evidence = Evidence(
            evidence_id="ev-1",
            source_id=self.source.source_id,
            retrieved_at=NOW,
            payload={"text": "ACME Tecnologia — contato@acme.example"},
            locator="#contact",
        )
        self.provenance = Provenance(
            evidence_ids=(self.evidence.evidence_id,),
            activity="extract_contact_page",
            generated_at=NOW,
            agent="test-adapter",
        )
        self.company = Company(company_id="company-1", created_at=NOW)
        self.company_ref = EntityRef(EntityType.COMPANY, self.company.company_id)

    def test_company_is_not_a_lead(self) -> None:
        self.assertIsInstance(self.company, Company)
        self.assertNotIsInstance(self.company, Lead)
        lead = Lead(
            lead_id="lead-1",
            company_id=self.company.company_id,
            status=LeadStatus.UNKNOWN,
            created_at=NOW,
        )
        self.assertEqual(lead.company_id, self.company.company_id)
        self.assertNotEqual(lead.lead_id, self.company.company_id)

    def test_candidate_fact_preserves_raw_and_normalized_values(self) -> None:
        fact = CandidateFact(
            candidate_fact_id="cf-1",
            subject=self.company_ref,
            predicate="company_name",
            raw_value=" ACME Tecnologia Ltda. ",
            normalized_value="ACME Tecnologia Ltda.",
            normalization_rule="trim_whitespace",
            provenance=self.provenance,
        )
        self.assertEqual(fact.raw_value, " ACME Tecnologia Ltda. ")
        self.assertEqual(fact.normalized_value, "ACME Tecnologia Ltda.")
        self.assertEqual(fact.provenance.evidence_ids, ("ev-1",))

    def test_canonical_fact_requires_candidate_support_and_provenance(self) -> None:
        fact = CanonicalFact(
            canonical_fact_id="canon-1",
            subject=self.company_ref,
            predicate="company_name",
            value="ACME Tecnologia Ltda.",
            candidate_fact_ids=("cf-1",),
            provenance=self.provenance,
            confidence=0.9,
        )
        self.assertEqual(fact.candidate_fact_ids, ("cf-1",))
        with self.assertRaises(ValueError):
            CanonicalFact(
                canonical_fact_id="canon-2",
                subject=self.company_ref,
                predicate="company_name",
                value="ACME",
                candidate_fact_ids=(),
                provenance=self.provenance,
            )

    def test_open_conflict_requires_two_candidates(self) -> None:
        conflict = Conflict(
            conflict_id="conflict-1",
            subject=self.company_ref,
            predicate="company_name",
            candidate_fact_ids=("cf-1", "cf-2"),
        )
        self.assertEqual(conflict.status, ConflictStatus.OPEN)
        with self.assertRaises(ValueError):
            Conflict(
                conflict_id="conflict-invalid",
                subject=self.company_ref,
                predicate="company_name",
                candidate_fact_ids=("cf-1",),
            )

    def test_resolved_conflict_must_reference_canonical_fact(self) -> None:
        with self.assertRaises(ValueError):
            Conflict(
                conflict_id="conflict-2",
                subject=self.company_ref,
                predicate="company_name",
                candidate_fact_ids=("cf-1", "cf-2"),
                status=ConflictStatus.RESOLVED,
            )
        resolved = Conflict(
            conflict_id="conflict-3",
            subject=self.company_ref,
            predicate="company_name",
            candidate_fact_ids=("cf-1", "cf-2"),
            status=ConflictStatus.RESOLVED,
            resolved_canonical_fact_id="canon-1",
            resolution_note="Selected the fact supported by the official source.",
        )
        self.assertEqual(resolved.resolved_canonical_fact_id, "canon-1")

    def test_contact_point_is_separate_and_found_is_not_validated(self) -> None:
        contact = ContactPoint(
            contact_id="contact-1",
            owner=self.company_ref,
            kind=ContactKind.EMAIL,
            value="contato@acme.example",
            provenance=self.provenance,
        )
        self.assertEqual(contact.status, ContactStatus.DISCOVERED)
        self.assertNotEqual(contact.status, ContactStatus.VALIDATED)

    def test_contact_owner_must_be_company_or_person(self) -> None:
        with self.assertRaises(ValueError):
            ContactPoint(
                contact_id="contact-2",
                owner=EntityRef(EntityType.LEAD, "lead-1"),
                kind=ContactKind.EMAIL,
                value="sales@example.com",
                provenance=self.provenance,
            )

    def test_person_role_relationship_requires_provenance(self) -> None:
        person = Person(person_id="person-1", created_at=NOW)
        role = ProfessionalRole(
            role_id="role-1",
            person_id=person.person_id,
            company_id=self.company.company_id,
            title="Diretor Comercial",
            provenance=self.provenance,
        )
        self.assertEqual(role.person_id, person.person_id)
        self.assertEqual(role.company_id, self.company.company_id)
        self.assertEqual(role.provenance.evidence_ids, ("ev-1",))

    def test_evidence_timestamp_must_be_timezone_aware(self) -> None:
        with self.assertRaises(ValueError):
            Evidence(
                evidence_id="ev-naive",
                source_id="src-1",
                retrieved_at=datetime(2026, 8, 21, 12, 0),
                payload="raw",
            )

    def test_confidence_bounds_are_enforced(self) -> None:
        with self.assertRaises(ValueError):
            CandidateFact(
                candidate_fact_id="cf-confidence",
                subject=self.company_ref,
                predicate="domain",
                raw_value="acme.example",
                provenance=self.provenance,
                confidence=1.1,
            )

    def test_qualified_lead_requires_explicit_reason(self) -> None:
        with self.assertRaises(ValueError):
            Lead(
                lead_id="lead-2",
                company_id=self.company.company_id,
                status=LeadStatus.QUALIFIED,
                created_at=NOW,
            )
        lead = Lead(
            lead_id="lead-3",
            company_id=self.company.company_id,
            status=LeadStatus.QUALIFIED,
            reasons=("Meets future externally-defined ICP criteria",),
            qualification_facts=("canon-industry",),
            created_at=NOW,
        )
        self.assertEqual(lead.status, LeadStatus.QUALIFIED)


if __name__ == "__main__":
    unittest.main()
