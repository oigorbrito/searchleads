# SQLite schema migrations

## Scope

This work unit adds an explicit, monotonic migration path to the clean-stack SQLite persistence boundary.

The clean stack stores domain entities in generic immutable record tables rather than one table per domain entity. Migration design therefore follows the real repository schema and does not introduce legacy laboratory tables such as `people`, `contacts`, or `canonical_facts`.

## Version markers

Schema version 2 keeps two markers in sync:

- `schema_meta.schema_version`, retained for compatibility with schema v1 databases;
- SQLite `PRAGMA user_version`, used as the SQLite-native version marker from v2 onward.

A zero `user_version` is accepted for v1 compatibility. Conflicting non-zero markers fail closed. A version newer than the code supports also fails closed.

## V1 to V2

The v1-to-v2 migration is additive and idempotent:

1. Add nullable `domain_records.payload_sha256` when missing.
2. Backfill SHA-256 from the exact persisted UTF-8 `payload_json` bytes.
3. Create `schema_migrations` as an append-only migration ledger.
4. Record migration version 2.
5. Synchronize `schema_meta` and `PRAGMA user_version` to version 2.

No existing domain JSON is rewritten during migration.

`evidence_records` is not rebuilt or rewritten. Raw Evidence BLOB bytes and their existing storage digest remain unchanged byte-for-byte.

## Defensive repair

After version migration, the repository introspects the current shape with `PRAGMA table_info`. Missing additive v2 structures are repaired idempotently. This handles historical databases whose version marker says v2 but whose additive migration was incomplete.

The repair path never drops or rebuilds tables.

The public repository also repairs the migration ledger itself: after current-version schema repair, it performs an idempotent `INSERT OR IGNORE` for `SCHEMA_VERSION` in `schema_migrations`. This covers databases that already advertise schema v2 but are missing the corresponding ledger row, and remains stable across repeated reopen operations.

## Domain-record integrity

V2 verifies `payload_sha256` whenever a generic domain record is loaded or compared during an idempotent save. A modified `payload_json` with the old digest raises `DomainRecordIntegrityError` rather than being decoded as trusted state.

This complements, rather than replaces, the existing Evidence raw-payload integrity check.

## Public repository layering

Runtime consumers import `SQLiteRepository` from `searchleads.persistence`.

That public class layers current-version migration-ledger repair on top of semantic-reference validation, which itself layers on the SQLite storage implementation. Runtime consumers should not instantiate the internal repository classes from `persistence.sqlite`, `persistence.semantic`, or `persistence.ledger` directly.

An executable import-boundary test scans production package code outside the persistence implementation and repository scripts to prevent those internal imports from becoming an accidental bypass.

## Acceptance tests

Migration and persistence-boundary tests cover:

- automatic v1-to-v2 migration;
- existing Source and Evidence records remain loadable;
- source JSON remains byte-for-byte identical;
- raw Evidence BLOB remains byte-for-byte identical;
- Evidence envelope and storage SHA remain unchanged;
- domain payload hashes are backfilled correctly;
- both schema version markers become v2;
- reopening is idempotent;
- incomplete additive v2 shape is repaired;
- a v2 database missing the current-version migration ledger row is repaired idempotently;
- the public repository composes semantic validation and ledger repair;
- runtime code cannot bypass that composition through internal persistence imports;
- future versions and conflicting non-zero version markers fail closed;
- post-migration domain JSON tampering is detected.

GitHub Actions is currently failing before runner steps execute, so the presence of these tests is not reported as a current CI PASS until workflow execution is restored.
