"""SQLite persistence for LEADS_PERSISTENCE_AND_EVIDENCE_V1.

The store preserves source observations and evidence-backed facts without
introducing acquisition, normalization, entity resolution, or qualification
logic. SQLite is an ENGINEERING_CHOICE for this work unit so the persistence
contract can be validated with no external service dependency.
"""

from __future__ import annotations

import base64
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .domain import (
    CandidateFact,
    CanonicalFact,
    Company,
    Conflict,
    ConflictStatus,
    ContactKind,
    ContactPoint,
    ContactStatus,
    EntityRef,
    EntityType,
    Evidence,
    Person,
    Provenance,
    Source,
    SourceType,
)


SCHEMA_VERSION = 1


class PersistenceError(RuntimeError):
    """Base persistence error."""


class IdentityCollisionError(PersistenceError):
    """Raised when one stable ID is reused for different immutable content."""


class MissingReferenceError(PersistenceError):
    """Raised when a persisted record references data not present in the store."""


def _encode_value(value: Any) -> Any:
    """Encode supported raw values into a lossless JSON-compatible structure."""

    if value is None or isinstance(value, (bool, int, float, str)):
        return {"kind": "scalar", "value": value}
    if isinstance(value, bytes):
        return {"kind": "bytes", "base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise TypeError("cannot persist a naive datetime value")
        return {"kind": "datetime", "value": value.isoformat()}
    if isinstance(value, tuple):
        return {"kind": "tuple", "items": [_encode_value(item) for item in value]}
    if isinstance(value, list):
        return {"kind": "list", "items": [_encode_value(item) for item in value]}
    if isinstance(value, dict):
        return {
            "kind": "dict",
            "items": [[_encode_value(key), _encode_value(item)] for key, item in value.items()],
        }
    raise TypeError(f"unsupported persisted value type: {type(value).__name__}")


def _decode_value(encoded: Any) -> Any:
    kind = encoded["kind"]
    if kind == "scalar":
        return encoded["value"]
    if kind == "bytes":
        return base64.b64decode(encoded["base64"].encode("ascii"))
    if kind == "datetime":
        return datetime.fromisoformat(encoded["value"])
    if kind == "tuple":
        return tuple(_decode_value(item) for item in encoded["items"])
    if kind == "list":
        return [_decode_value(item) for item in encoded["items"]]
    if kind == "dict":
        return {
            _decode_value(key): _decode_value(item)
            for key, item in encoded["items"]
        }
    raise PersistenceError(f"unknown persisted value kind: {kind!r}")


def _dump_value(value: Any) -> str:
    return json.dumps(_encode_value(value), ensure_ascii=False, separators=(",", ":"))


def _load_value(value: str) -> Any:
    return _decode_value(json.loads(value))


def _dump_provenance(provenance: Provenance) -> str:
    return json.dumps(
        {
            "evidence_ids": list(provenance.evidence_ids),
            "activity": provenance.activity,
            "generated_at": provenance.generated_at.isoformat(),
            "agent": provenance.agent,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _load_provenance(value: str) -> Provenance:
    data = json.loads(value)
    return Provenance(
        evidence_ids=tuple(data["evidence_ids"]),
        activity=data["activity"],
        generated_at=datetime.fromisoformat(data["generated_at"]),
        agent=data["agent"],
    )


def _dump_ids(values: tuple[str, ...]) -> str:
    return json.dumps(list(values), separators=(",", ":"))


def _load_ids(value: str) -> tuple[str, ...]:
    return tuple(json.loads(value))


class SQLiteLeadStore:
    """Small synchronous persistence boundary for domain records.

    Records use stable domain IDs and immutable insert semantics. Re-inserting
    the exact same record is idempotent; reusing an ID for different content is
    rejected to avoid silently rewriting evidence or provenance.
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def __enter__(self) -> "SQLiteLeadStore":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    @property
    def schema_version(self) -> int:
        row = self._conn.execute(
            "SELECT value FROM metadata WHERE key = 'schema_version'"
        ).fetchone()
        if row is None:
            raise PersistenceError("schema_version metadata is missing")
        return int(row["value"])

    def _create_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS companies (
                company_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS people (
                person_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                locator TEXT NOT NULL,
                label TEXT
            );

            CREATE TABLE IF NOT EXISTS evidence (
                evidence_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL REFERENCES sources(source_id),
                retrieved_at TEXT NOT NULL,
                payload TEXT NOT NULL,
                locator TEXT,
                content_hash TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_evidence_source_id ON evidence(source_id);

            CREATE TABLE IF NOT EXISTS contact_points (
                contact_id TEXT PRIMARY KEY,
                owner_type TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                value TEXT NOT NULL,
                provenance TEXT NOT NULL,
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS candidate_facts (
                candidate_fact_id TEXT PRIMARY KEY,
                subject_type TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                predicate TEXT NOT NULL,
                raw_value TEXT NOT NULL,
                normalized_value TEXT,
                normalization_rule TEXT,
                provenance TEXT NOT NULL,
                confidence REAL
            );
            CREATE INDEX IF NOT EXISTS idx_candidate_subject_predicate
                ON candidate_facts(subject_type, subject_id, predicate);

            CREATE TABLE IF NOT EXISTS canonical_facts (
                canonical_fact_id TEXT PRIMARY KEY,
                subject_type TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                predicate TEXT NOT NULL,
                value TEXT NOT NULL,
                candidate_fact_ids TEXT NOT NULL,
                provenance TEXT NOT NULL,
                confidence REAL
            );
            CREATE INDEX IF NOT EXISTS idx_canonical_subject_predicate
                ON canonical_facts(subject_type, subject_id, predicate);

            CREATE TABLE IF NOT EXISTS conflicts (
                conflict_id TEXT PRIMARY KEY,
                subject_type TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                predicate TEXT NOT NULL,
                candidate_fact_ids TEXT NOT NULL,
                status TEXT NOT NULL,
                resolved_canonical_fact_id TEXT,
                resolution_note TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_conflict_subject_predicate
                ON conflicts(subject_type, subject_id, predicate);
            """
        )
        self._conn.execute(
            "INSERT OR IGNORE INTO metadata(key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        self._conn.commit()
        if self.schema_version != SCHEMA_VERSION:
            raise PersistenceError(
                f"unsupported schema version {self.schema_version}; expected {SCHEMA_VERSION}"
            )

    def _assert_provenance_exists(self, provenance: Provenance) -> None:
        missing = [
            evidence_id
            for evidence_id in provenance.evidence_ids
            if self.get_evidence(evidence_id) is None
        ]
        if missing:
            raise MissingReferenceError(
                f"provenance references missing evidence IDs: {', '.join(missing)}"
            )

    def _assert_contact_owner_exists(self, owner: EntityRef) -> None:
        if owner.entity_type is EntityType.COMPANY:
            exists = self.get_company(owner.entity_id) is not None
        elif owner.entity_type is EntityType.PERSON:
            exists = self.get_person(owner.entity_id) is not None
        else:
            exists = False
        if not exists:
            raise MissingReferenceError(
                f"contact owner does not exist: {owner.entity_type.value}:{owner.entity_id}"
            )

    def _assert_candidate_facts_exist(self, candidate_fact_ids: Iterable[str]) -> None:
        missing = [
            candidate_fact_id
            for candidate_fact_id in candidate_fact_ids
            if self.get_candidate_fact(candidate_fact_id) is None
        ]
        if missing:
            raise MissingReferenceError(
                f"missing candidate fact IDs: {', '.join(missing)}"
            )

    def _insert_or_validate_same(
        self,
        *,
        table: str,
        id_column: str,
        identifier: str,
        columns: tuple[str, ...],
        values: tuple[Any, ...],
    ) -> None:
        placeholders = ",".join("?" for _ in columns)
        column_sql = ",".join(columns)
        try:
            self._conn.execute(
                f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})",
                values,
            )
            self._conn.commit()
            return
        except sqlite3.IntegrityError as error:
            row = self._conn.execute(
                f"SELECT {column_sql} FROM {table} WHERE {id_column} = ?",
                (identifier,),
            ).fetchone()
            if row is not None and tuple(row[column] for column in columns) == values:
                return
            raise IdentityCollisionError(
                f"{table}.{id_column}={identifier!r} already exists with different content"
            ) from error

    def save_company(self, company: Company) -> None:
        self._insert_or_validate_same(
            table="companies",
            id_column="company_id",
            identifier=company.company_id,
            columns=("company_id", "created_at"),
            values=(company.company_id, company.created_at.isoformat()),
        )

    def get_company(self, company_id: str) -> Company | None:
        row = self._conn.execute(
            "SELECT company_id, created_at FROM companies WHERE company_id = ?",
            (company_id,),
        ).fetchone()
        if row is None:
            return None
        return Company(
            company_id=row["company_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def save_person(self, person: Person) -> None:
        self._insert_or_validate_same(
            table="people",
            id_column="person_id",
            identifier=person.person_id,
            columns=("person_id", "created_at"),
            values=(person.person_id, person.created_at.isoformat()),
        )

    def get_person(self, person_id: str) -> Person | None:
        row = self._conn.execute(
            "SELECT person_id, created_at FROM people WHERE person_id = ?",
            (person_id,),
        ).fetchone()
        if row is None:
            return None
        return Person(
            person_id=row["person_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def save_source(self, source: Source) -> None:
        self._insert_or_validate_same(
            table="sources",
            id_column="source_id",
            identifier=source.source_id,
            columns=("source_id", "source_type", "locator", "label"),
            values=(source.source_id, source.source_type.value, source.locator, source.label),
        )

    def get_source(self, source_id: str) -> Source | None:
        row = self._conn.execute(
            "SELECT source_id, source_type, locator, label FROM sources WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        if row is None:
            return None
        return Source(
            source_id=row["source_id"],
            source_type=SourceType(row["source_type"]),
            locator=row["locator"],
            label=row["label"],
        )

    def save_evidence(self, evidence: Evidence) -> None:
        if self.get_source(evidence.source_id) is None:
            raise MissingReferenceError(
                f"evidence source does not exist: {evidence.source_id}"
            )
        self._insert_or_validate_same(
            table="evidence",
            id_column="evidence_id",
            identifier=evidence.evidence_id,
            columns=(
                "evidence_id",
                "source_id",
                "retrieved_at",
                "payload",
                "locator",
                "content_hash",
            ),
            values=(
                evidence.evidence_id,
                evidence.source_id,
                evidence.retrieved_at.isoformat(),
                _dump_value(evidence.payload),
                evidence.locator,
                evidence.content_hash,
            ),
        )

    def get_evidence(self, evidence_id: str) -> Evidence | None:
        row = self._conn.execute(
            """
            SELECT evidence_id, source_id, retrieved_at, payload, locator, content_hash
            FROM evidence WHERE evidence_id = ?
            """,
            (evidence_id,),
        ).fetchone()
        if row is None:
            return None
        return Evidence(
            evidence_id=row["evidence_id"],
            source_id=row["source_id"],
            retrieved_at=datetime.fromisoformat(row["retrieved_at"]),
            payload=_load_value(row["payload"]),
            locator=row["locator"],
            content_hash=row["content_hash"],
        )

    def list_evidence(self, source_id: str | None = None) -> tuple[Evidence, ...]:
        if source_id is None:
            rows = self._conn.execute(
                "SELECT evidence_id FROM evidence ORDER BY rowid"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT evidence_id FROM evidence WHERE source_id = ? ORDER BY rowid",
                (source_id,),
            ).fetchall()
        loaded: list[Evidence] = []
        for row in rows:
            evidence = self.get_evidence(row["evidence_id"])
            if evidence is None:
                raise PersistenceError("evidence disappeared during enumeration")
            loaded.append(evidence)
        return tuple(loaded)

    def save_contact_point(self, contact: ContactPoint) -> None:
        self._assert_contact_owner_exists(contact.owner)
        self._assert_provenance_exists(contact.provenance)
        self._insert_or_validate_same(
            table="contact_points",
            id_column="contact_id",
            identifier=contact.contact_id,
            columns=(
                "contact_id",
                "owner_type",
                "owner_id",
                "kind",
                "value",
                "provenance",
                "status",
            ),
            values=(
                contact.contact_id,
                contact.owner.entity_type.value,
                contact.owner.entity_id,
                contact.kind.value,
                contact.value,
                _dump_provenance(contact.provenance),
                contact.status.value,
            ),
        )

    def get_contact_point(self, contact_id: str) -> ContactPoint | None:
        row = self._conn.execute(
            """
            SELECT contact_id, owner_type, owner_id, kind, value, provenance, status
            FROM contact_points WHERE contact_id = ?
            """,
            (contact_id,),
        ).fetchone()
        if row is None:
            return None
        return ContactPoint(
            contact_id=row["contact_id"],
            owner=EntityRef(EntityType(row["owner_type"]), row["owner_id"]),
            kind=ContactKind(row["kind"]),
            value=row["value"],
            provenance=_load_provenance(row["provenance"]),
            status=ContactStatus(row["status"]),
        )

    def save_candidate_fact(self, fact: CandidateFact) -> None:
        self._assert_provenance_exists(fact.provenance)
        self._insert_or_validate_same(
            table="candidate_facts",
            id_column="candidate_fact_id",
            identifier=fact.candidate_fact_id,
            columns=(
                "candidate_fact_id",
                "subject_type",
                "subject_id",
                "predicate",
                "raw_value",
                "normalized_value",
                "normalization_rule",
                "provenance",
                "confidence",
            ),
            values=(
                fact.candidate_fact_id,
                fact.subject.entity_type.value,
                fact.subject.entity_id,
                fact.predicate,
                _dump_value(fact.raw_value),
                None if fact.normalized_value is None else _dump_value(fact.normalized_value),
                fact.normalization_rule,
                _dump_provenance(fact.provenance),
                fact.confidence,
            ),
        )

    def get_candidate_fact(self, candidate_fact_id: str) -> CandidateFact | None:
        row = self._conn.execute(
            """
            SELECT candidate_fact_id, subject_type, subject_id, predicate, raw_value,
                   normalized_value, normalization_rule, provenance, confidence
            FROM candidate_facts WHERE candidate_fact_id = ?
            """,
            (candidate_fact_id,),
        ).fetchone()
        if row is None:
            return None
        return CandidateFact(
            candidate_fact_id=row["candidate_fact_id"],
            subject=EntityRef(EntityType(row["subject_type"]), row["subject_id"]),
            predicate=row["predicate"],
            raw_value=_load_value(row["raw_value"]),
            normalized_value=(
                None if row["normalized_value"] is None else _load_value(row["normalized_value"])
            ),
            normalization_rule=row["normalization_rule"],
            provenance=_load_provenance(row["provenance"]),
            confidence=row["confidence"],
        )

    def save_canonical_fact(self, fact: CanonicalFact) -> None:
        self._assert_candidate_facts_exist(fact.candidate_fact_ids)
        self._assert_provenance_exists(fact.provenance)
        self._insert_or_validate_same(
            table="canonical_facts",
            id_column="canonical_fact_id",
            identifier=fact.canonical_fact_id,
            columns=(
                "canonical_fact_id",
                "subject_type",
                "subject_id",
                "predicate",
                "value",
                "candidate_fact_ids",
                "provenance",
                "confidence",
            ),
            values=(
                fact.canonical_fact_id,
                fact.subject.entity_type.value,
                fact.subject.entity_id,
                fact.predicate,
                _dump_value(fact.value),
                _dump_ids(fact.candidate_fact_ids),
                _dump_provenance(fact.provenance),
                fact.confidence,
            ),
        )

    def get_canonical_fact(self, canonical_fact_id: str) -> CanonicalFact | None:
        row = self._conn.execute(
            """
            SELECT canonical_fact_id, subject_type, subject_id, predicate, value,
                   candidate_fact_ids, provenance, confidence
            FROM canonical_facts WHERE canonical_fact_id = ?
            """,
            (canonical_fact_id,),
        ).fetchone()
        if row is None:
            return None
        return CanonicalFact(
            canonical_fact_id=row["canonical_fact_id"],
            subject=EntityRef(EntityType(row["subject_type"]), row["subject_id"]),
            predicate=row["predicate"],
            value=_load_value(row["value"]),
            candidate_fact_ids=_load_ids(row["candidate_fact_ids"]),
            provenance=_load_provenance(row["provenance"]),
            confidence=row["confidence"],
        )

    def save_conflict(self, conflict: Conflict) -> None:
        self._assert_candidate_facts_exist(conflict.candidate_fact_ids)
        if (
            conflict.resolved_canonical_fact_id is not None
            and self.get_canonical_fact(conflict.resolved_canonical_fact_id) is None
        ):
            raise MissingReferenceError(
                "resolved conflict references missing canonical fact: "
                f"{conflict.resolved_canonical_fact_id}"
            )
        self._insert_or_validate_same(
            table="conflicts",
            id_column="conflict_id",
            identifier=conflict.conflict_id,
            columns=(
                "conflict_id",
                "subject_type",
                "subject_id",
                "predicate",
                "candidate_fact_ids",
                "status",
                "resolved_canonical_fact_id",
                "resolution_note",
            ),
            values=(
                conflict.conflict_id,
                conflict.subject.entity_type.value,
                conflict.subject.entity_id,
                conflict.predicate,
                _dump_ids(conflict.candidate_fact_ids),
                conflict.status.value,
                conflict.resolved_canonical_fact_id,
                conflict.resolution_note,
            ),
        )

    def get_conflict(self, conflict_id: str) -> Conflict | None:
        row = self._conn.execute(
            """
            SELECT conflict_id, subject_type, subject_id, predicate, candidate_fact_ids,
                   status, resolved_canonical_fact_id, resolution_note
            FROM conflicts WHERE conflict_id = ?
            """,
            (conflict_id,),
        ).fetchone()
        if row is None:
            return None
        return Conflict(
            conflict_id=row["conflict_id"],
            subject=EntityRef(EntityType(row["subject_type"]), row["subject_id"]),
            predicate=row["predicate"],
            candidate_fact_ids=_load_ids(row["candidate_fact_ids"]),
            status=ConflictStatus(row["status"]),
            resolved_canonical_fact_id=row["resolved_canonical_fact_id"],
            resolution_note=row["resolution_note"],
        )
