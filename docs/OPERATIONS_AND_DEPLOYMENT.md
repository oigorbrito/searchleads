# OPERATIONS_AND_DEPLOYMENT

Status: CANONICAL

## Supported Runtime

Current repository execution is Python-based, local-test oriented, and now includes a lightweight operational chassis that can run without Crawlee.

## Services

- domain and persistence libraries
- discovery and validation workflows
- qualification and acceptance flows
- application/API surface
- runtime adapter boundary
- operational lifecycle, telemetry, and SEND_READY gates
- backup and restore helpers for SQLite-backed state
- canonical export and review surfaces
- experimental bake-off probes

## Dependencies

- sqlite for persistence
- Python test runtime
- optional experimental external packages for bake-off flows

## Storage

- raw evidence storage
- immutable domain records
- migration ledger
- schema metadata

## Startup and Shutdown

- startup must validate supported schema state, repository availability, and runtime adapter availability before readiness is reported
- startup failures are explicit and do not silently downgrade to readiness
- shutdown should preserve committed state
- interrupted migrations require repair semantics

## Recovery

- schema repair is explicit
- digest mismatch is not auto-healed
- tampering should fail closed
- backup and restore are file-backed and verified by replay

## Queue Behavior

- discovery and review workflows must preserve deterministic ordering where exposed

## Retry

- retries are allowed when they do not destroy evidence or create silent state drift

## Observability

- current observability is test/evidence driven and structured at the operational boundary
- metrics must be linked to a documented requirement or gate
- structured events should avoid raw Evidence or contact payloads

## Health and Readiness

- health is not equivalent to business readiness
- readiness must be tied to a gate definition
- health reports process liveness
- readiness reports internal wiring and dependency availability, not commercial SEND_READY
- SEND_READY is a separate state machine and does not follow from qualification alone

## Backups and Restoration

- backup and restore are implemented for SQLite-backed operational state
- restore must preserve evidence digests, statements, relationships, and qualification state

## Failure Modes

- missing dependencies
- integrity mismatch
- incompatible schema
- blocked external runners
- invalid domain state

## Deployment Topology

- lightweight local and CI execution are current
- the fallback chassis supports local operational integration without Crawlee
- the default topology is a single Python process with file-backed SQLite and explicit backup/restore paths
- external live certification remains a separate operational path
