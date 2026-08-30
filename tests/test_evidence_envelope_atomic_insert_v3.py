import hashlib
from datetime import datetime, timezone

from searchleads.domain import Evidence, Source
from searchleads.persistence import SQLiteRepository, encode_record
from dataclasses import replace


NOW = datetime(2026, 8, 29, 21, 30, tzinfo=timezone.utc)


def test_new_evidence_is_inserted_with_envelope_digest_in_same_statement(tmp_path) -> None:
    path = str(tmp_path / "atomic-evidence-v3.sqlite3")
    source = Source("src-atomic", "website", "https://example.test")
    evidence = Evidence(
        "ev-atomic",
        source.source_id,
        "https://example.test/about",
        NOW,
        "raw atomic payload",
        "upstream-digest",
        {"status": 200},
    )

    with SQLiteRepository(path) as repo:
        repo.save(source)
        repo._connection.executescript(
            """
            CREATE TRIGGER require_envelope_digest_on_insert
            BEFORE INSERT ON evidence_records
            WHEN NEW.envelope_sha256 IS NULL
            BEGIN
                SELECT RAISE(ABORT, 'envelope digest must be present on insert');
            END;
            """
        )

        assert repo.save(evidence) is True

        row = repo._connection.execute(
            """SELECT envelope_json, envelope_sha256
               FROM evidence_records WHERE evidence_id = ?""",
            (evidence.evidence_id,),
        ).fetchone()

    expected_envelope = encode_record(replace(evidence, raw_payload=None))
    expected_digest = hashlib.sha256(expected_envelope.encode("utf-8")).hexdigest()

    assert row is not None
    assert row["envelope_json"] == expected_envelope
    assert row["envelope_sha256"] == expected_digest
