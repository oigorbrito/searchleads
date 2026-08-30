from __future__ import annotations

import hashlib
from dataclasses import replace

from searchleads.domain import Evidence

from .ledger import SQLiteRepository as _LedgerSQLiteRepository
from .sqlite import (
    PersistenceConflictError,
    PersistenceError,
    SchemaVersionError,
    encode_record,
    raw_payload_sha256,
)

SCHEMA_VERSION = 3


class EvidenceEnvelopeIntegrityError(PersistenceError):
    """Raised when a persisted Evidence envelope no longer matches its storage digest."""


def _envelope_sha256(envelope_json: str) -> str:
    return hashlib.sha256(envelope_json.encode("utf-8")).hexdigest()


class SQLiteRepository(_LedgerSQLiteRepository):
    """Public persistence repository with schema-v3 Evidence envelope integrity."""

    def _initialize_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (
                singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                schema_version INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS domain_records (
                record_type TEXT NOT NULL,
                record_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (record_type, record_id)
            );

            CREATE TABLE IF NOT EXISTS evidence_records (
                evidence_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                envelope_json TEXT NOT NULL,
                raw_payload BLOB,
                raw_payload_sha256 TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_evidence_source_capture
                ON evidence_records (source_id, captured_at, evidence_id);
            """
        )

        row = self._connection.execute(
            "SELECT schema_version FROM schema_meta WHERE singleton = 1"
        ).fetchone()
        meta_version = int(row["schema_version"]) if row is not None else 1
        pragma_version = int(self._connection.execute("PRAGMA user_version").fetchone()[0])

        if meta_version > SCHEMA_VERSION or pragma_version > SCHEMA_VERSION:
            self._connection.close()
            raise SchemaVersionError(
                "database schema version is newer than supported "
                f"(schema_meta={meta_version}, user_version={pragma_version}, supported={SCHEMA_VERSION})"
            )
        if pragma_version not in (0, meta_version):
            self._connection.close()
            raise SchemaVersionError(
                "database schema version markers disagree "
                f"(schema_meta={meta_version}, user_version={pragma_version})"
            )

        if row is None:
            self._connection.execute(
                "INSERT INTO schema_meta(singleton, schema_version) VALUES (1, ?)",
                (meta_version,),
            )

        if meta_version < 2:
            super()._migrate(meta_version)
            meta_version = 2

        if meta_version == 2:
            self._migrate_v2_to_v3()
            meta_version = 3

        if meta_version != SCHEMA_VERSION:
            self._connection.close()
            raise SchemaVersionError(f"no migration path from schema version {meta_version}")

        self._repair_current_schema()
        self._set_schema_version(SCHEMA_VERSION)
        self._connection.commit()

    def _migrate_v2_to_v3(self) -> None:
        # A historical database can claim v2 while missing additive v2 shape.
        # Repair the lower layer first, then add the v3 column and digest backfill.
        super()._repair_current_schema()
        self._ensure_v3_shape()
        self._backfill_evidence_envelope_digests()
        self._connection.execute(
            "INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)",
            (SCHEMA_VERSION,),
        )
        self._set_schema_version(SCHEMA_VERSION)

    def _repair_current_schema(self) -> None:
        super()._repair_current_schema()
        added_envelope_digest_column = self._ensure_v3_shape()
        if added_envelope_digest_column:
            # A database already marked v3 may come from an interrupted additive
            # migration that never created the v3 column. In that specific repair
            # case the existing envelopes are the only available backfill source.
            self._backfill_evidence_envelope_digests()
        else:
            # Once the v3 column exists, a missing digest is persisted integrity
            # state, not shape repair. Do not silently synthesize trust on reopen.
            self._assert_no_missing_evidence_envelope_digests()
        self._connection.execute(
            "INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)",
            (SCHEMA_VERSION,),
        )

    def _ensure_v3_shape(self) -> bool:
        if "envelope_sha256" in self._columns("evidence_records"):
            return False
        self._connection.execute(
            "ALTER TABLE evidence_records ADD COLUMN envelope_sha256 TEXT"
        )
        return True

    def _backfill_evidence_envelope_digests(self) -> None:
        rows = self._connection.execute(
            "SELECT evidence_id, envelope_json FROM evidence_records WHERE envelope_sha256 IS NULL"
        ).fetchall()
        for row in rows:
            self._connection.execute(
                "UPDATE evidence_records SET envelope_sha256 = ? WHERE evidence_id = ?",
                (_envelope_sha256(row["envelope_json"]), row["evidence_id"]),
            )

    def _assert_no_missing_evidence_envelope_digests(self) -> None:
        row = self._connection.execute(
            "SELECT evidence_id FROM evidence_records WHERE envelope_sha256 IS NULL LIMIT 1"
        ).fetchone()
        if row is not None:
            raise EvidenceEnvelopeIntegrityError(
                f"Evidence {row['evidence_id']!r} envelope storage digest is missing"
            )

    def _verify_evidence_envelope(self, evidence_id: str) -> None:
        row = self._connection.execute(
            "SELECT envelope_json, envelope_sha256 FROM evidence_records WHERE evidence_id = ?",
            (evidence_id,),
        ).fetchone()
        if row is None:
            return
        digest = row["envelope_sha256"]
        if digest is None or _envelope_sha256(row["envelope_json"]) != digest:
            raise EvidenceEnvelopeIntegrityError(
                f"Evidence {evidence_id!r} envelope storage digest mismatch"
            )

    def _save_evidence(self, evidence: Evidence) -> bool:
        envelope = replace(evidence, raw_payload=None)
        envelope_json = encode_record(envelope)
        envelope_digest = _envelope_sha256(envelope_json)
        raw_bytes = evidence.raw_payload.encode("utf-8") if evidence.raw_payload is not None else None
        raw_digest = raw_payload_sha256(evidence.raw_payload) if evidence.raw_payload is not None else None

        row = self._connection.execute(
            """SELECT envelope_json, raw_payload, raw_payload_sha256, envelope_sha256
               FROM evidence_records WHERE evidence_id = ?""",
            (evidence.evidence_id,),
        ).fetchone()
        if row is not None:
            self._verify_evidence_envelope(evidence.evidence_id)
            stored_raw = bytes(row["raw_payload"]) if row["raw_payload"] is not None else None
            if (
                row["envelope_json"] == envelope_json
                and stored_raw == raw_bytes
                and row["raw_payload_sha256"] == raw_digest
                and row["envelope_sha256"] == envelope_digest
            ):
                return False
            raise PersistenceConflictError(
                f"Evidence id {evidence.evidence_id!r} already exists with different content"
            )

        # V3 writes the envelope and both storage digests in the same INSERT and
        # transaction. There is no committed state in which a newly saved Evidence
        # row exists without its envelope digest.
        self._connection.execute(
            """INSERT INTO evidence_records(
                   evidence_id, source_id, captured_at, envelope_json,
                   raw_payload, raw_payload_sha256, envelope_sha256
               ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                evidence.evidence_id,
                evidence.source_id,
                evidence.captured_at.isoformat(),
                envelope_json,
                raw_bytes,
                raw_digest,
                envelope_digest,
            ),
        )
        self._connection.commit()
        return True

    def load_evidence(self, evidence_id: str) -> Evidence | None:
        self._verify_evidence_envelope(evidence_id)
        return super().load_evidence(evidence_id)
