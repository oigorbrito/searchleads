from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from searchleads.domain import Evidence, Source
from searchleads.persistence import (
    EvidenceEnvelopeConsistencyError,
    SQLiteRepository,
    encode_record,
)

NOW = datetime(2026, 8, 29, 18, 0, tzinfo=timezone.utc)


def _persist_evidence(path: str) -> Evidence:
    evidence = Evidence(
        "ev-1",
        "src-1",
        "https://example.test/about",
        NOW,
        "raw payload",
        metadata={"status": 200},
    )
    with SQLiteRepository(path) as repo:
        repo.save(Source("src-1", "website", "https://example.test"))
        repo.save(evidence)
    return evidence


def _replace_envelope(path: str, envelope: Evidence) -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE evidence_records SET envelope_json = ? WHERE evidence_id = ?",
        (encode_record(replace(envelope, raw_payload=None)), "ev-1"),
    )
    connection.commit()
    connection.close()


@pytest.mark.parametrize(
    ("field_name", "tampered"),
    [
        ("evidence_id", lambda value: replace(value, evidence_id="ev-other")),
        ("source_id", lambda value: replace(value, source_id="src-other")),
        ("captured_at", lambda value: replace(value, captured_at=value.captured_at + timedelta(seconds=1))),
    ],
)
def test_load_evidence_rejects_envelope_storage_column_mismatch(
    tmp_path, field_name: str, tampered
) -> None:
    path = str(tmp_path / f"tampered-{field_name}.sqlite3")
    evidence = _persist_evidence(path)
    _replace_envelope(path, tampered(evidence))

    with SQLiteRepository(path) as repo:
        with pytest.raises(EvidenceEnvelopeConsistencyError, match="digest mismatch"):
            repo.load_evidence("ev-1")


def test_iter_evidence_rejects_tampered_envelope(tmp_path) -> None:
    path = str(tmp_path / "tampered-iteration.sqlite3")
    evidence = _persist_evidence(path)
    _replace_envelope(path, replace(evidence, source_id="src-other"))

    with SQLiteRepository(path) as repo:
        with pytest.raises(EvidenceEnvelopeConsistencyError, match="digest mismatch"):
            list(repo.iter_evidence())
