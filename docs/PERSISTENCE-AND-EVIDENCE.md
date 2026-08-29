# SearchLeads Persistence and Evidence v2

## Work unit

`LEADS_PERSISTENCE_AND_EVIDENCE_V1` established the storage boundary. The current clean stack extends that contract with additive SQLite schema migrations, semantic reference checks, migration-ledger repair, and a public persistence import boundary.

This document describes the current persistence contract rather than the historical v1-only implementation state.

## Gates

- `RAW_EVIDENCE_PRESERVED = YES`
- `REPROCESSABLE = YES`
- `ROUNDTRIP = PASS` for the original verified persistence unit; current stacked CI execution must not be reported as PASS while GitHub Actions jobs terminate before running steps.

## Storage model

Persistence uses SQLite through Python's standard library. This is an `ENGINEERING_CHOICE`, not an evidence-backed claim that SQLite is the final production database.

Two storage paths are deliberately separated:

1. `domain_records` stores deterministic typed JSON envelopes for immutable domain objects other than raw evidence payloads and, in schema v2, stores an internal SHA-256 for each domain envelope.
2. `evidence_records` stores an Evidence envelope plus the raw payload as UTF-8 bytes in a SQLite BLOB.

The raw Evidence payload receives an internal SHA-256 digest used only to detect storage corruption. `Evidence.content_digest` is preserved exactly as supplied and is not reinterpreted, replaced, or assumed to use SHA-256.

Schema v2 likewise uses `domain_records.payload_sha256` only as a storage-integrity digest. Existing domain JSON is not rewritten during migration.

## Public repository boundary

Runtime consumers obtain `SQLiteRepository` from `searchleads.persistence`.

The public repository composes the current persistence layers:

- SQLite codec/storage and reference-existence checks;
- semantic fact/provenance scope validation;
- idempotent current-version migration-ledger repair.

Direct runtime imports of implementation repositories from `searchleads.persistence.sqlite`, `.semantic`, or `.ledger` are intentionally outside the public contract and are guarded by an executable AST boundary test.

## Immutability and idempotency

Records are append-only by `(record_type, record_id)` and Evidence is append-only by `evidence_id`.

- Writing the exact same immutable record again is idempotent.
- Reusing the same ID with different content raises `PersistenceConflictError`.
- No record-update API is included.

This avoids silently rewriting evidence or facts that may already be referenced by provenance.

## Round-trip contract

The codec preserves:

- dataclass record type;
- timezone-aware datetimes;
- all SearchLeads `StrEnum` concrete types;
- tuples versus lists;
- nested mappings and JSON-compatible scalar values;
- Unicode text without ASCII coercion.

Unsupported Python values are rejected with `PersistenceEncodingError` rather than being stringified or silently made lossy.

The persistence layer does not narrow the domain model itself: `CandidateFact.raw_value` and related `Any` fields remain unchanged. The SQLite codec defines which values can be persisted losslessly in this version.

## Reference integrity

Persistence distinguishes existence checks from semantic compatibility.

Base reference checks require referenced Source, Evidence, Company, Person, Provenance, CandidateFact, or related records to exist where the domain relationship requires them.

The public semantic layer additionally rejects existing-but-incompatible fact lineage. CandidateFact, CanonicalFact, Conflict, and Provenance references must agree on the relevant `subject_id` and `field_name` scope. Existing IDs are therefore insufficient when they refer to an unrelated fact lineage.

## Reprocessing contract

`SQLiteRepository.iter_evidence()` yields reconstructed Evidence objects in deterministic `(captured_at, evidence_id)` order and can be filtered by `source_id`.

`SQLiteRepository.raw_evidence_bytes()` returns verified UTF-8 bytes for a stored payload. A digest mismatch, invalid UTF-8 payload, or inconsistent payload/digest state raises `EvidenceIntegrityError` before data is returned for reprocessing.

Schema v2 also verifies `domain_records.payload_sha256` when generic domain records are loaded or compared during idempotent save. Tampered domain JSON raises `DomainRecordIntegrityError` before it is treated as trusted state.

## Schema versioning and migration

The current schema is `SCHEMA_VERSION = 2`.

Version state uses two coordinated markers:

- `schema_meta.schema_version`, retained from v1;
- SQLite `PRAGMA user_version`, used from v2 onward.

Opening a real v1 database performs the additive, idempotent v1→v2 migration documented in `SQLITE-SCHEMA-MIGRATIONS.md`. The migration adds the domain payload integrity digest, backfills it from the exact stored JSON bytes, creates the append-only `schema_migrations` ledger, records version 2, and synchronizes both version markers.

A database already marked v2 is defensively inspected for missing additive v2 structures. Repair is idempotent and also ensures the current schema version is represented in `schema_migrations`, including historical incomplete-v2 databases whose version markers were already advanced.

Future schema versions and conflicting non-zero version markers fail closed with `SchemaVersionError`.

## Explicitly deferred

- database selection for production scale;
- schema migrations beyond v2;
- concurrent/distributed writers;
- binary/non-text web artifact capture;
- compression/deduplication/object storage;
- retention policy;
- entity-resolution persisted merge/split mechanics and specialized query indexes.

Acquisition, source-specific parsing, normalization, entity resolution, contact validation, vertical ICP policy, qualification, and export now exist in later clean-stack work units and are no longer persistence-layer deferred decisions.

## Verification status

The original persistence unit recorded its local verification results in the historical v1 document state. Later migration and invariant units add executable tests for schema migration, integrity, semantic references, ledger repair, and the public import boundary.

At the current repository state, GitHub Actions jobs have repeatedly terminated before any workflow step is provisioned (`steps=[]`/no runner logs). Until execution resumes, no new aggregate `pytest` or `compileall` PASS should be inferred from the presence of these tests alone.
