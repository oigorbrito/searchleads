from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from searchleads.domain import (
    CandidateFact,
    CanonicalFact,
    Company,
    Conflict,
    ConflictStatus,
    ContactKind,
    ContactPoint,
    EntityRef,
    EntityType,
    Evidence,
    Person,
    Provenance,
    Source,
    SourceType,
)
from searchleads.persistence import (
    IdentityCollisionError,
    MissingReferenceError,
    SCHEMA_VERSION,
    SQLiteLeadStore,
)


NOW = datetime(2026, 8, 21, 13, 30, tzinfo=timezone.utc)


class PersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "leads.sqlite3"
        self.store = SQLiteLeadStore(self.db_path)
        self.company = Company(company_id="company-1", created_at=NOW)
        self.person = Person(person_id="person-1", created_at=NOW)
        self.source = Source(
            source_id="source-1",
            source_type=SourceType.WEBSITE,
            locator="https://example.com/contact",
            label="Example contact page",
        )
        self.evidence = Evidence(
            evidence_id="evidence-1",
            source_id=self.source.source_id,
            retrieved_at=NOW,
            payload={
                "html": b"<p>ACME Tecnologia</p>",
                "fields": ["ACME", {"email": "contato@acme.example"}],
                "captured": NOW,
            },
            locator="#contact",
            content_hash="sha256:example",
        )
        self.provenance = Provenance(
            evidence_ids=(self.evidence.evidence_id,),
            activity="extract_contact_page",
            generated_at=NOW,
            agent="test-adapter",
        )
        self.company_ref = EntityRef(EntityType.COMPANY, self.company.company_id)

    def tearDown(self) -> None:
        self.store.close()
        self.tempdir.cleanup()

    def _save_foundation(self) -> None:
        self.store.save_company(self.company)
        self.store.save_person(self.person)
        self.store.save_source(self.source)
        self.store.save_evidence(self.evidence)

    def _candidate(self, fact_id: str, value: str) -> CandidateFact:
        return CandidateFact(
            candidate_fact_id=fact_id,
            subject=self.company_ref,
            predicate="company_name",
            raw_value=value,
            normalized_value=value.strip(),
            normalization_rule="trim_whitespace",
            provenance=self.provenance,
            confidence=0.8,
        )

    def test_schema_is_versioned(self) -> None:
        self.assertEqual(self.store.schema_version, SCHEMA_VERSION)

    def test_company_and_person_round_trip(self) -> None:
        self.store.save_company(self.company)
        self.store.save_person(self.person)
        self.assertEqual(self.store.get_company(self.company.company_id), self.company)
        self.assertEqual(self.store.get_person(self.person.person_id), self.person)

    def test_source_and_raw_evidence_round_trip_losslessly(self) -> None:
        self.store.save_source(self.source)
        self.store.save_evidence(self.evidence)
        loaded = self.store.get_evidence(self.evidence.evidence_id)
        self.assertEqual(self.store.get_source(self.source.source_id), self.source)
        self.assertEqual(loaded, self.evidence)
        self.assertEqual(loaded.payload["html"], b"<p>ACME Tecnologia</p>")
        self.assertEqual(loaded.payload["captured"], NOW)

    def test_evidence_can_be_reopened_from_disk_and_reprocessed(self) -> None:
        self.store.save_source(self.source)
        self.store.save_evidence(self.evidence)
        self.store.close()
        self.store = SQLiteLeadStore(self.db_path)

        observations = self.store.list_evidence(source_id=self.source.source_id)

        self.assertEqual(observations, (self.evidence,))
        self.assertIn(b"ACME", observations[0].payload["html"])

    def test_evidence_requires_persisted_source(self) -> None:
        with self.assertRaises(MissingReferenceError):
            self.store.save_evidence(self.evidence)

    def test_contact_point_round_trip_preserves_provenance(self) -> None:
        self._save_foundation()
        contact = ContactPoint(
            contact_id="contact-1",
            owner=self.company_ref,
            kind=ContactKind.EMAIL,
            value="contato@acme.example",
            provenance=self.provenance,
        )
        self.store.save_contact_point(contact)
        self.assertEqual(self.store.get_contact_point(contact.contact_id), contact)

    def test_contact_requires_persisted_owner(self) -> None:
        self.store.save_source(self.source)
        self.store.save_evidence(self.evidence)
        contact = ContactPoint(
            contact_id="contact-1",
            owner=self.company_ref,
            kind=ContactKind.EMAIL,
            value="contato@acme.example",
            provenance=self.provenance,
        )
        with self.assertRaises(MissingReferenceError):
            self.store.save_contact_point(contact)

    def test_candidate_fact_round_trip_preserves_raw_normalized_and_provenance(self) -> None:
        self._save_foundation()
        fact = self._candidate("candidate-1", " ACME Tecnologia ")
        self.store.save_candidate_fact(fact)
        self.assertEqual(self.store.get_candidate_fact(fact.candidate_fact_id), fact)

    def test_fact_provenance_must_reference_persisted_evidence(self) -> None:
        self.store.save_company(self.company)
        fact = self._candidate("candidate-1", "ACME")
        with self.assertRaises(MissingReferenceError):
            self.store.save_candidate_fact(fact)

    def test_canonical_fact_round_trip_requires_persisted_candidates(self) -> None:
        self._save_foundation()
        candidate = self._candidate("candidate-1", "ACME")
        self.store.save_candidate_fact(candidate)
        canonical = CanonicalFact(
            canonical_fact_id="canonical-1",
            subject=self.company_ref,
            predicate="company_name",
            value="ACME",
            candidate_fact_ids=(candidate.candidate_fact_id,),
            provenance=self.provenance,
            confidence=0.9,
        )
        self.store.save_canonical_fact(canonical)
        self.assertEqual(self.store.get_canonical_fact(canonical.canonical_fact_id), canonical)

    def test_conflict_round_trip_for_open_and_resolved_states(self) -> None:
        self._save_foundation()
        candidate_1 = self._candidate("candidate-1", "ACME")
        candidate_2 = self._candidate("candidate-2", "ACME Tecnologia")
        self.store.save_candidate_fact(candidate_1)
        self.store.save_candidate_fact(candidate_2)

        open_conflict = Conflict(
            conflict_id="conflict-open",
            subject=self.company_ref,
            predicate="company_name",
            candidate_fact_ids=(candidate_1.candidate_fact_id, candidate_2.candidate_fact_id),
        )
        self.store.save_conflict(open_conflict)
        self.assertEqual(self.store.get_conflict(open_conflict.conflict_id), open_conflict)

        canonical = CanonicalFact(
            canonical_fact_id="canonical-1",
            subject=self.company_ref,
            predicate="company_name",
            value="ACME Tecnologia",
            candidate_fact_ids=(candidate_1.candidate_fact_id, candidate_2.candidate_fact_id),
            provenance=self.provenance,
        )
        self.store.save_canonical_fact(canonical)
        resolved = Conflict(
            conflict_id="conflict-resolved",
            subject=self.company_ref,
            predicate="company_name",
            candidate_fact_ids=(candidate_1.candidate_fact_id, candidate_2.candidate_fact_id),
            status=ConflictStatus.RESOLVED,
            resolved_canonical_fact_id=canonical.canonical_fact_id,
            resolution_note="Resolution is represented without deleting competing candidates.",
        )
        self.store.save_conflict(resolved)
        self.assertEqual(self.store.get_conflict(resolved.conflict_id), resolved)

    def test_complete_fact_graph_survives_database_reopen(self) -> None:
        self._save_foundation()
        contact = ContactPoint(
            contact_id="contact-reopen",
            owner=self.company_ref,
            kind=ContactKind.EMAIL,
            value="contato@acme.example",
            provenance=self.provenance,
        )
        candidate_1 = self._candidate("candidate-reopen-1", " ACME ")
        candidate_2 = self._candidate("candidate-reopen-2", "ACME Tecnologia")
        self.store.save_contact_point(contact)
        self.store.save_candidate_fact(candidate_1)
        self.store.save_candidate_fact(candidate_2)
        canonical = CanonicalFact(
            canonical_fact_id="canonical-reopen",
            subject=self.company_ref,
            predicate="company_name",
            value="ACME Tecnologia",
            candidate_fact_ids=(candidate_1.candidate_fact_id, candidate_2.candidate_fact_id),
            provenance=self.provenance,
        )
        self.store.save_canonical_fact(canonical)
        conflict = Conflict(
            conflict_id="conflict-reopen",
            subject=self.company_ref,
            predicate="company_name",
            candidate_fact_ids=(candidate_1.candidate_fact_id, candidate_2.candidate_fact_id),
            status=ConflictStatus.RESOLVED,
            resolved_canonical_fact_id=canonical.canonical_fact_id,
            resolution_note="Both competing observations remain persisted.",
        )
        self.store.save_conflict(conflict)

        self.store.close()
        self.store = SQLiteLeadStore(self.db_path)

        self.assertEqual(self.store.get_company(self.company.company_id), self.company)
        self.assertEqual(self.store.get_person(self.person.person_id), self.person)
        self.assertEqual(self.store.get_source(self.source.source_id), self.source)
        self.assertEqual(self.store.get_evidence(self.evidence.evidence_id), self.evidence)
        self.assertEqual(self.store.get_contact_point(contact.contact_id), contact)
        self.assertEqual(self.store.get_candidate_fact(candidate_1.candidate_fact_id), candidate_1)
        self.assertEqual(self.store.get_candidate_fact(candidate_2.candidate_fact_id), candidate_2)
        self.assertEqual(self.store.get_canonical_fact(canonical.canonical_fact_id), canonical)
        self.assertEqual(self.store.get_conflict(conflict.conflict_id), conflict)

    def test_reusing_stable_id_with_different_content_is_rejected(self) -> None:
        self.store.save_company(self.company)
        self.store.save_company(self.company)  # idempotent identical write
        changed = Company(
            company_id=self.company.company_id,
            created_at=datetime(2026, 8, 22, 13, 30, tzinfo=timezone.utc),
        )
        with self.assertRaises(IdentityCollisionError):
            self.store.save_company(changed)


if __name__ == "__main__":
    unittest.main()
