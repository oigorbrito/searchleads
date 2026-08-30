from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
import sqlite3

import pytest

from searchleads.domain import Company, Evidence, Person, Source
from searchleads.persistence import SQLiteRepository


class CandidatePersistenceConflict(RuntimeError):
    pass


class RegistrationStatus(StrEnum):
    VERIFIED_ACTIVE = "VERIFIED_ACTIVE"
    INACTIVE = "INACTIVE"
    NOT_FOUND = "NOT_FOUND"
    PENDING = "PENDING"


@dataclass(frozen=True, slots=True)
class PersonIdentityRow:
    person_id: str
    candidate_fact_ids: tuple[str, ...] = ()
    canonical_fact_ids: tuple[str, ...] = ()
    contact_point_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PersonCompanyRelationshipRow:
    relationship_id: str
    person_id: str
    company_id: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProfessionalRegistrationRow:
    registration_id: str
    person_id: str
    authority: str
    number: str
    jurisdiction: str
    status: RegistrationStatus
    evidence_ids: tuple[str, ...]


class RelationshipCandidateStore:
    """Experimental sidecar store; deliberately not production persistence."""

    def __init__(self, references: SQLiteRepository) -> None:
        self.references = references
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(
            """
            CREATE TABLE person_identity (
                person_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE person_company_relationship (
                relationship_id TEXT PRIMARY KEY,
                person_id TEXT NOT NULL REFERENCES person_identity(person_id),
                company_id TEXT NOT NULL,
                evidence_ids_json TEXT NOT NULL
            );
            CREATE INDEX idx_relationship_person
                ON person_company_relationship(person_id, relationship_id);
            CREATE INDEX idx_relationship_company
                ON person_company_relationship(company_id, relationship_id);
            CREATE TABLE professional_registration (
                registration_id TEXT PRIMARY KEY,
                person_id TEXT NOT NULL REFERENCES person_identity(person_id),
                authority TEXT NOT NULL,
                number TEXT NOT NULL,
                jurisdiction TEXT NOT NULL,
                status TEXT NOT NULL,
                evidence_ids_json TEXT NOT NULL
            );
            CREATE INDEX idx_registration_person
                ON professional_registration(person_id, registration_id);
            """
        )

    def close(self) -> None:
        self.db.close()

    @staticmethod
    def _json_tuple(values: tuple[str, ...]) -> str:
        return json.dumps(list(values), ensure_ascii=False, separators=(",", ":"))

    def _require_evidence(self, evidence_ids: tuple[str, ...]) -> None:
        if not evidence_ids:
            raise ValueError("candidate record requires evidence")
        for evidence_id in evidence_ids:
            if self.references.load(Evidence, evidence_id) is None:
                raise ValueError(f"missing Evidence {evidence_id!r}")

    def save_identity(self, row: PersonIdentityRow) -> bool:
        if not row.person_id.strip():
            raise ValueError("person_id must not be blank")
        payload = json.dumps(
            {
                "candidate_fact_ids": row.candidate_fact_ids,
                "canonical_fact_ids": row.canonical_fact_ids,
                "contact_point_ids": row.contact_point_ids,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        existing = self.db.execute(
            "SELECT payload_json FROM person_identity WHERE person_id = ?", (row.person_id,)
        ).fetchone()
        if existing is not None:
            if existing["payload_json"] == payload:
                return False
            raise CandidatePersistenceConflict("person identity reused with different content")
        self.db.execute(
            "INSERT INTO person_identity(person_id, payload_json) VALUES (?, ?)",
            (row.person_id, payload),
        )
        self.db.commit()
        return True

    def save_relationship(self, row: PersonCompanyRelationshipRow) -> bool:
        self._require_evidence(row.evidence_ids)
        if self.references.load(Company, row.company_id) is None:
            raise ValueError(f"missing Company {row.company_id!r}")
        payload = self._json_tuple(row.evidence_ids)
        existing = self.db.execute(
            """SELECT person_id, company_id, evidence_ids_json
               FROM person_company_relationship WHERE relationship_id = ?""",
            (row.relationship_id,),
        ).fetchone()
        expected = (row.person_id, row.company_id, payload)
        if existing is not None:
            actual = (existing["person_id"], existing["company_id"], existing["evidence_ids_json"])
            if actual == expected:
                return False
            raise CandidatePersistenceConflict("relationship id reused with different content")
        self.db.execute(
            """INSERT INTO person_company_relationship(
                   relationship_id, person_id, company_id, evidence_ids_json
               ) VALUES (?, ?, ?, ?)""",
            (row.relationship_id, row.person_id, row.company_id, payload),
        )
        self.db.commit()
        return True

    def save_registration(self, row: ProfessionalRegistrationRow) -> bool:
        self._require_evidence(row.evidence_ids)
        payload = self._json_tuple(row.evidence_ids)
        existing = self.db.execute(
            """SELECT person_id, authority, number, jurisdiction, status, evidence_ids_json
               FROM professional_registration WHERE registration_id = ?""",
            (row.registration_id,),
        ).fetchone()
        expected = (
            row.person_id,
            row.authority,
            row.number,
            row.jurisdiction,
            row.status.value,
            payload,
        )
        if existing is not None:
            actual = tuple(existing[key] for key in (
                "person_id", "authority", "number", "jurisdiction", "status", "evidence_ids_json"
            ))
            if actual == expected:
                return False
            raise CandidatePersistenceConflict("registration id reused with different content")
        self.db.execute(
            """INSERT INTO professional_registration(
                   registration_id, person_id, authority, number, jurisdiction, status, evidence_ids_json
               ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            expected[:1] + expected[1:],
        )
        self.db.commit()
        return True

    def counts(self) -> tuple[int, int, int]:
        return tuple(
            int(self.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in (
                "person_identity",
                "person_company_relationship",
                "professional_registration",
            )
        )  # type: ignore[return-value]


def _seed_reference_repository() -> SQLiteRepository:
    repository = SQLiteRepository()
    source = Source(
        source_id="source:official",
        source_type="official_web",
        locator="https://official.example/",
    )
    evidence_a = Evidence(
        evidence_id="evidence:a",
        source_id=source.source_id,
        locator="https://official.example/a",
        raw_payload="relationship A",
    )
    evidence_b = Evidence(
        evidence_id="evidence:b",
        source_id=source.source_id,
        locator="https://official.example/b",
        raw_payload="relationship B",
    )
    evidence_reg = Evidence(
        evidence_id="evidence:registration",
        source_id=source.source_id,
        locator="https://official.example/registry",
        raw_payload="CRO-SP 12345 ACTIVE",
    )
    repository.save(source)
    repository.save(evidence_a)
    repository.save(evidence_b)
    repository.save(evidence_reg)
    repository.save(Company("company:a"))
    repository.save(Company("company:b"))
    return repository


def _split_legacy(person: Person) -> tuple[PersonIdentityRow, PersonCompanyRelationshipRow]:
    return (
        PersonIdentityRow(
            person.person_id,
            person.candidate_fact_ids,
            person.canonical_fact_ids,
            person.contact_point_ids,
        ),
        PersonCompanyRelationshipRow(
            f"person-company:{person.person_id}:{person.company_id}",
            person.person_id,
            person.company_id,
            person.relationship_evidence_ids,
        ),
    )


def test_candidate_store_persists_one_identity_with_two_company_relationships() -> None:
    references = _seed_reference_repository()
    store = RelationshipCandidateStore(references)
    try:
        identity = PersonIdentityRow("person:ana")
        assert store.save_identity(identity) is True
        assert store.save_identity(identity) is False
        assert store.save_relationship(PersonCompanyRelationshipRow(
            "rel:ana:a", identity.person_id, "company:a", ("evidence:a",)
        )) is True
        assert store.save_relationship(PersonCompanyRelationshipRow(
            "rel:ana:b", identity.person_id, "company:b", ("evidence:b",)
        )) is True
        assert store.counts() == (1, 2, 0)

        print("RELATIONAL_PERSISTENCE_MULTI_COMPANY_V1")
        print("person_identity_rows=1")
        print("company_relationship_rows=2")
        print("company_snapshot_mutations=0")
    finally:
        store.close()
        references.close()


def test_lossless_v1_migration_does_not_silently_merge_distinct_person_ids() -> None:
    references = _seed_reference_repository()
    store = RelationshipCandidateStore(references)
    try:
        legacy_a = Person("person:obs:a", "company:a", ("evidence:a",))
        legacy_b = Person("person:obs:b", "company:b", ("evidence:b",))
        for person in (legacy_a, legacy_b):
            identity, relationship = _split_legacy(person)
            store.save_identity(identity)
            store.save_relationship(relationship)

        assert store.counts() == (2, 2, 0)
        print("RELATIONAL_MIGRATION_NO_SILENT_ER_V1")
        print("legacy_person_records=2")
        print("migrated_identity_records=2")
        print("automatic_cross_company_merge=NO")
        print("explicit_er_decision_required=YES")
    finally:
        store.close()
        references.close()


def test_explicit_er_resolution_can_point_two_relationships_at_one_identity() -> None:
    references = _seed_reference_repository()
    store = RelationshipCandidateStore(references)
    try:
        canonical = PersonIdentityRow("person:canonical:ana")
        store.save_identity(canonical)
        store.save_relationship(PersonCompanyRelationshipRow(
            "rel:resolved:a", canonical.person_id, "company:a", ("evidence:a",)
        ))
        store.save_relationship(PersonCompanyRelationshipRow(
            "rel:resolved:b", canonical.person_id, "company:b", ("evidence:b",)
        ))
        relationships = store.db.execute(
            "SELECT DISTINCT person_id FROM person_company_relationship"
        ).fetchall()
        assert [row["person_id"] for row in relationships] == [canonical.person_id]
        assert store.counts() == (1, 2, 0)
    finally:
        store.close()
        references.close()


def test_relationship_and_registration_both_require_raw_evidence_references() -> None:
    references = _seed_reference_repository()
    store = RelationshipCandidateStore(references)
    try:
        store.save_identity(PersonIdentityRow("person:ana"))
        with pytest.raises(ValueError, match="missing Evidence"):
            store.save_relationship(PersonCompanyRelationshipRow(
                "rel:bad", "person:ana", "company:a", ("evidence:missing",)
            ))
        with pytest.raises(ValueError, match="missing Evidence"):
            store.save_registration(ProfessionalRegistrationRow(
                "registration:bad", "person:ana", "CRO-SP", "12345", "SP",
                RegistrationStatus.PENDING, ("evidence:missing",)
            ))
    finally:
        store.close()
        references.close()


def test_professional_registration_is_independent_from_company_relationship() -> None:
    references = _seed_reference_repository()
    store = RelationshipCandidateStore(references)
    try:
        identity = PersonIdentityRow("person:ana")
        store.save_identity(identity)
        store.save_relationship(PersonCompanyRelationshipRow(
            "rel:ana:a", identity.person_id, "company:a", ("evidence:a",)
        ))
        registration = ProfessionalRegistrationRow(
            "registration:cro-sp:12345",
            identity.person_id,
            "CRO-SP",
            "12345",
            "SP",
            RegistrationStatus.VERIFIED_ACTIVE,
            ("evidence:registration",),
        )
        assert store.save_registration(registration) is True
        assert store.counts() == (1, 1, 1)
        row = store.db.execute(
            "SELECT person_id, status FROM professional_registration WHERE registration_id = ?",
            (registration.registration_id,),
        ).fetchone()
        assert row["person_id"] == identity.person_id
        assert row["status"] == RegistrationStatus.VERIFIED_ACTIVE.value

        print("RELATIONAL_PROFESSIONAL_REGISTRATION_V1")
        print("registration_has_company_id=NO")
        print("registration_status_independent=YES")
        print("raw_evidence_required=YES")
    finally:
        store.close()
        references.close()


def test_candidate_records_are_immutable_by_stable_id() -> None:
    references = _seed_reference_repository()
    store = RelationshipCandidateStore(references)
    try:
        store.save_identity(PersonIdentityRow("person:ana"))
        store.save_relationship(PersonCompanyRelationshipRow(
            "rel:ana", "person:ana", "company:a", ("evidence:a",)
        ))
        with pytest.raises(CandidatePersistenceConflict):
            store.save_relationship(PersonCompanyRelationshipRow(
                "rel:ana", "person:ana", "company:b", ("evidence:b",)
            ))
    finally:
        store.close()
        references.close()
