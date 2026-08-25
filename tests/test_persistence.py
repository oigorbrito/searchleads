from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

import pytest

from searchleads.domain import (
    CandidateFact,
    CanonicalFact,
    Company,
    Conflict,
    ConflictStatus,
    ContactKind,
    ContactPoint,
    ContactStatus,
    DecisionClass,
    Evidence,
    Lead,
    LeadStage,
    Person,
    Provenance,
    QualificationStatus,
    Source,
)
from searchleads.persistence import (
    SCHEMA_VERSION,
    EvidenceIntegrityError,
    PersistenceConflictError,
    PersistenceEncodingError,
    MissingReferenceError,
    SQLiteRepository,
    SchemaVersionError,
    decode_record,
    encode_record,
    raw_payload_sha256,
)

NOW = datetime(2026, 8, 24, 18, 30, tzinfo=timezone.utc)
LATER = datetime(2026, 8, 24, 18, 31, tzinfo=timezone.utc)


def sample_records() -> list[object]:
    return [
        Source("src-1", "website", "https://acme.example", "ACME"),
        Evidence(
            "ev-1",
            "src-1",
            "https://acme.example/about",
            NOW,
            "Razão social: ACME\nContato: olá@acme.example 🚀\x00fim",
            "upstream-digest-as-received",
            {"status": 200, "headers": {"content-type": "text/html"}, "attempts": (1, 2)},
        ),
        Provenance("prov-1", "company-1", "name", ("ev-1",), "structured-extraction", NOW, "parser-v1"),
        CandidateFact(
            "fact-1",
            "company-1",
            "name",
            {"text": " ACME LTDA. ", "tokens": ["ACME", "LTDA"]},
            "acme ltda",
            ("ev-1",),
            "prov-1",
            0.91,
            DecisionClass.LOCALLY_VERIFIED,
            NOW,
        ),
        CanonicalFact(
            "canon-1",
            "company-1",
            "name",
            "ACME LTDA.",
            ("fact-1",),
            "prov-1",
            "single-source provisional selection",
            DecisionClass.ENGINEERING_CHOICE,
        ),
        Conflict(
            "conf-1",
            "company-1",
            "industry",
            ("fact-1", "fact-2"),
            ConflictStatus.RESOLVED,
            "fact-1",
            "manual review",
        ),
        Company("company-1", ("fact-1",), ("canon-1",), ("person-1",), ("contact-1",)),
        Person("person-1", "company-1", ("ev-1",), ("fact-3",), ("canon-3",), ("contact-2",)),
        ContactPoint(
            "contact-1",
            "company-1",
            ContactKind.EMAIL,
            "ola@acme.example",
            ("ev-1",),
            ContactStatus.VALIDATED,
            NOW,
            ("ev-validation",),
            LATER,
        ),
        Lead(
            "lead-1",
            "company-1",
            LeadStage.QUALIFIED,
            QualificationStatus.QUALIFIED,
            ("future explicit rule",),
            NOW,
        ),
    ]


@pytest.mark.parametrize("record", sample_records(), ids=lambda value: type(value).__name__)
def test_codec_roundtrips_every_domain_record(record: object) -> None:
    assert decode_record(encode_record(record)) == record


def test_codec_is_deterministic() -> None:
    record = sample_records()[3]
    assert encode_record(record) == encode_record(record)


def test_codec_preserves_nested_mapping_tuple_list_and_unicode() -> None:
    evidence = sample_records()[1]
    restored = decode_record(encode_record(evidence))
    assert restored == evidence
    assert restored.metadata["attempts"] == (1, 2)
    assert "🚀" in restored.raw_payload


def test_codec_rejects_unsupported_record_type() -> None:
    with pytest.raises(PersistenceEncodingError):
        encode_record(object())


def test_codec_rejects_non_lossless_python_value() -> None:
    fact = CandidateFact("f", "c", "x", {1, 2}, "x", ("e",), "p", observed_at=NOW)
    with pytest.raises(PersistenceEncodingError):
        encode_record(fact)


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        json.dumps({"codec_version": 99, "record_type": "Source", "fields": {}}),
        json.dumps({"codec_version": 1, "record_type": "Nope", "fields": {}}),
        json.dumps({"codec_version": 1, "record_type": "Source", "fields": []}),
        json.dumps(
            {
                "codec_version": 1,
                "record_type": "Source",
                "fields": {"source_id": "", "source_type": "x", "locator": "x", "name": None},
            }
        ),
    ],
)
def test_codec_rejects_invalid_documents(payload: str) -> None:
    with pytest.raises(PersistenceEncodingError):
        decode_record(payload)


def test_raw_payload_sha256_is_stable_for_utf8_text() -> None:
    payload = "çã🚀\x00\n"
    assert raw_payload_sha256(payload) == raw_payload_sha256(payload)
    assert len(raw_payload_sha256(payload)) == 64


