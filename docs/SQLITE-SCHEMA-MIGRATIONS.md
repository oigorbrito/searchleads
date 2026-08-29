# SQLite schema migrations

## Scope

This work unit defines the explicit, monotonic migration path for the clean-stack SQLite persistence boundary.

The clean stack stores domain entities in generic immutable record tables rather than one table per domain entity. Migration design follows the real repository schema and does not introduce legacy laboratory tables such as `people`, `contacts`, or `canonical_facts`.

## Version markers

The current schema is version 3. Two markers are kept in sync:

- `schema_meta.schema_version`, retained for compatibility with schema v1 databases;
- SQLite `PRAGMA user_version`, used as the SQLite-native version marker from v2 onward.

A zero `user_version` is accepted for historical compatibility. Conflicting non-zero markers fail closed. A version newer than the code supports also fails closed.

## V1 to V2

The v1-to-v2 migration is additive and idempotent:

1. Add nullable `domain_records.payload_sha256` when missing.
2. Backfill SHA-256 from the exact persisted UTF-8 `payload_json` bytes.
3. Create `schema_migrations` as an append-only migration ledger.
4. Record migration version 2.
5. Synchronize `schema_meta` and `PRAGMA user_version` to version 2.

No existing domain JSON is rewritten during migration. `evidence_records` is not rebuilt or rewritten, and raw Evidence BLOB bytes remain unchanged.

## V2 to V3

The v2-to-v3 migration closes the remaining Evidence-envelope storage-integrity gap without changing the domain codec:

1. Repair any incomplete additive v2 shape before applying v3.
2. Add nullable `evidence_records.envelope_sha256` when missing.
3. Backfill SHA-256 from the exact persisted UTF-8 `envelope_json` bytes.
4. Record migration version 3.
5. Synchronize both schema version markers to version 3.

The migration does not rewrite `envelope_json`, raw Evidence BLOB bytes, `raw_payload_sha256`, or upstream `Evidence.content_digest` values.

V3 verifies `envelope_sha256` before decoding/returning Evidence and before an idempotent save of an existing Evidence record. A digest mismatch raises `EvidenceEnvelopeIntegrityError` rather than silently trusting or repairing the record.

This SHA-256 is an internal storage-integrity checksum. It detects accidental or unilateral persisted-envelope modification; it is not an authenticity guarantee against an actor that can rewrite both the payload and its digest.

## Defensive repair

After version migration, the repository introspects the current shape with `PRAGMA table_info`. Missing additive structures are repaired idempotently. This handles historical databases whose version marker advertises the current version while an additive migration was incomplete.

Repair never drops or rebuilds tables. The migration ledger is also repaired idempotently, preserving the historical chain `[2, 3]` for a database that has traversed both implemented migrations.

For v3 specifically, backfill during defensive repair is permitted only when the `envelope_sha256` column itself is absent and must be added. Once that v3 column already exists, a persisted Evidence row with `envelope_sha256 IS NULL` is treated as invalid integrity state and opening the repository fails closed; the digest is not silently reconstructed on reopen.

## Storage integrity

V2 verifies `domain_records.payload_sha256` whenever a generic domain record is loaded or compared during an idempotent save.

Raw Evidence bytes continue to use `raw_payload_sha256` and UTF-8 validation.

V3 adds independent integrity verification for the complete serialized Evidence envelope, covering envelope-only fields such as locator, metadata, and upstream content digest in addition to the redundant-column consistency checks introduced before v3.

## Public repository layering

Runtime consumers import `SQLiteRepository` and `SCHEMA_VERSION` from `searchleads.persistence`.

The public class now layers schema-v3 envelope integrity over migration-ledger repair, semantic-reference validation, and the base SQLite storage implementation. Runtime consumers must not instantiate `persistence.v3`, `persistence.ledger`, `persistence.semantic`, or `persistence.sqlite` directly.

The executable import-boundary test scans production package code outside the persistence implementation and repository scripts to prevent implementation-module imports from becoming an accidental bypass.

## Acceptance tests

Migration and persistence-boundary tests cover:

- automatic v1-to-v2-to-v3 migration;
- direct v2-to-v3 migration;
- exact preservation of existing Evidence envelope JSON and raw Evidence bytes during v3 backfill;
- SHA-256 backfill for existing Evidence envelopes;
- both schema version markers becoming v3;
- migration ledger history `[2, 3]` and idempotent reopen behavior;
- incomplete additive v2 and v3 shapes being repaired;
- an existing v3 digest column with a missing per-row digest failing closed instead of being silently backfilled;
- domain payload, raw Evidence, and full Evidence-envelope tampering failing closed;
- envelope-only tampering in locator, metadata, and upstream content digest being detected;
- idempotent save refusing to silently repair an invalid envelope digest;
- public repository layering and runtime import-boundary enforcement;
- future versions and conflicting non-zero version markers failing closed.

GitHub Actions is currently failing before runner steps execute, so the presence of these tests is not reported as a current CI PASS until workflow execution is restored.