from __future__ import annotations

import base64
import hashlib
import json
import shutil
import sqlite3
from dataclasses import fields, is_dataclass, replace
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterator, Mapping, TypeVar

from searchleads.domain import (
    CandidateFact,
    CanonicalFact,
    Company,
    Conflict,
    ConflictStatus,
    ContactKind,
    ContactPoint,
    ContactStatus,
    DecisionClass,
    Evidence,
    Lead,
    LeadStage,
    Person,
    PersonCompanyRelationship,
    PersonIdentity,
    ProfessionalRegistration,
    QualificationDecision,
    Provenance,
    QualificationStatus,
    RelationshipContactLink,
    Source,
    Statement,
    StatementEvidenceLink,
)

SCHEMA_VERSION = 2
_CODEC_VERSION = 1
_TAG = "__searchleads_type__"


class PersistenceError(RuntimeError):
    """Base class for persistence failures."""


class PersistenceEncodingError(PersistenceError):
    """Raised when a domain value cannot be represented losslessly."""


class PersistenceConflictError(PersistenceError):
    """Raised when an immutable record ID is reused with different content."""


class MissingReferenceError(PersistenceError):
    """Raised when a record points to data not present in the repository."""


class EvidenceIntegrityError(PersistenceError):
    """Raised when stored raw evidence no longer matches its storage digest."""


class DomainRecordIntegrityError(PersistenceError):
    """Raised when a stored domain-record JSON payload no longer matches its digest."""


class SchemaVersionError(PersistenceError):
    """Raised when the database schema version is unsupported or inconsistent."""


Record = (
    Source
    | Evidence
    | Provenance
    | CandidateFact
    | CanonicalFact
    | Conflict
    | Company
    | Person
    | PersonIdentity
    | PersonCompanyRelationship
    | ProfessionalRegistration
    | RelationshipContactLink
    | Statement
    | StatementEvidenceLink
    | ContactPoint
    | Lead
    | QualificationDecision
)
TRecord = TypeVar("TRecord", bound=Record)

_RECORD_TYPES: dict[str, type[Record]] = {
    cls.__name__: cls
    for cls in (
        Source,
        Evidence,
        Provenance,
        CandidateFact,
        CanonicalFact,
        Conflict,
        Company,
        Person,
        PersonIdentity,
        PersonCompanyRelationship,
        ProfessionalRegistration,
        RelationshipContactLink,
        Statement,
        StatementEvidenceLink,
        ContactPoint,
        Lead,
        QualificationDecision,
    )
}
_ENUM_TYPES: dict[str, type[StrEnum]] = {
    cls.__name__: cls
    for cls in (
        ConflictStatus,
        ContactKind,
        ContactStatus,
        DecisionClass,
        LeadStage,
        QualificationStatus,
    )
}
_ID_FIELDS: dict[type[Record], str] = {
    Source: "source_id",
    Evidence: "evidence_id",
    Provenance: "provenance_id",
    CandidateFact: "fact_id",
    CanonicalFact: "fact_id",
    Conflict: "conflict_id",
    Company: "company_id",
    Person: "person_id",
    PersonIdentity: "person_id",
    PersonCompanyRelationship: "relationship_id",
    ProfessionalRegistration: "registration_id",
    RelationshipContactLink: "link_id",
    Statement: "statement_id",
    StatementEvidenceLink: "link_id",
    ContactPoint: "contact_id",
    Lead: "lead_id",
    QualificationDecision: "decision_id",
}


