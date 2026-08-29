from __future__ import annotations

import hashlib

from searchleads.domain import Evidence

from .ledger import SQLiteRepository as _LedgerSQLiteRepository
from .sqlite import PersistenceError, SchemaVersionError

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
        self._ensure_v3_shape()
        self._backfill_evidence_envelope_digests()
        self._connection.execute(
            "INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)",
            (SCHEMA_VERSION,),
        )

    def _ensure_v3_shape(self) -> None:
        if "envelope_sha256" not in self._columns("evidence_records"):
            self._connection.execute(
                "ALTER TABLE evidence_records ADD COLUMN envelope_sha256 TEXT"
            )

    def _backfill_evidence_envelope_digests(self) -> None:
        rows = self._connection.execute(
            "SELECT evidence_id, envelope_json FROM evidence_records WHERE envelope_sha256 IS NULL"
        ).fetchall()
        for row in rows:
            self._connection.execute(
                "UPDATE evidence_records SET envelope_sha256 = ? WHERE evidence_id = ?",
                (_envelope_sha256(row["envelope_json"]), row["evidence_id"]),
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
        existing = self._connection.execute(
            "SELECT 1 FROM evidence_records WHERE evidence_id = ?",
            (evidence.evidence_id,),
        ).fetchone()
        if existing is not None:
            self._verify_evidence_envelope(evidence.evidence_id)

        inserted = super()._save_evidence(evidence)
        if not inserted:
            return False

        row = self._connection.execute(
            "SELECT envelope_json FROM evidence_records WHERE evidence_id = ?",
            (evidence.evidence_id,),
        ).fetchone()
        if row is None:  # pragma: no cover - impossible without concurrent deletion
            raise EvidenceEnvelopeIntegrityError(
                f"Evidence {evidence.evidence_id!r} disappeared during envelope hashing"
            )
        self._connection.execute(
            "UPDATE evidence_records SET envelope_sha256 = ? WHERE evidence_id = ?",
            (_envelope_sha256(row["envelope_json"]), evidence.evidence_id),
        )
        self._connection.commit()
        return True

    def load_evidence(self, evidence_id: str) -> Evidence | None:
        self._verify_evidence_envelope(evidence_id)
        return super().load_evidence(evidence_id)