def persist_dependency_graph(repo: SQLiteRepository) -> list[object]:
    source = Source("src-1", "website", "https://acme.example", "ACME")
    evidence = Evidence("ev-1", "src-1", "https://acme.example/about", NOW, "raw")
    validation = Evidence("ev-validation", "src-1", "https://acme.example/check", LATER, "valid")
    company = Company("company-1")
    provenance = Provenance("prov-1", "company-1", "name", ("ev-1",), "extract", NOW)
    candidate1 = CandidateFact("fact-1", "company-1", "name", "ACME", "acme", ("ev-1",), "prov-1", observed_at=NOW)
    candidate2 = CandidateFact("fact-2", "company-1", "name", "ACME SA", "acme sa", ("ev-1",), "prov-1", observed_at=NOW)
    for item in (source, evidence, validation, company, provenance, candidate1, candidate2):
        repo.save(item)
    return [source, evidence, validation, company, provenance, candidate1, candidate2]


def test_repository_roundtrips_complete_reference_graph() -> None:
    with SQLiteRepository() as repo:
        persisted = persist_dependency_graph(repo)
        records = [
            CanonicalFact("canon-1", "company-1", "name", "ACME", ("fact-1",), "prov-1", "single"),
            Conflict("conf-1", "company-1", "name", ("fact-1", "fact-2")),
            Person("person-1", "company-1", ("ev-1",)),
            ContactPoint(
                "contact-1", "company-1", ContactKind.EMAIL, "a@b.com", ("ev-1",),
                ContactStatus.VALIDATED, NOW, ("ev-validation",), LATER
            ),
            Lead("lead-1", "company-1"),
        ]
        for item in records:
            assert repo.save(item) is True
        for item in persisted + records:
            restored = repo.load(type(item), repo._record_id(item))
            assert restored == item


def test_repository_same_record_is_idempotent() -> None:
    source = Source("src-1", "website", "https://acme.example")
    with SQLiteRepository() as repo:
        assert repo.save(source) is True
        assert repo.save(source) is False


def test_repository_rejects_same_id_with_changed_content() -> None:
    with SQLiteRepository() as repo:
        repo.save(Source("src-1", "website", "https://acme.example"))
        with pytest.raises(PersistenceConflictError):
            repo.save(Source("src-1", "registry", "https://registry.example"))


def test_evidence_same_id_changed_raw_payload_is_conflict() -> None:
    first = Evidence("ev", "src", "x", NOW, "raw-one")
    second = Evidence("ev", "src", "x", NOW, "raw-two")
    with SQLiteRepository() as repo:
        repo.save(Source("src", "website", "x"))
        repo.save(first)
        with pytest.raises(PersistenceConflictError):
            repo.save(second)


def test_missing_record_returns_none() -> None:
    with SQLiteRepository() as repo:
        assert repo.load(Source, "missing") is None
        assert repo.load_evidence("missing") is None
        assert repo.raw_evidence_bytes("missing") is None


def test_evidence_raw_payload_is_preserved_as_exact_utf8_bytes() -> None:
    payload = "linha 1\r\nlinha 2 — çã 🚀\x00fim"
    evidence = Evidence("ev", "src", "x", NOW, payload)
    with SQLiteRepository() as repo:
        repo.save(Source("src", "website", "x"))
        repo.save(evidence)
        assert repo.raw_evidence_bytes("ev") == payload.encode("utf-8")
        assert repo.load_evidence("ev").raw_payload == payload


def test_evidence_without_raw_payload_roundtrips_none() -> None:
    evidence = Evidence("ev", "src", "x", NOW, None, "upstream", {"status": 204})
    with SQLiteRepository() as repo:
        repo.save(Source("src", "website", "x"))
        repo.save(evidence)
        assert repo.raw_evidence_bytes("ev") is None
        assert repo.load_evidence("ev") == evidence


def test_domain_content_digest_is_not_rewritten_by_storage_digest() -> None:
    evidence = Evidence("ev", "src", "x", NOW, "raw", "not-sha256-upstream-format")
    with SQLiteRepository() as repo:
        repo.save(Source("src", "website", "x"))
        repo.save(evidence)
        assert repo.load_evidence("ev").content_digest == "not-sha256-upstream-format"


def test_reprocessing_iterates_in_capture_order_and_can_filter_source() -> None:
    records = [
        Evidence("b", "src-a", "b", LATER, "B"),
        Evidence("a", "src-a", "a", NOW, "A"),
        Evidence("c", "src-b", "c", NOW, "C"),
    ]
    with SQLiteRepository() as repo:
        repo.save(Source("src-a", "website", "a"))
        repo.save(Source("src-b", "website", "b"))
        for record in records:
            repo.save(record)
        assert [item.evidence_id for item in repo.iter_evidence()] == ["a", "c", "b"]
        assert [item.raw_payload for item in repo.iter_evidence("src-a")] == ["A", "B"]


