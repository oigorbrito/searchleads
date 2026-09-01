import hashlib
import sqlite3
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from searchleads.domain import Evidence, Source
from searchleads.persistence import (
    SCHEMA_VERSION,
    EvidenceEnvelopeIntegrityError,
    SQLiteRepository,
    encode_record,
)
from searchleads.persistence.ledger import SQLiteRepository as V2SQLiteRepository


NOW = datetime(2026, 8, 29, 18, 0, tzinfo=timezone.utc)


def sample_records() -> tuple[Source, Evidence]:
    source = Source("src-v3", "website", "https://example.test")
    evidence = Evidence(
        "ev-v3",
        source.source_id,
        "https://example.test/about",
        NOW,
        "raw payload — ç",
        "upstream-content-digest",
        {"status": 200, "method": "GET"},
    )
    return source, evidence


def test_v2_database_migrates_to_v3_without_rewriting_evidence_content(tmp_path) -> None:
    path = str(tmp_path / "legacy-v2.sqlite3")
    source, evidence = sample_records()

    with V2SQLiteRepository(path) as repo:
        repo.save(source)
        repo.save(evidence)

    connection = sqlite3.connect(path)
    before = connection.execute(
        """SELECT envelope_json, raw_payload, raw_payload_sha256
           FROM evidence_records WHERE evidence_id = ?""",
        (evidence.evidence_id,),
    ).fetchone()
    connection.close()

    with SQLiteRepository(path) as repo:
        assert repo.load_evidence(evidence.evidence_id) == evidence

    connection = sqlite3.connect(path)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(evidence_records)")}
    after = connection.execute(
        """SELECT envelope_json, raw_payload, raw_payload_sha256, envelope_sha256
           FROM evidence_records WHERE evidence_id = ?""",
        (evidence.evidence_id,),
    ).fetchone()
    meta_version = connection.execute(
        "SELECT schema_version FROM schema_meta WHERE singleton = 1"
    ).fetchone()[0]
    pragma_version = connection.execute("PRAGMA user_version").fetchone()[0]
    ledger = connection.execute(
        "SELECT version FROM schema_migrations ORDER BY version"
    ).fetchall()
    connection.close()

    assert SCHEMA_VERSION == 3
    assert "envelope_sha256" in columns
    assert after[:3] == before
    assert after[3] == hashlib.sha256(before[0].encode("utf-8")).hexdigest()
    assert (meta_version, pragma_version) == (3, 3)
    assert ledger == [(2,), (3,)]


@pytest.mark.parametrize(
    "mutated",
    [
        lambda evidence: replace(evidence, locator="https://evil.test/changed"),
        lambda evidence: replace(evidence, content_digest="tampered-upstream-digest"),
        lambda evidence: replace(evidence, metadata={"status": 200, "tampered": True}),
    ],
)
def test_v3_detects_tampering_in_envelope_only_fields(tmp_path, mutated) -> None:
    path = str(tmp_path / "tampered-envelope.sqlite3")
    source, evidence = sample_records()

    with SQLiteRepository(path) as repo:
        repo.save(source)
        repo.save(evidence)

    tampered_envelope = encode_record(replace(mutated(evidence), raw_payload=None))
    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE evidence_records SET envelope_json = ? WHERE evidence_id = ?",
        (tampered_envelope, evidence.evidence_id),
    )
    connection.commit()
    connection.close()

    with SQLiteRepository(path) as repo:
        with pytest.raises(EvidenceEnvelopeIntegrityError, match="envelope storage digest mismatch"):
            repo.load_evidence(evidence.evidence_id)


def test_idempotent_save_does_not_silently_repair_tampered_envelope_digest(tmp_path) -> None:
    path = str(tmp_path / "tampered-digest.sqlite3")
    source, evidence = sample_records()

    with SQLiteRepository(path) as repo:
        repo.save(source)
        repo.save(evidence)

    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE evidence_records SET envelope_sha256 = ? WHERE evidence_id = ?",
        ("0" * 64, evidence.evidence_id),
    )
    connection.commit()
    connection.close()

    with SQLiteRepository(path) as repo:
        with pytest.raises(EvidenceEnvelopeIntegrityError, match="envelope storage digest mismatch"):
            repo.save(evidence)


def test_v3_marker_with_missing_envelope_digest_shape_is_repaired(tmp_path) -> None:
    path = str(tmp_path / "incomplete-v3.sqlite3")
    source, evidence = sample_records()

    with V2SQLiteRepository(path) as repo:
        repo.save(source)
        repo.save(evidence)

    connection = sqlite3.connect(path)
    connection.execute("UPDATE schema_meta SET schema_version = 3 WHERE singleton = 1")
    connection.execute("PRAGMA user_version = 3")
    connection.commit()
    connection.close()

    with SQLiteRepository(path) as repo:
        assert repo.load_evidence(evidence.evidence_id) == evidence

    connection = sqlite3.connect(path)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(evidence_records)")}
    digest = connection.execute(
        "SELECT envelope_sha256 FROM evidence_records WHERE evidence_id = ?",
        (evidence.evidence_id,),
    ).fetchone()[0]
    ledger = connection.execute(
        "SELECT version FROM schema_migrations ORDER BY version"
    ).fetchall()
    connection.close()

    assert "envelope_sha256" in columns
    assert digest is not None
    assert ledger == [(2,), (3,)]
