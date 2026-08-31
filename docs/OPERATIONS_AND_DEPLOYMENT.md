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

- startup must validate supported schema state
- startup must validate repository and runtime adapter availability before readiness is reported
- shutdown should preserve committed state
- interrupted migrations require repair semantics

## Recovery

- schema repair is explicit
- digest mismatch is not auto-healed
- tampering should fail closed

## Queue Behavior

- discovery and review workflows must preserve deterministic ordering where exposed

## Retry

- retries are allowed when they do not destroy evidence or create silent state drift

## Observability

- current observability is test/evidence driven
- metrics must be linked to a documented requirement or gate

## Health and Readiness

- health is not equivalent to business readiness
- readiness must be tied to a gate definition
- health reports process liveness
- readiness reports internal wiring and dependency availability, not commercial SEND_READY

## Backups and Restoration

- backup and restore requirements exist operationally but need explicit implementation detail in later work

## Failure Modes

- missing dependencies
- integrity mismatch
- incompatible schema
- blocked external runners
- invalid domain state

## Deployment Topology

- lightweight local and CI execution are current
- the fallback chassis supports local operational integration without Crawlee
- external operational topology remains a future baseline item
