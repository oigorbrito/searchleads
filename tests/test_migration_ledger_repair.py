import sqlite3

from searchleads.persistence import SCHEMA_VERSION, SQLiteRepository


def create_incomplete_v2(path: str) -> None:
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
            payload_sha256 TEXT,
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
        INSERT INTO schema_meta(singleton, schema_version) VALUES (1, 2);
        """
    )
    connection.execute("PRAGMA user_version = 2")
    connection.commit()
    connection.close()


def ledger_versions(path: str) -> list[int]:
    connection = sqlite3.connect(path)
    rows = connection.execute(
        "SELECT version FROM schema_migrations ORDER BY version"
    ).fetchall()
    connection.close()
    return [int(row[0]) for row in rows]


def test_repair_of_v2_database_records_current_migration_version(tmp_path) -> None:
    path = str(tmp_path / "incomplete-v2.sqlite3")
    create_incomplete_v2(path)

    with SQLiteRepository(path):
        pass

    assert ledger_versions(path) == [SCHEMA_VERSION]


def test_reopening_repaired_database_does_not_duplicate_ledger_entry(tmp_path) -> None:
    path = str(tmp_path / "reopen-v2.sqlite3")
    create_incomplete_v2(path)

    with SQLiteRepository(path):
        pass
    first = ledger_versions(path)

    with SQLiteRepository(path):
        pass
    second = ledger_versions(path)

    assert first == [SCHEMA_VERSION]
    assert second == first
