import sqlite3
from datetime import datetime, timezone

import pytest

from searchleads.domain import Evidence, Source
from searchleads.persistence import EvidenceEnvelopeIntegrityError, SQLiteRepository


def test_existing_v3_column_with_missing_envelope_digest_fails_closed(tmp_path) -> None:
    path = str(tmp_path / "missing-envelope-digest-v3.sqlite3")
    source = Source("src-missing-digest", "website", "https://example.test")
    evidence = Evidence(
        "ev-missing-digest",
        source.source_id,
        "https://example.test/about",
        datetime(2026, 8, 29, 20, 0, tzinfo=timezone.utc),
        "raw payload",
        "upstream-digest",
        {"status": 200},
    )

    with SQLiteRepository(path) as repo:
        repo.save(source)
        repo.save(evidence)

    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE evidence_records SET envelope_sha256 = NULL WHERE evidence_id = ?",
        (evidence.evidence_id,),
    )
    connection.commit()
    connection.close()

    with pytest.raises(EvidenceEnvelopeIntegrityError, match="envelope storage digest is missing"):
        SQLiteRepository(path)


def test_failed_open_closes_the_connection_it_acquired(monkeypatch) -> None:
    import searchleads.persistence.sqlite as sqlite_module

    opened: list[sqlite3.Connection] = []
    real_connect = sqlite_module.sqlite3.connect

    def recording_connect(*args, **kwargs):
        connection = real_connect(*args, **kwargs)
        opened.append(connection)
        return connection

    def failing_schema(self) -> None:
        raise RuntimeError("forced schema failure")

    monkeypatch.setattr(sqlite_module.sqlite3, "connect", recording_connect)
    monkeypatch.setattr(SQLiteRepository, "_initialize_schema", failing_schema)

    with pytest.raises(RuntimeError, match="forced schema failure"):
        SQLiteRepository()

    assert len(opened) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        opened[0].execute("SELECT 1")
