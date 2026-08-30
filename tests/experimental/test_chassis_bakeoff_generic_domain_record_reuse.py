from __future__ import annotations

from dataclasses import dataclass

import pytest

from searchleads.domain import Company, Evidence, Source
from searchleads.persistence import MissingReferenceError, SQLiteRepository
import searchleads.persistence.sqlite as sqlite_layer


@dataclass(frozen=True, slots=True)
class PersonIdentityCandidateRecord:
    person_id: str


@dataclass(frozen=True, slots=True)
class PersonCompanyRelationshipCandidateRecord:
    relationship_id: str
    person_id: str
    company_id: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProfessionalRegistrationCandidateRecord:
    registration_id: str
    person_id: str
    authority: str
    number: str
    jurisdiction: str
    status: str
    evidence_ids: tuple[str, ...]


class CandidateRepository(SQLiteRepository):
    def _assert_references(self, record) -> None:
        context = f"{type(record).__name__} {self._record_id(record)!r}"
        if isinstance(record, PersonIdentityCandidateRecord):
            return
        if isinstance(record, PersonCompanyRelationshipCandidateRecord):
            self._require(PersonIdentityCandidateRecord, record.person_id, context)
            self._require(Company, record.company_id, context)
            self._require_evidence(record.evidence_ids, context)
            return
        if isinstance(record, ProfessionalRegistrationCandidateRecord):
            self._require(PersonIdentityCandidateRecord, record.person_id, context)
            self._require_evidence(record.evidence_ids, context)
            return
        super()._assert_references(record)


def _register_candidate_record_types(monkeypatch: pytest.MonkeyPatch) -> None:
    for record_type, id_field in (
        (PersonIdentityCandidateRecord, "person_id"),
        (PersonCompanyRelationshipCandidateRecord, "relationship_id"),
        (ProfessionalRegistrationCandidateRecord, "registration_id"),
    ):
        monkeypatch.setitem(sqlite_layer._ID_FIELDS, record_type, id_field)
        monkeypatch.setitem(sqlite_layer._RECORD_TYPES, record_type.__name__, record_type)


def _seed(repository: SQLiteRepository) -> None:
    source = Source("source:official", "official_web", "https://official.example/")
    evidence_relationship = Evidence(
        "evidence:relationship",
        source.source_id,
        "https://official.example/team",
        raw_payload="Ana Silva - Finance Director",
    )
    evidence_registration = Evidence(
        "evidence:registration",
        source.source_id,
        "https://official.example/cro",
        raw_payload="CRO-SP 12345 VERIFIED_ACTIVE",
    )
    repository.save(source)
    repository.save(evidence_relationship)
    repository.save(evidence_registration)
    repository.save(Company("company:a"))


def test_candidate_relational_records_reuse_current_generic_domain_table(monkeypatch: pytest.MonkeyPatch) -> None:
    _register_candidate_record_types(monkeypatch)
    with CandidateRepository() as repository:
        _seed(repository)
        version_before = int(repository._connection.execute("PRAGMA user_version").fetchone()[0])
        tables_before = {
            row[0]
            for row in repository._connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        }

        identity = PersonIdentityCandidateRecord("person:ana")
        relationship = PersonCompanyRelationshipCandidateRecord(
            "relationship:ana:a",
            identity.person_id,
            "company:a",
            ("evidence:relationship",),
        )
        registration = ProfessionalRegistrationCandidateRecord(
            "registration:cro-sp:12345",
            identity.person_id,
            "CRO-SP",
            "12345",
            "SP",
            "VERIFIED_ACTIVE",
            ("evidence:registration",),
        )

        assert repository.save(identity) is True
        assert repository.save(relationship) is True
        assert repository.save(registration) is True
        assert repository.load(PersonIdentityCandidateRecord, identity.person_id) == identity
        assert repository.load(PersonCompanyRelationshipCandidateRecord, relationship.relationship_id) == relationship
        assert repository.load(ProfessionalRegistrationCandidateRecord, registration.registration_id) == registration

        version_after = int(repository._connection.execute("PRAGMA user_version").fetchone()[0])
        tables_after = {
            row[0]
            for row in repository._connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        }
        assert version_before == version_after == 3
        assert tables_before == tables_after
        rows = repository._connection.execute(
            """SELECT record_type, COUNT(*) AS n FROM domain_records
               WHERE record_type IN (?, ?, ?)
               GROUP BY record_type ORDER BY record_type""",
            tuple(sorted((
                PersonIdentityCandidateRecord.__name__,
                PersonCompanyRelationshipCandidateRecord.__name__,
                ProfessionalRegistrationCandidateRecord.__name__,
            ))),
        ).fetchall()
        assert sum(int(row["n"]) for row in rows) == 3

        print("GENERIC_DOMAIN_RECORD_REUSE_EXECUTABLE_V1")
        print("schema_version_before=3")
        print("schema_version_after=3")
        print("new_physical_tables=0")
        print("candidate_record_types_persisted=3")
        print("codec_registry_extension_required=YES")
        print("semantic_reference_extension_required=YES")


def test_candidate_relationship_reuses_existing_reference_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    _register_candidate_record_types(monkeypatch)
    with CandidateRepository() as repository:
        _seed(repository)
        identity = PersonIdentityCandidateRecord("person:ana")
        repository.save(identity)

        with pytest.raises(MissingReferenceError, match="Evidence"):
            repository.save(PersonCompanyRelationshipCandidateRecord(
                "relationship:missing-evidence",
                identity.person_id,
                "company:a",
                ("evidence:missing",),
            ))
        with pytest.raises(MissingReferenceError, match="Company"):
            repository.save(PersonCompanyRelationshipCandidateRecord(
                "relationship:missing-company",
                identity.person_id,
                "company:missing",
                ("evidence:relationship",),
            ))
        with pytest.raises(MissingReferenceError, match="PersonIdentityCandidateRecord"):
            repository.save(ProfessionalRegistrationCandidateRecord(
                "registration:missing-person",
                "person:missing",
                "CRO-SP",
                "12345",
                "SP",
                "PENDING",
                ("evidence:registration",),
            ))
