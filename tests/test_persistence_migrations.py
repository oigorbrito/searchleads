import hashlib
import sqlite3

import pytest

from searchleads.domain import Evidence
from searchleads.persistence import CURRENT_SCHEMA_VERSION, SQLiteStore


REQUIRED_TABLES = {
    "sources",
    "evidence",
    "companies",
    "candidate_facts",
    "canonical_facts",
    "people",
    "professional_roles",
    "contacts",
    "contact_validations",
    "normalizations",
    "leads",
    "review_cases",
}


def _create_legacy_wu2_database(path) -> tuple[bytes, str]:  # type: ignore[no-untyped-def]
    raw = b"legacy immutable evidence\x00payload"
    digest = hashlib.sha256(raw).hexdigest()
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        PRAGMA user_version = 1;

        CREATE TABLE sources (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            locator TEXT NOT NULL
        );

        CREATE TABLE evidence (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            raw_content BLOB NOT NULL,
            sha256 TEXT NOT NULL,
            retrieved_at TEXT
        );

        CREATE TABLE companies (
            id TEXT PRIMARY KEY,
            legal_name TEXT
        );

        CREATE TABLE candidate_facts (
            id TEXT PRIMARY KEY,
            subject_type TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            field_name TEXT NOT NULL,
            value_json TEXT NOT NULL,
            evidence_id TEXT NOT NULL
        );

        CREATE TABLE canonical_facts (
            id TEXT PRIMARY KEY,
            subject_type TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            field_name TEXT NOT NULL,
            value_json TEXT NOT NULL
        );

        CREATE TABLE people (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE TABLE contacts (
            id TEXT PRIMARY KEY,
            owner_type TEXT NOT NULL,
            owner_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            value TEXT NOT NULL
        );
        """
    )
    connection.execute(
        "INSERT INTO sources VALUES (?, ?, ?, ?)",
        ("source-legacy", "Legacy Source", "fixture", "legacy://source"),
    )
    connection.execute(
        "INSERT INTO evidence VALUES (?, ?, ?, ?, ?)",
        ("evidence-legacy", "source-legacy", raw, digest, "2026-01-01T00:00:00Z"),
    )
    connection.execute(
        "INSERT INTO companies VALUES (?, ?)",
        ("company-legacy", "Legacy Company"),
    )
    connection.execute(
        "INSERT INTO people VALUES (?, ?)",
        ("person-legacy", "Legacy Person"),
    )
    connection.execute(
        "INSERT INTO contacts VALUES (?, ?, ?, ?, ?)",
        ("contact-legacy", "company", "company-legacy", "email", "info@example.com"),
    )
    connection.commit()
    connection.close()
    return raw, digest


def test_legacy_wu2_database_auto_migrates_without_data_loss(tmp_path) -> None:
    path = tmp_path / "legacy.sqlite3"
    raw, digest = _create_legacy_wu2_database(path)

    with SQLiteStore(path) as store:
        assert store.schema_version == CURRENT_SCHEMA_VERSION
        tables = {
            row[0]
            for row in store.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert REQUIRED_TABLES <= tables
        assert "evidence_id" in store.columns("people")
        assert {"evidence_id", "discovery_rule"} <= store.columns("contacts")
        assert "supporting_candidate_fact_ids" in store.columns("canonical_facts")

        company = store.connection.execute(
            "SELECT legal_name FROM companies WHERE id = 'company-legacy'"
        ).fetchone()
        assert company[0] == "Legacy Company"

        migrated_evidence = store.get_evidence("evidence-legacy")
        assert migrated_evidence is not None
        assert migrated_evidence.raw_content == raw
        assert migrated_evidence.sha256 == digest


def test_reopen_is_idempotent_and_raw_evidence_unchanged(tmp_path) -> None:
    path = tmp_path / "legacy.sqlite3"
    raw, digest = _create_legacy_wu2_database(path)

    with SQLiteStore(path) as first:
        first_schema = {
            table: first.columns(table)
            for table in REQUIRED_TABLES
        }
        first_evidence = first.get_evidence("evidence-legacy")
        assert first_evidence is not None

    with SQLiteStore(path) as second:
        second_schema = {
            table: second.columns(table)
            for table in REQUIRED_TABLES
        }
        second_evidence = second.get_evidence("evidence-legacy")
        assert second_evidence is not None
        assert second.schema_version == CURRENT_SCHEMA_VERSION

    assert second_schema == first_schema
    assert first_evidence.raw_content == second_evidence.raw_content == raw
    assert first_evidence.sha256 == second_evidence.sha256 == digest


def test_existing_evidence_cannot_be_replaced(tmp_path) -> None:
    path = tmp_path / "store.sqlite3"
    raw = b"original"
    digest = hashlib.sha256(raw).hexdigest()

    with SQLiteStore(path) as store:
        store.connection.execute(
            "INSERT INTO sources (id, name, kind, locator) VALUES (?, ?, ?, ?)",
            ("source-1", "Source", "fixture", "fixture://source"),
        )
        store.connection.commit()
        store.put_evidence(
            Evidence(
                id="evidence-1",
                source_id="source-1",
                raw_content=raw,
                sha256=digest,
            )
        )

        with pytest.raises(ValueError, match="immutable"):
            store.put_evidence(
                Evidence(
                    id="evidence-1",
                    source_id="source-1",
                    raw_content=b"changed",
                    sha256=hashlib.sha256(b"changed").hexdigest(),
                )
            )

        stored = store.get_evidence("evidence-1")
        assert stored is not None
        assert stored.raw_content == raw
        assert stored.sha256 == digest


def test_current_version_repairs_historically_incomplete_schema(tmp_path) -> None:
    path = tmp_path / "misversioned.sqlite3"
    connection = sqlite3.connect(path)
    connection.executescript(
        f"""
        PRAGMA user_version = {CURRENT_SCHEMA_VERSION};
        CREATE TABLE people (id TEXT PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE contacts (
            id TEXT PRIMARY KEY,
            owner_type TEXT NOT NULL,
            owner_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            value TEXT NOT NULL
        );
        """
    )
    connection.close()

    with SQLiteStore(path) as store:
        assert "evidence_id" in store.columns("people")
        assert {"evidence_id", "discovery_rule"} <= store.columns("contacts")
        assert REQUIRED_TABLES <= {
            row[0]
            for row in store.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
