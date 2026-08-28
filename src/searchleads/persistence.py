from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .domain import Evidence, Source

CURRENT_SCHEMA_VERSION = 3


class UnsupportedSchemaVersion(RuntimeError):
    pass


class SQLiteStore:
    """SQLite reference persistence with additive, idempotent migrations."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> SQLiteStore:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        self.close()

    @property
    def schema_version(self) -> int:
        return int(self.connection.execute("PRAGMA user_version").fetchone()[0])

    def table_exists(self, table: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        return row is not None

    def columns(self, table: str) -> set[str]:
        if not self.table_exists(table):
            return set()
        return {row[1] for row in self.connection.execute(f"PRAGMA table_info({_quote_ident(table)})")}

    def put_source(self, source: Source) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO sources (id, name, kind, locator)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    kind = excluded.kind,
                    locator = excluded.locator
                """,
                (source.id, source.name, source.kind, source.locator),
            )

    def put_evidence(self, evidence: Evidence) -> None:
        with self.connection:
            existing = self.connection.execute(
                "SELECT raw_content, sha256 FROM evidence WHERE id = ?",
                (evidence.id,),
            ).fetchone()
            if existing is not None:
                if bytes(existing["raw_content"]) != evidence.raw_content or existing["sha256"] != evidence.sha256:
                    raise ValueError("Evidence is immutable and cannot be replaced")
                return
            self.connection.execute(
                """
                INSERT INTO evidence (id, source_id, raw_content, sha256, retrieved_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    evidence.id,
                    evidence.source_id,
                    evidence.raw_content,
                    evidence.sha256,
                    evidence.retrieved_at,
                ),
            )

    def get_evidence(self, evidence_id: str) -> Evidence | None:
        row = self.connection.execute(
            "SELECT id, source_id, raw_content, sha256, retrieved_at FROM evidence WHERE id = ?",
            (evidence_id,),
        ).fetchone()
        if row is None:
            return None
        return Evidence(
            id=row["id"],
            source_id=row["source_id"],
            raw_content=bytes(row["raw_content"]),
            sha256=row["sha256"],
            retrieved_at=row["retrieved_at"],
        )

    def _migrate(self) -> None:
        version = self.schema_version
        if version > CURRENT_SCHEMA_VERSION:
            raise UnsupportedSchemaVersion(
                f"database schema {version} is newer than supported {CURRENT_SCHEMA_VERSION}"
            )

        with self.connection:
            if version < 1:
                self._migration_1_core()
            if version < 2:
                self._migration_2_people_contacts()
            if version < 3:
                self._migration_3_facts_review_and_leads()

            # Historical databases may have user_version values that do not
            # fully describe their shape. Repair only by additive operations.
            self._repair_current_schema()
            self.connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION}")

    def _migration_1_core(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                locator TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                raw_content BLOB NOT NULL,
                sha256 TEXT NOT NULL,
                retrieved_at TEXT,
                FOREIGN KEY(source_id) REFERENCES sources(id)
            );

            CREATE TABLE IF NOT EXISTS companies (
                id TEXT PRIMARY KEY,
                legal_name TEXT
            );

            CREATE TABLE IF NOT EXISTS candidate_facts (
                id TEXT PRIMARY KEY,
                subject_type TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                value_json TEXT NOT NULL,
                evidence_id TEXT NOT NULL,
                FOREIGN KEY(evidence_id) REFERENCES evidence(id)
            );

            CREATE TABLE IF NOT EXISTS canonical_facts (
                id TEXT PRIMARY KEY,
                subject_type TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                value_json TEXT NOT NULL
            );
            """
        )

    def _migration_2_people_contacts(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS people (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                evidence_id TEXT
            );

            CREATE TABLE IF NOT EXISTS professional_roles (
                id TEXT PRIMARY KEY,
                person_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                title TEXT NOT NULL,
                evidence_id TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS contacts (
                id TEXT PRIMARY KEY,
                owner_type TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                value TEXT NOT NULL,
                evidence_id TEXT,
                discovery_rule TEXT
            );

            CREATE TABLE IF NOT EXISTS contact_validations (
                id TEXT PRIMARY KEY,
                contact_point_id TEXT NOT NULL,
                status TEXT NOT NULL,
                rule TEXT NOT NULL,
                evidence_id TEXT
            );
            """
        )

    def _migration_3_facts_review_and_leads(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS normalizations (
                id TEXT PRIMARY KEY,
                subject_type TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                input_value_json TEXT NOT NULL,
                normalized_value_json TEXT NOT NULL,
                rule TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                qualification_state TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS review_cases (
                id TEXT PRIMARY KEY,
                reason TEXT NOT NULL,
                subject_type TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                details_json TEXT NOT NULL DEFAULT '{}'
            );
            """
        )
        self._add_column_if_missing(
            "canonical_facts",
            "supporting_candidate_fact_ids",
            "TEXT NOT NULL DEFAULT '[]'",
        )

    def _repair_current_schema(self) -> None:
        self._migration_1_core()
        self._migration_2_people_contacts()
        self._migration_3_facts_review_and_leads()
        self._add_column_if_missing("people", "evidence_id", "TEXT")
        self._add_column_if_missing("contacts", "evidence_id", "TEXT")
        self._add_column_if_missing("contacts", "discovery_rule", "TEXT")
        self._add_column_if_missing(
            "canonical_facts",
            "supporting_candidate_fact_ids",
            "TEXT NOT NULL DEFAULT '[]'",
        )

    def _add_column_if_missing(self, table: str, column: str, definition: str) -> None:
        if column not in self.columns(table):
            self.connection.execute(
                f"ALTER TABLE {_quote_ident(table)} ADD COLUMN {_quote_ident(column)} {definition}"
            )


def encode_ids(ids: Iterable[str]) -> str:
    return json.dumps(list(ids), separators=(",", ":"), sort_keys=False)


def decode_ids(value: str) -> tuple[str, ...]:
    loaded = json.loads(value)
    if not isinstance(loaded, list) or not all(isinstance(item, str) for item in loaded):
        raise ValueError("expected JSON array of string ids")
    return tuple(loaded)


def _quote_ident(identifier: str) -> str:
    if not identifier or not identifier.replace("_", "").isalnum():
        raise ValueError(f"unsafe SQLite identifier: {identifier!r}")
    return f'"{identifier}"'
