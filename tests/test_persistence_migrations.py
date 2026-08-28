from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from searchleads.domain import Evidence, Source
from searchleads.persistence import (
    SCHEMA_VERSION,
    DomainRecordIntegrityError,
    SQLiteRepository,
    SchemaVersionError,
    encode_record,
    raw_payload_sha256,
)

NOW = datetime(2026, 8, 24, 18, 30, tzinfo=timezone.utc)


def _create_v1_database(path: str) -> tuple[Source, Evidence, bytes]:
    source = Source("src-legacy", "website", "https://legacy.example", "Legacy")
    evidence = Evidence(
        "ev-legacy",
        source.source_id,
        "https://legacy.example/about",
        NOW,
        "linha 1\r\nlinha 2 — çã 🚀\x00fim",
        "upstream-digest",
        {"status": 200},
    )
    raw_bytes = evidence.raw_payload.encode("utf-8")
    envelope = encode_record(replace(evidence, raw_payload=None))

    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE schema_meta (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            schema_version INTEGER NOT NULL
        );
        CREATE TABLE domain_records (
            record_type TEXT NOT NULL,
            record_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (record_type, record_id)
        );
        CREATE TABLE evidence_records (
            evidence_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            captured_at TEXT NOT NULL,
            envelope_json TEXT NOT NULL,
            raw_payload BLOB,
            raw_payload_sha256 TEXT
        );
        CREATE INDEX idx_evidence_source_capture
            ON evidence_records (source_id, captured_at, evidence_id);
        INSERT INTO schema_meta(singleton, schema_version) VALUES (1, 1);
        """
    )
    connection.execute(
        "INSERT INTO domain_records(record_type, record_id, payload_json) VALUES (?, ?, ?)",
        ("Source", source.source_id, encode_record(source)),
    )
    connection.execute(
        """INSERT INTO evidence_records(
               evidence_id, source_id, captured_at, envelope_json, raw_payload, raw_payload_sha256
           ) VALUES (?, ?, ?, ?, ?, ?)""",
        (
            evidence.evidence_id,
            evidence.source_id,
            evidence.captured_at.isoformat(),
            envelope,
            raw_bytes,
            raw_payload_sha256(evidence.raw_payload),
        ),
    )
    connection.commit()
    connection.close()
    return source, evidence, raw_bytes


def _schema_versions(path: str) -> tuple[int, int]:
    connection = sqlite3.connect(path)
    meta = connection.execute(
        "SELECT schema_version FROM schema_meta WHERE singleton = 1"
    ).fetchone()[0]
    pragma = connection.execute("PRAGMA user_version").fetchone()[0]
    connection.close()
    return int(meta), int(pragma)


def test_v1_database_auto_migrates_without_changing_legacy_rows_or_raw_evidence(tmp_path) -> None:
    path = str(tmp_path / "legacy-v1.sqlite3")
    source, evidence, raw_before = _create_v1_database(path)

    connection = sqlite3.connect(path)
    source_payload_before = connection.execute(
        "SELECT payload_json FROM domain_records WHERE record_type = 'Source' AND record_id = ?",
        (source.source_id,),
    ).fetchone()[0]
    evidence_row_before = connection.execute(
        """SELECT envelope_json, raw_payload, raw_payload_sha256
           FROM evidence_records WHERE evidence_id = ?""",
        (evidence.evidence_id,),
    ).fetchone()
    connection.close()

    with SQLiteRepository(path) as repo:
        assert repo.load(Source, source.source_id) == source
        assert repo.load_evidence(evidence.evidence_id) == evidence
        assert repo.raw_evidence_bytes(evidence.evidence_id) == raw_before

    assert _schema_versions(path) == (SCHEMA_VERSION, SCHEMA_VERSION)

    connection = sqlite3.connect(path)
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(domain_records)")
    }
    source_payload_after, source_digest = connection.execute(
        """SELECT payload_json, payload_sha256 FROM domain_records
           WHERE record_type = 'Source' AND record_id = ?""",
        (source.source_id,),
    ).fetchone()
    evidence_row_after = connection.execute(
        """SELECT envelope_json, raw_payload, raw_payload_sha256
           FROM evidence_records WHERE evidence_id = ?""",
        (evidence.evidence_id,),
    ).fetchone()
    migrations = connection.execute(
        "SELECT version FROM schema_migrations ORDER BY version"
    ).fetchall()
    connection.close()

    assert "payload_sha256" in columns
    assert source_payload_after == source_payload_before
    assert source_digest == hashlib.sha256(source_payload_before.encode("utf-8")).hexdigest()
    assert bytes(evidence_row_after[1]) == raw_before
    assert evidence_row_after == evidence_row_before
    assert migrations == [(2,)]


def test_reopening_migrated_database_is_idempotent(tmp_path) -> None:
    path = str(tmp_path / "legacy-reopen.sqlite3")
    source, evidence, raw_before = _create_v1_database(path)

    with SQLiteRepository(path):
        pass

    connection = sqlite3.connect(path)
    snapshot_before = (
        connection.execute("SELECT * FROM domain_records").fetchall(),
        connection.execute("SELECT * FROM evidence_records").fetchall(),
        connection.execute("SELECT * FROM schema_migrations").fetchall(),
    )
    connection.close()

    with SQLiteRepository(path) as repo:
        assert repo.load(Source, source.source_id) == source
        assert repo.load_evidence(evidence.evidence_id) == evidence
        assert repo.raw_evidence_bytes(evidence.evidence_id) == raw_before

    connection = sqlite3.connect(path)
    snapshot_after = (
        connection.execute("SELECT * FROM domain_records").fetchall(),
        connection.execute("SELECT * FROM evidence_records").fetchall(),
        connection.execute("SELECT * FROM schema_migrations").fetchall(),
    )
    connection.close()

    assert snapshot_after == snapshot_before
    assert _schema_versions(path) == (SCHEMA_VERSION, SCHEMA_VERSION)


def test_v2_marker_with_incomplete_additive_shape_is_repaired(tmp_path) -> None:
    path = str(tmp_path / "incomplete-v2.sqlite3")
    source, _, _ = _create_v1_database(path)

    connection = sqlite3.connect(path)
    connection.execute("UPDATE schema_meta SET schema_version = 2 WHERE singleton = 1")
    connection.execute("PRAGMA user_version = 2")
    connection.commit()
    connection.close()

    with SQLiteRepository(path) as repo:
        assert repo.load(Source, source.source_id) == source

    connection = sqlite3.connect(path)
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(domain_records)")
    }
    digest = connection.execute(
        "SELECT payload_sha256 FROM domain_records WHERE record_id = ?",
        (source.source_id,),
    ).fetchone()[0]
    connection.close()

    assert "payload_sha256" in columns
    assert digest is not None


def test_future_schema_version_still_fails_closed(tmp_path) -> None:
    path = str(tmp_path / "future.sqlite3")
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE schema_meta (singleton INTEGER PRIMARY KEY, schema_version INTEGER NOT NULL)"
    )
    connection.execute("INSERT INTO schema_meta VALUES (1, ?)", (SCHEMA_VERSION + 1,))
    connection.commit()
    connection.close()

    with pytest.raises(SchemaVersionError, match="newer than supported"):
        SQLiteRepository(path)


def test_nonzero_schema_markers_that_disagree_fail_closed(tmp_path) -> None:
    path = str(tmp_path / "marker-disagreement.sqlite3")
    _create_v1_database(path)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA user_version = 2")
    connection.commit()
    connection.close()

    with pytest.raises(SchemaVersionError, match="markers disagree"):
        SQLiteRepository(path)


def test_domain_record_payload_tampering_is_detected_after_v2(tmp_path) -> None:
    path = str(tmp_path / "domain-integrity.sqlite3")
    source = Source("src", "website", "https://example.test")
    with SQLiteRepository(path) as repo:
        repo.save(source)

    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE domain_records SET payload_json = ? WHERE record_type = 'Source' AND record_id = ?",
        (encode_record(Source("src", "registry", "https://tampered.test")), source.source_id),
    )
    connection.commit()
    connection.close()

    with SQLiteRepository(path) as repo:
        with pytest.raises(DomainRecordIntegrityError, match="storage digest mismatch"):
            repo.load(Source, source.source_id)