def test_database_reopen_preserves_records_and_raw_evidence(tmp_path) -> None:
    path = tmp_path / "searchleads.sqlite3"
    evidence = Evidence("ev", "src", "x", NOW, "payload 🚀", metadata={"status": 200})
    company = Company("company-1", ("fact-1",))
    with SQLiteRepository(path) as repo:
        repo.save(Source("src", "website", "x"))
        repo.save(evidence)
        repo.save(company)
    with SQLiteRepository(path) as repo:
        assert repo.load_evidence("ev") == evidence
        assert repo.load(Company, "company-1") == company


def test_schema_version_is_persisted(tmp_path) -> None:
    path = tmp_path / "schema.sqlite3"
    with SQLiteRepository(path):
        pass
    connection = sqlite3.connect(path)
    version = connection.execute("SELECT schema_version FROM schema_meta WHERE singleton = 1").fetchone()[0]
    connection.close()
    assert version == SCHEMA_VERSION


def test_unsupported_schema_version_is_rejected(tmp_path) -> None:
    path = tmp_path / "future.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE schema_meta (singleton INTEGER PRIMARY KEY, schema_version INTEGER NOT NULL)")
    connection.execute("INSERT INTO schema_meta VALUES (1, ?)", (SCHEMA_VERSION + 1,))
    connection.commit()
    connection.close()
    with pytest.raises(SchemaVersionError):
        SQLiteRepository(path)


def test_storage_detects_corrupted_raw_payload(tmp_path) -> None:
    path = tmp_path / "corrupt.sqlite3"
    with SQLiteRepository(path) as repo:
        repo.save(Source("src", "website", "x"))
        repo.save(Evidence("ev", "src", "x", NOW, "original"))
    connection = sqlite3.connect(path)
    connection.execute("UPDATE evidence_records SET raw_payload = ? WHERE evidence_id = ?", (b"tampered", "ev"))
    connection.commit()
    connection.close()
    with SQLiteRepository(path) as repo:
        with pytest.raises(EvidenceIntegrityError):
            repo.load_evidence("ev")


def test_storage_detects_invalid_utf8_raw_payload(tmp_path) -> None:
    path = tmp_path / "invalid-utf8.sqlite3"
    with SQLiteRepository(path) as repo:
        repo.save(Source("src", "website", "x"))
        repo.save(Evidence("ev", "src", "x", NOW, "original"))
    connection = sqlite3.connect(path)
    connection.execute("UPDATE evidence_records SET raw_payload = ? WHERE evidence_id = ?", (b"\xff", "ev"))
    connection.commit()
    connection.close()
    with SQLiteRepository(path) as repo:
        with pytest.raises(EvidenceIntegrityError):
            repo.raw_evidence_bytes("ev")


def test_storage_detects_digest_without_raw_payload(tmp_path) -> None:
    path = tmp_path / "digest-only.sqlite3"
    with SQLiteRepository(path) as repo:
        repo.save(Source("src", "website", "x"))
        repo.save(Evidence("ev", "src", "x", NOW, None))
    connection = sqlite3.connect(path)
    connection.execute("UPDATE evidence_records SET raw_payload_sha256 = ? WHERE evidence_id = ?", ("abc", "ev"))
    connection.commit()
    connection.close()
    with SQLiteRepository(path) as repo:
        with pytest.raises(EvidenceIntegrityError):
            repo.load_evidence("ev")


def test_load_rejects_unsupported_requested_type() -> None:
    with SQLiteRepository() as repo:
        with pytest.raises(PersistenceEncodingError):
            repo.load(dict, "x")


def test_codec_preserves_enum_identity_not_only_string_equality() -> None:
    records = sample_records()
    candidate = decode_record(encode_record(records[3]))
    conflict = decode_record(encode_record(records[5]))
    contact = decode_record(encode_record(records[8]))
    lead = decode_record(encode_record(records[9]))
    assert candidate.decision_class is DecisionClass.LOCALLY_VERIFIED
    assert conflict.status is ConflictStatus.RESOLVED
    assert contact.kind is ContactKind.EMAIL
    assert contact.status is ContactStatus.VALIDATED
    assert lead.stage is LeadStage.QUALIFIED
    assert lead.qualification_status is QualificationStatus.QUALIFIED


@pytest.mark.parametrize(
    "encoded",
    [
        {"__searchleads_type__": "enum", "enum_type": "UnknownEnum", "value": "X"},
        {"__searchleads_type__": "unknown-tag", "value": "X"},
    ],
)
def test_codec_rejects_unknown_nested_types(encoded: dict[str, object]) -> None:
    payload = json.dumps(
        {
            "codec_version": 1,
            "record_type": "Source",
            "fields": {
                "source_id": "src",
                "source_type": encoded,
                "locator": "x",
                "name": None,
            },
        }
    )
    with pytest.raises(PersistenceEncodingError):
        decode_record(payload)


