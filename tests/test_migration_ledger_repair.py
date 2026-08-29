import sqlite3

from searchleads.persistence import SCHEMA_VERSION, SQLiteRepository


EXPECTED_LEDGER = [2, SCHEMA_VERSION]


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


def schema_versions(path: str) -> tuple[int, int]:
    connection = sqlite3.connect(path)
    meta_version = connection.execute(
        "SELECT schema_version FROM schema_meta WHERE singleton = 1"
    ).fetchone()[0]
    pragma_version = connection.execute("PRAGMA user_version").fetchone()[0]
    connection.close()
    return int(meta_version), int(pragma_version)


def test_fresh_public_repository_records_full_migration_chain(tmp_path) -> None:
    path = str(tmp_path / "fresh-v3.sqlite3")

    with SQLiteRepository(path):
        pass

    assert schema_versions(path) == (SCHEMA_VERSION, SCHEMA_VERSION)
    assert ledger_versions(path) == EXPECTED_LEDGER

    with SQLiteRepository(path):
        pass

    assert schema_versions(path) == (SCHEMA_VERSION, SCHEMA_VERSION)
    assert ledger_versions(path) == EXPECTED_LEDGER


def test_repair_of_v2_database_records_v2_and_v3_migration_versions(tmp_path) -> None:
    path = str(tmp_path / "incomplete-v2.sqlite3")
    create_incomplete_v2(path)

    with SQLiteRepository(path):
        pass

    assert ledger_versions(path) == EXPECTED_LEDGER


def test_reopening_repaired_database_does_not_duplicate_ledger_entries(tmp_path) -> None:
    path = str(tmp_path / "reopen-v2.sqlite3")
    create_incomplete_v2(path)

    with SQLiteRepository(path):
        pass
    first = ledger_versions(path)

    with SQLiteRepository(path):
        pass
    second = ledger_versions(path)

    assert first == EXPECTED_LEDGER
    assert second == first
