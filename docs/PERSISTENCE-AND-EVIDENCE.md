# SearchLeads Persistence and Evidence v1

## Work unit

`LEADS_PERSISTENCE_AND_EVIDENCE_V1`

This unit adds the minimum persistence layer required to preserve the scientific/domain model without introducing acquisition, crawling, entity-resolution, validation, or qualification algorithms.

## Gates

- `RAW_EVIDENCE_PRESERVED = YES`
- `REPROCESSABLE = YES`
- `ROUNDTRIP = PASS`

## Storage model

Persistence uses SQLite through Python's standard library. This is an `ENGINEERING_CHOICE`, not an evidence-backed claim that SQLite is the final production database.

Two storage paths are deliberately separated:

1. `domain_records` stores deterministic typed JSON envelopes for immutable domain objects other than raw evidence payloads.
2. `evidence_records` stores an Evidence envelope plus the raw payload as UTF-8 bytes in a SQLite BLOB.

The raw payload receives an internal SHA-256 digest used only to detect storage corruption. `Evidence.content_digest` is preserved exactly as supplied and is not reinterpreted, replaced, or assumed to use SHA-256.

## Immutability and idempotency

Records are append-only by `(record_type, record_id)` and Evidence is append-only by `evidence_id`.

- Writing the exact same immutable record again is idempotent.
- Reusing the same ID with different content raises `PersistenceConflictError`.
- No update API is included in v1.

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

The persistence layer does not narrow the domain model itself: `CandidateFact.raw_value` and related `Any` fields remain unchanged. The SQLite codec simply defines which values can be persisted losslessly in this version.

## Reprocessing contract

`SQLiteRepository.iter_evidence()` yields reconstructed Evidence objects in deterministic `(captured_at, evidence_id)` order and can be filtered by `source_id`.

`SQLiteRepository.raw_evidence_bytes()` returns verified UTF-8 bytes for a stored payload. A digest mismatch, invalid UTF-8 payload, or inconsistent payload/digest state raises `EvidenceIntegrityError` before data is returned for reprocessing.

## Schema versioning

The SQLite file stores `SCHEMA_VERSION = 1` in `schema_meta`. Opening a database with a different schema version raises `SchemaVersionError`; no implicit migration is attempted.

## Explicitly deferred

- database selection for production scale;
- migrations beyond schema v1;
- concurrent/distributed writers;
- acquisition/crawler implementation;
- binary/non-text web artifact capture;
- compression/deduplication/object storage;
- retention policy;
- source-specific parsing;
- normalization rules;
- entity-resolution persistence/query indexes;
- contact validation;
- ICP and qualification logic.

## Verification

Local verification for this unit:

- 73 pre-existing domain tests retained and passing;
- 55 persistence/codec tests passing;
- 128 total tests passing;
- 100% line coverage across the measured package statements;
- ResourceWarnings treated as errors during the final run.