def test_repository_save_rejects_unsupported_record() -> None:
    with SQLiteRepository() as repo:
        with pytest.raises(PersistenceEncodingError):
            repo.save(object())


def test_evidence_same_record_is_idempotent() -> None:
    evidence = Evidence("ev", "src", "x", NOW, "raw")
    with SQLiteRepository() as repo:
        repo.save(Source("src", "website", "x"))
        assert repo.save(evidence) is True
        assert repo.save(evidence) is False


def test_load_detects_corrupted_record_type_envelope(tmp_path) -> None:
    path = tmp_path / "wrong-record-type.sqlite3"
    with SQLiteRepository(path) as repo:
        repo.save(Source("src", "website", "x"))
    connection = sqlite3.connect(path)
    wrong_payload = encode_record(Company("company-1"))
    connection.execute(
        "UPDATE domain_records SET payload_json = ? WHERE record_type = ? AND record_id = ?",
        (wrong_payload, "Source", "src"),
    )
    connection.commit()
    connection.close()
    with SQLiteRepository(path) as repo:
        with pytest.raises(PersistenceEncodingError):
            repo.load(Source, "src")


def test_load_evidence_detects_wrong_envelope_type(tmp_path) -> None:
    path = tmp_path / "wrong-evidence-envelope.sqlite3"
    with SQLiteRepository(path) as repo:
        repo.save(Source("src", "website", "x"))
        repo.save(Evidence("ev", "src", "x", NOW, "raw"))
    connection = sqlite3.connect(path)
    wrong_payload = encode_record(Source("src", "website", "x"))
    connection.execute(
        "UPDATE evidence_records SET envelope_json = ? WHERE evidence_id = ?",
        (wrong_payload, "ev"),
    )
    connection.commit()
    connection.close()
    with SQLiteRepository(path) as repo:
        with pytest.raises(PersistenceEncodingError):
            repo.load_evidence("ev")


def test_codec_roundtrips_bytes_inside_any_fields() -> None:
    fact = CandidateFact(
        "bytes-fact", "company", "artifact", b"\x00\xffraw", {"blob": b"\x01\x02"},
        ("ev",), "prov", observed_at=NOW
    )
    restored = decode_record(encode_record(fact))
    assert restored.raw_value == b"\x00\xffraw"
    assert restored.normalized_value["blob"] == b"\x01\x02"


def test_codec_rejects_invalid_base64_bytes_value() -> None:
    payload = json.dumps(
        {
            "codec_version": 1,
            "record_type": "Source",
            "fields": {
                "source_id": "src",
                "source_type": {"__searchleads_type__": "bytes", "base64": "%%%"},
                "locator": "x",
                "name": None,
            },
        }
    )
    with pytest.raises(PersistenceEncodingError):
        decode_record(payload)


@pytest.mark.parametrize(
    "record",
    [
        Evidence("ev", "missing-source", "x", NOW, "raw"),
        Provenance("prov", "company", "name", ("missing-ev",), "extract", NOW),
        CandidateFact("fact", "company", "name", "A", "a", ("missing-ev",), "missing-prov", observed_at=NOW),
        CanonicalFact("canon", "company", "name", "A", ("missing-fact",), "missing-prov", "single"),
        Conflict("conf", "company", "name", ("missing-a", "missing-b")),
        Person("person", "missing-company", ("missing-ev",)),
        ContactPoint("contact", "missing-owner", ContactKind.EMAIL, "a@b.com", ("missing-ev",)),
        Lead("lead", "missing-company"),
    ],
    ids=lambda value: type(value).__name__,
)
def test_repository_rejects_missing_references(record: object) -> None:
    with SQLiteRepository() as repo:
        with pytest.raises(MissingReferenceError):
            repo.save(record)


def test_contact_accepts_person_owner_when_dependencies_exist() -> None:
    with SQLiteRepository() as repo:
        repo.save(Source("src", "website", "x"))
        repo.save(Evidence("ev", "src", "x", NOW, "raw"))
        repo.save(Company("company"))
        repo.save(Person("person", "company", ("ev",)))
        contact = ContactPoint("contact", "person", ContactKind.EMAIL, "a@b.com", ("ev",))
        assert repo.save(contact) is True
        assert repo.load(ContactPoint, "contact") == contact


def test_company_aggregate_reference_snapshots_do_not_create_insertion_cycle() -> None:
    company = Company("company", ("future-fact",), ("future-canon",), ("future-person",), ("future-contact",))
    with SQLiteRepository() as repo:
        assert repo.save(company) is True
        assert repo.load(Company, "company") == company
