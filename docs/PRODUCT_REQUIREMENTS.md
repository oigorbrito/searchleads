# PRODUCT_REQUIREMENTS

Status: CANONICAL
Authority: normative requirement catalog for SearchLeads.

## Requirement Rules

- Stable IDs are mandatory.
- `INFERRED` marks requirements derived from implementation or tests and not yet separately confirmed by a source document.
- A requirement must not silently change meaning when implementation changes.
- Every critical requirement must trace to architecture, code, test, and evidence.

## Requirements

| ID | Category | Statement | Rationale | Priority | Source | Acceptance criterion | Verification method | Status |
|---|---|---|---|---|---|---|---|---|
| FR-001 | Functional | The system must discover leads from explicit evidence-backed sources. | Product value depends on repeatable acquisition. | High | README, existing discovery docs | Discovery output contains traceable evidence and source references. | Unit, integration, E2E | CANONICAL |
| FR-002 | Functional | The system must normalize company identity deterministically. | Downstream ER and qualification depend on stable identity. | High | current code/tests | Identical inputs produce identical normalized output. | Unit, invariant | CANONICAL |
| FR-003 | Functional | The system must support conservative Company ER. | Avoid false merges. | High | scorecard, tests | Review/abstain decisions are explicit; no silent fuzzy merge authority. | Benchmark, adversarial | PROVISIONAL_COMPOSE |
| FR-004 | Functional | The system must support conservative Person ER. | Avoid false merges. | High | scorecard, tests | Same as Company ER, with explicit review/abstain/merge outcomes. | Benchmark, adversarial | PROVISIONAL_COMPOSE |
| FR-005 | Functional | Contact discovery must preserve discovered evidence and owner scope. | Contact lineage is part of product trust. | High | contact docs/tests | Discovered contact includes owner and discovery evidence. | Unit, integration | CANONICAL |
| FR-006 | Functional | Contact validation must remain separate from discovery. | Prevent conflating observed and validated state. | High | domain model, tests | Validated state requires explicit validation evidence and timestamp. | Unit, contract | CANONICAL |
| DR-001 | Data | Raw Evidence must be stored separately from derived statements. | Replay and auditability. | High | persistence docs/tests | Evidence load/replay preserves raw payload and integrity checks. | Migration, invariant | CANONICAL |
| DR-002 | Data | Statements and provenance links must remain reconstructible. | Enables deterministic traceability. | High | persistence docs/tests | Statement identity and evidence links are reproducible from persisted records. | Unit, invariant | CANONICAL |
| DR-003 | Data | Person identity must not depend on `company_id`. | Prevent identity collapse across relationships. | High | scorecard, ER docs | Person identity survives company change snapshots. | Benchmark, ER tests | PROVISIONAL_COMPOSE |
| QR-001 | Quality | The system must be deterministic for the same persisted inputs. | Required for reproducibility. | High | tests, operations | Same inputs produce identical outputs and exports. | E2E | CANONICAL |
| QR-002 | Quality | The system must prefer conservative abstention over uncertain merge. | Reduce false-positive risk. | High | ER docs/tests | Ambiguous cases route to review rather than auto-merge. | Benchmark, adversarial | PROVISIONAL_COMPOSE |
| QR-003 | Quality | The system must surface explicit integrity errors when storage digests do not match. | Prevent silent corruption. | High | persistence tests | Tampered evidence is rejected with a specific integrity error. | Fault injection | CANONICAL |
| OR-001 | Operational | Supported commands and runtime paths must be documented. | Operators need a stable runbook surface. | Medium | repo docs | Startup, recovery, and failure modes are described canonically. | Review | INFERRED |
| OR-002 | Operational | The repository must distinguish infrastructure blockers from test failures. | Avoid false PASS/FAIL conclusions. | High | user guidance, tests | Unavailable tools/runners are reported as blocked, not failed. | Process review | CANONICAL |
| OR-003 | Operational | The system must support explicit startup, shutdown, backup, restore, and crash recovery contracts. | Operators need a reproducible lifecycle boundary. | High | wave 06 evidence, persistence helpers | Startup, shutdown, backup, restore, and reload are executable and tested. | Operational, migration, E2E | CANONICAL |
| OR-004 | Operational | System readiness must remain separate from SEND_READY and external certification. | Commercial gating must not leak into core service readiness. | High | wave 06 evidence, compliance docs | System readiness can pass while commercial readiness remains blocked. | Review, operational | CANONICAL |
| CR-001 | Compliance | Contact and campaign readiness must remain distinct. | Do not imply send authorization from qualification alone. | High | qualification docs/tests | Qualification does not certify send/legal readiness. | Review | CANONICAL |
| CR-002 | Compliance | Secrets must not be committed to documentation. | Protect credentials. | High | developer constraints | No secret material appears in canonical docs. | Review | CANONICAL |