def _encode_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return {_TAG: "enum", "enum_type": type(value).__name__, "value": value.value}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return {_TAG: "bytes", "base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, datetime):
        return {_TAG: "datetime", "value": value.isoformat()}
    if isinstance(value, tuple):
        return {_TAG: "tuple", "items": [_encode_value(item) for item in value]}
    if isinstance(value, list):
        return {_TAG: "list", "items": [_encode_value(item) for item in value]}
    if isinstance(value, Mapping):
        return {
            _TAG: "mapping",
            "items": [[_encode_value(key), _encode_value(item)] for key, item in value.items()],
        }
    raise PersistenceEncodingError(f"unsupported value type: {type(value).__name__}")


def _decode_value(value: Any) -> Any:
    if not isinstance(value, dict) or _TAG not in value:
        return value
    tag = value[_TAG]
    if tag == "bytes":
        try:
            return base64.b64decode(value["base64"].encode("ascii"), validate=True)
        except (KeyError, ValueError) as exc:
            raise PersistenceEncodingError("invalid base64 bytes value") from exc
    if tag == "datetime":
        return datetime.fromisoformat(value["value"])
    if tag == "enum":
        enum_type = _ENUM_TYPES.get(value["enum_type"])
        if enum_type is None:
            raise PersistenceEncodingError(f"unknown enum type: {value['enum_type']}")
        return enum_type(value["value"])
    if tag == "tuple":
        return tuple(_decode_value(item) for item in value["items"])
    if tag == "list":
        return [_decode_value(item) for item in value["items"]]
    if tag == "mapping":
        return {_decode_value(key): _decode_value(item) for key, item in value["items"]}
    raise PersistenceEncodingError(f"unknown encoded value tag: {tag}")


def encode_record(record: Record) -> str:
    """Serialize a supported immutable domain record to deterministic JSON."""
    if type(record) not in _ID_FIELDS or not is_dataclass(record):
        raise PersistenceEncodingError(f"unsupported record type: {type(record).__name__}")
    document = {
        "codec_version": _CODEC_VERSION,
        "record_type": type(record).__name__,
        "fields": {field.name: _encode_value(getattr(record, field.name)) for field in fields(record)},
    }
    return json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def decode_record(payload: str) -> Record:
    """Deserialize a record produced by :func:`encode_record`."""
    try:
        document = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as exc:
        raise PersistenceEncodingError("invalid record JSON") from exc
    if document.get("codec_version") != _CODEC_VERSION:
        raise PersistenceEncodingError("unsupported codec version")
    record_type = _RECORD_TYPES.get(document.get("record_type"))
    if record_type is None:
        raise PersistenceEncodingError("unknown record type")
    encoded_fields = document.get("fields")
    if not isinstance(encoded_fields, dict):
        raise PersistenceEncodingError("record fields must be a mapping")
    values = {name: _decode_value(value) for name, value in encoded_fields.items()}
    try:
        return record_type(**values)
    except (TypeError, ValueError) as exc:
        raise PersistenceEncodingError("decoded record violates domain invariants") from exc


def raw_payload_sha256(raw_payload: str) -> str:
    """Return the storage-integrity digest for a raw textual payload."""
    return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()


def _domain_payload_sha256(payload_json: str) -> str:
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


class SQLiteRepository:
    """Append-only SQLite persistence for SearchLeads domain records.

    Evidence payloads are stored as UTF-8 BLOBs outside the JSON envelope and
    protected by an internal SHA-256 digest. Domain ``content_digest`` remains
    untouched because its semantics belong to the acquisition layer.

    Schema evolution is monotonic and additive. ``schema_meta`` remains for
    compatibility with v1 databases while ``PRAGMA user_version`` is kept in
    sync as the SQLite-native version marker from v2 onward.
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._initialize_schema()

    def __enter__(self) -> "SQLiteRepository":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    @property
    def schema_version(self) -> int:
        return int(self._connection.execute("PRAGMA user_version").fetchone()[0])

    def _initialize_schema(self) -> None:
        # V1 base shape is intentionally created first so historical databases
        # and brand-new databases follow the same tested migration path.
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

        self._migrate(meta_version)
        self._repair_current_schema()
        self._set_schema_version(SCHEMA_VERSION)
        self._connection.commit()

    def _migrate(self, version: int) -> None:
        current = version
        while current < SCHEMA_VERSION:
            if current == 1:
                self._migrate_v1_to_v2()
                current = 2
                continue
            raise SchemaVersionError(f"no migration path from schema version {current}")

    def _migrate_v1_to_v2(self) -> None:
        self._ensure_v2_shape()
        self._backfill_domain_payload_digests()
        self._connection.execute(
            "INSERT OR IGNORE INTO schema_migrations(version) VALUES (2)"
        )
        self._set_schema_version(2)

    def _repair_current_schema(self) -> None:
        # Repair is additive and idempotent. It exists for historical databases
        # whose version marker may be correct but whose shape is incomplete.
        self._ensure_v2_shape()
        self._backfill_domain_payload_digests()

    def _ensure_v2_shape(self) -> None:
        if "payload_sha256" not in self._columns("domain_records"):
            self._connection.execute(
                "ALTER TABLE domain_records ADD COLUMN payload_sha256 TEXT"
            )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def _backfill_domain_payload_digests(self) -> None:
        rows = self._connection.execute(
            "SELECT record_type, record_id, payload_json FROM domain_records WHERE payload_sha256 IS NULL"
        ).fetchall()
        for row in rows:
            self._connection.execute(
                """UPDATE domain_records SET payload_sha256 = ?
                   WHERE record_type = ? AND record_id = ?""",
                (
                    _domain_payload_sha256(row["payload_json"]),
                    row["record_type"],
                    row["record_id"],
                ),
            )

    def _set_schema_version(self, version: int) -> None:
        # PRAGMA user_version does not support parameter bindings in SQLite;
        # explicitly cast version to int to prevent any query formatting risk.
        version_int = int(version)
        self._connection.execute(
            "UPDATE schema_meta SET schema_version = ? WHERE singleton = 1",
            (version_int,),
        )
        self._connection.execute(f"PRAGMA user_version = {version_int}")

    def _columns(self, table: str) -> set[str]:
        if table not in {"schema_meta", "domain_records", "evidence_records", "schema_migrations"}:
            raise ValueError(f"unsupported schema table: {table!r}")
        # Escape double quotes in table identifier for defense-in-depth SQL query safety
        escaped_table = table.replace('"', '""')
        return {
            str(row[1])
            for row in self._connection.execute(f'PRAGMA table_info("{escaped_table}")')
        }

    @staticmethod
    def _record_id(record: Record) -> str:
        id_field = _ID_FIELDS.get(type(record))
        if id_field is None:
            raise PersistenceEncodingError(f"unsupported record type: {type(record).__name__}")
        return getattr(record, id_field)

    def save(self, record: Record) -> bool:
        """Insert a record after checking persistence-level references.

        Returns ``True`` for a new insert and ``False`` when the exact same
        immutable record was already stored. Reusing an ID for different
        content raises :class:`PersistenceConflictError`.
        """
        self._assert_references(record)
        if isinstance(record, Evidence):
            return self._save_evidence(record)
        record_id = self._record_id(record)
        payload = encode_record(record)
        digest = _domain_payload_sha256(payload)
        row = self._connection.execute(
            """SELECT payload_json, payload_sha256 FROM domain_records
               WHERE record_type = ? AND record_id = ?""",
            (type(record).__name__, record_id),
        ).fetchone()
        if row is not None:
            self._verify_domain_payload(row["payload_json"], row["payload_sha256"])
            if row["payload_json"] == payload:
                return False
            raise PersistenceConflictError(
                f"{type(record).__name__} id {record_id!r} already exists with different content"
            )
        self._connection.execute(
            """INSERT INTO domain_records(record_type, record_id, payload_json, payload_sha256)
               VALUES (?, ?, ?, ?)""",
            (type(record).__name__, record_id, payload, digest),
        )
        self._connection.commit()
        return True

    def _exists(self, record_type: type[Record], record_id: str) -> bool:
        if record_type is Evidence:
            row = self._connection.execute(
                "SELECT 1 FROM evidence_records WHERE evidence_id = ?", (record_id,)
            ).fetchone()
        else:
            row = self._connection.execute(
                "SELECT 1 FROM domain_records WHERE record_type = ? AND record_id = ?",
                (record_type.__name__, record_id),
            ).fetchone()
        return row is not None

    def _require(self, record_type: type[Record], record_id: str, context: str) -> None:
        if not self._exists(record_type, record_id):
            raise MissingReferenceError(
                f"{context} requires existing {record_type.__name__} id {record_id!r}"
            )

    def _require_evidence(self, evidence_ids: tuple[str, ...], context: str) -> None:
        for evidence_id in evidence_ids:
            self._require(Evidence, evidence_id, context)

    def _assert_references(self, record: Record) -> None:
        context = f"{type(record).__name__} {self._record_id(record)!r}"
        if isinstance(record, Source):
            return
        if isinstance(record, Evidence):
            self._require(Source, record.source_id, context)
            return
        if isinstance(record, Provenance):
            self._require_evidence(record.evidence_ids, context)
            return
        if isinstance(record, CandidateFact):
            self._require_evidence(record.evidence_ids, context)
            self._require(Provenance, record.provenance_id, context)
            return
        if isinstance(record, CanonicalFact):
            for candidate_id in record.candidate_fact_ids:
                self._require(CandidateFact, candidate_id, context)
            self._require(Provenance, record.provenance_id, context)
            return
        if isinstance(record, Conflict):
            for candidate_id in record.candidate_fact_ids:
                self._require(CandidateFact, candidate_id, context)
            return
        if isinstance(record, Company):
            # Company carries aggregate reference snapshots, but enforcing them
            # here would create an insertion cycle because Person/ContactPoint
            # require their owner Company to exist first.
            return
        if isinstance(record, PersonIdentity):
            return
        if isinstance(record, Person):
            self._require(Company, record.company_id, context)
            self._require_evidence(record.relationship_evidence_ids, context)
            return
        if isinstance(record, PersonCompanyRelationship):
            self._require(PersonIdentity, record.person_id, context)
            self._require(Company, record.company_id, context)
            self._require_evidence(record.evidence_ids, context)
            return
        if isinstance(record, ProfessionalRegistration):
            self._require(PersonIdentity, record.person_id, context)
            self._require_evidence(record.evidence_ids, context)
            return
        if isinstance(record, RelationshipContactLink):
            self._require(PersonCompanyRelationship, record.relationship_id, context)
            self._require(ContactPoint, record.contact_id, context)
            self._require_evidence(record.evidence_ids, context)
            return
        if isinstance(record, Statement):
            self._require(Provenance, record.provenance_id, context)
            return
        if isinstance(record, StatementEvidenceLink):
            self._require(Statement, record.statement_id, context)
            self._require_evidence(record.evidence_ids, context)
            return
        if isinstance(record, ContactPoint):
            if not (self._exists(Company, record.owner_id) or self._exists(Person, record.owner_id)):
                raise MissingReferenceError(
                    f"{context} requires existing Company or Person owner id {record.owner_id!r}"
                )
            self._require_evidence(record.discovery_evidence_ids, context)
            self._require_evidence(record.validation_evidence_ids, context)
            return
        if isinstance(record, Lead):
            self._require(Company, record.company_id, context)
            return
        if isinstance(record, QualificationDecision):
            self._require(Lead, record.lead_id, context)
            self._require_evidence(record.evidence_ids, context)
            return
        raise PersistenceEncodingError(  # pragma: no cover - _record_id rejects unsupported types first
            f"unsupported record type: {type(record).__name__}"
        )

    def _save_evidence(self, evidence: Evidence) -> bool:
        envelope = replace(evidence, raw_payload=None)
        envelope_json = encode_record(envelope)
        raw_bytes = evidence.raw_payload.encode("utf-8") if evidence.raw_payload is not None else None
        digest = raw_payload_sha256(evidence.raw_payload) if evidence.raw_payload is not None else None
        row = self._connection.execute(
            """SELECT envelope_json, raw_payload, raw_payload_sha256
               FROM evidence_records WHERE evidence_id = ?""",
            (evidence.evidence_id,),
        ).fetchone()
        if row is not None:
            stored_raw = bytes(row["raw_payload"]) if row["raw_payload"] is not None else None
            if (
                row["envelope_json"] == envelope_json
                and stored_raw == raw_bytes
                and row["raw_payload_sha256"] == digest
            ):
                return False
            raise PersistenceConflictError(
                f"Evidence id {evidence.evidence_id!r} already exists with different content"
            )
        self._connection.execute(
            """INSERT INTO evidence_records(
                   evidence_id, source_id, captured_at, envelope_json, raw_payload, raw_payload_sha256
               ) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                evidence.evidence_id,
                evidence.source_id,
                evidence.captured_at.isoformat(),
                envelope_json,
                raw_bytes,
                digest,
            ),
        )
        self._connection.commit()
        return True

    def load(self, record_type: type[TRecord], record_id: str) -> TRecord | None:
        """Load a record by its concrete domain type and ID."""
        if record_type not in _ID_FIELDS:
            raise PersistenceEncodingError(f"unsupported record type: {record_type.__name__}")
        if record_type is Evidence:
            return self.load_evidence(record_id)  # type: ignore[return-value]
        row = self._connection.execute(
            """SELECT payload_json, payload_sha256 FROM domain_records
               WHERE record_type = ? AND record_id = ?""",
            (record_type.__name__, record_id),
        ).fetchone()
        if row is None:
            return None
        self._verify_domain_payload(row["payload_json"], row["payload_sha256"])
        record = decode_record(row["payload_json"])
        if type(record) is not record_type:
            raise PersistenceEncodingError("stored record type does not match requested type")
        return record  # type: ignore[return-value]

    @staticmethod
    def _verify_domain_payload(payload_json: str, digest: str | None) -> None:
        if digest is None or _domain_payload_sha256(payload_json) != digest:
            raise DomainRecordIntegrityError("domain record storage digest mismatch")

    def load_evidence(self, evidence_id: str) -> Evidence | None:
        row = self._connection.execute(
            """SELECT envelope_json, raw_payload, raw_payload_sha256
               FROM evidence_records WHERE evidence_id = ?""",
            (evidence_id,),
        ).fetchone()
        if row is None:
            return None
        envelope = decode_record(row["envelope_json"])
        if not isinstance(envelope, Evidence):
            raise PersistenceEncodingError("evidence envelope has wrong record type")
        raw_payload = self._decode_raw_payload(row["raw_payload"], row["raw_payload_sha256"])
        return replace(envelope, raw_payload=raw_payload)

    @staticmethod
    def _decode_raw_payload(raw_payload: bytes | None, digest: str | None) -> str | None:
        if raw_payload is None:
            if digest is not None:
                raise EvidenceIntegrityError("raw payload digest exists without payload")
            return None
        try:
            text = bytes(raw_payload).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EvidenceIntegrityError("raw evidence is not valid UTF-8") from exc
        if digest is None or raw_payload_sha256(text) != digest:
            raise EvidenceIntegrityError("raw evidence storage digest mismatch")
        return text

    def raw_evidence_bytes(self, evidence_id: str) -> bytes | None:
        """Return the verified UTF-8 bytes used for reprocessing."""
        row = self._connection.execute(
            "SELECT raw_payload, raw_payload_sha256 FROM evidence_records WHERE evidence_id = ?",
            (evidence_id,),
        ).fetchone()
        if row is None:
            return None
        text = self._decode_raw_payload(row["raw_payload"], row["raw_payload_sha256"])
        return text.encode("utf-8") if text is not None else None

    def iter_evidence(self, source_id: str | None = None) -> Iterator[Evidence]:
        """Yield evidence in deterministic capture order for reprocessing."""
        if source_id is None:
            rows = self._connection.execute(
                "SELECT evidence_id FROM evidence_records ORDER BY captured_at, evidence_id"
            )
        else:
            rows = self._connection.execute(
                """SELECT evidence_id FROM evidence_records
                   WHERE source_id = ? ORDER BY captured_at, evidence_id""",
                (source_id,),
            )
        for row in rows:
            evidence = self.load_evidence(row["evidence_id"])
            if evidence is None:  # pragma: no cover - impossible without concurrent deletion
                raise PersistenceError("evidence disappeared during iteration")
            yield evidence

    def backup_to(self, destination: str | Path) -> Path:
        """Write a byte-for-byte SQLite backup to ``destination``."""
        destination_path = Path(destination)
        if destination_path.parent and not destination_path.parent.exists():
            destination_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(destination_path) as target_connection:
            self._connection.backup(target_connection)
            target_connection.commit()
        return destination_path

    @staticmethod
    def restore_from(backup_path: str | Path, destination: str | Path) -> Path:
        """Restore a backup file into ``destination``."""
        source_path = Path(backup_path)
        destination_path = Path(destination)
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        if destination_path.parent and not destination_path.parent.exists():
            destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
        return destination_path
