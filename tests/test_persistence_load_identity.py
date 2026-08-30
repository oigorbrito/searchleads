import hashlib
import sqlite3

import pytest

from searchleads.domain import Source
from searchleads.persistence import DomainRecordIdentityError, SQLiteRepository, encode_record


def test_load_rejects_valid_rehashed_payload_with_different_record_id(tmp_path) -> None:
    path = str(tmp_path / "identity-mismatch.sqlite3")
    original = Source("source-a", "website", "https://a.example")
    replacement = Source("source-b", "website", "https://b.example")

    with SQLiteRepository(path) as repo:
        repo.save(original)

    payload = encode_record(replacement)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    connection = sqlite3.connect(path)
    connection.execute(
        """UPDATE domain_records
           SET payload_json = ?, payload_sha256 = ?
           WHERE record_type = 'Source' AND record_id = ?""",
        (payload, digest, original.source_id),
    )
    connection.commit()
    connection.close()

    with SQLiteRepository(path) as repo:
        with pytest.raises(DomainRecordIdentityError, match="physical record id"):
            repo.load(Source, original.source_id)
