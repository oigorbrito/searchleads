# SEARCHLEADS_COMPLETION_PLAN

Status: CANONICAL
Purpose: master workstream plan and authority for the next unblocked capability.

## State Machine

- NOT_DEFINED
- DEFINED
- DESIGNED
- IMPLEMENTING
- IMPLEMENTED
- VERIFICATION_PENDING
- VERIFIED
- EXTERNAL_VALIDATION_PENDING
- READY
- BLOCKED

## Capability Map

### CAP-01 Architecture Baseline

- objective: establish canonical authority docs and stable IDs
- requirements: FR-001, QR-001, OR-002, CR-002
- dependencies: current repo docs and implementation inventory
- architecture decision: canonical docs govern experimental docs
- implementation state: IMPLEMENTING
- verification: document inventory and consistency review
- acceptance criteria: charter, requirements, architecture, domain, data, quality, V&V, readiness, traceability, and plan exist
- evidence: created canonical docs in this session
- blockers: ER closure and traceability completion
- exit criteria: baseline docs are authoritative and linked
- release impact: unlocks controlled downstream planning

### CAP-02 Company ER

- objective: close Company ER with conservative benchmark evidence
- requirements: FR-003, QR-002
- dependencies: benchmark harness and curated fixtures
- architecture decision: benchmark-closed ER, no silent merge authority
- implementation state: BLOCKED
- verification: adversarial benchmark and regression
- acceptance criteria: winner or continued defer with explicit evidence
- evidence: current scorecard and experimental tests
- blockers: execution and contract alignment
- exit criteria: documented decision plus tests aligned
- release impact: unblocks company identity direction

### CAP-03 Person ER

- objective: close Person ER with conservative benchmark evidence
- requirements: FR-004, QR-002, DR-003
- dependencies: benchmark harness and curated fixtures
- architecture decision: person identity independent from company relationship
- implementation state: BLOCKED
- verification: adversarial benchmark and regression
- acceptance criteria: decision on merge/review/abstain behavior
- evidence: current scorecard and experimental tests
- blockers: execution and contract alignment
- exit criteria: documented decision plus tests aligned
- release impact: unblocks person identity direction

### CAP-04 Evidence and Persistence

- objective: preserve raw evidence, integrity, and replay
- requirements: DR-001, QR-003
- dependencies: sqlite persistence and digest verification
- architecture decision: evidence remains separate from derived statements
- implementation state: VERIFIED_PARTIAL
- verification: persistence and fault-injection tests
- acceptance criteria: tampering is rejected, replay remains deterministic
- evidence: existing persistence tests
- blockers: some contract tests still need alignment
- exit criteria: consistency errors are explicit and covered
- release impact: protects auditability

### CAP-05 Contact Discovery and Validation

- objective: keep discovery and validation separate and evidence-backed
- requirements: FR-005, FR-006, CR-001
- dependencies: discovery sources and publication corroboration
- architecture decision: discovered state cannot imply validation
- implementation state: IMPLEMENTED
- verification: contact discovery and validation tests
- acceptance criteria: evidence-preserving discovery and explicit validation
- evidence: contact test suite
- blockers: none known at current baseline
- exit criteria: stable tests and docs linkage
- release impact: supports commercial qualification input

### CAP-06 Qualification

- objective: produce deterministic commercial qualification decisions
- requirements: CR-001, FR-001
- dependencies: policy contract and contact/person evidence
- architecture decision: qualification separate from send readiness
- implementation state: IMPLEMENTED
- verification: policy and acceptance tests
- acceptance criteria: deterministic qualification with explicit gates
- evidence: dental qualification tests
- blockers: external compliance not certified
- exit criteria: internal qualification gate stable
- release impact: gates lead generation

### CAP-07 Acquisition Runtime

- objective: define and validate runtime composition for acquisition
- requirements: OR-001, QR-001
- dependencies: runtime adapter and operations plan
- architecture decision: runtime is an adapter boundary
- implementation state: DEFERRED
- verification: runtime probes and integration checks
- acceptance criteria: acquisition path documented and testable
- evidence: experimental runtime docs/tests
- blockers: benchmark not yet closed
- exit criteria: runtime choice is documented and wired
- release impact: enables scalable acquisition path

## Critical Path

CAP-01 Architecture Baseline
→ CAP-02 Company ER
→ CAP-03 Person ER
→ CAP-04 Evidence and Persistence alignment
→ CAP-05 Contact Discovery and Validation
→ CAP-06 Qualification
→ CAP-07 Acquisition Runtime
→ integrated E2E and operational readiness

## Current Critical Path Item

CAP-01 Architecture Baseline

## Next Unblocked Capability

CAP-04 Evidence and Persistence

## Blocked Capabilities

- CAP-02 Company ER
- CAP-03 Person ER

## New Evidence

- canonical documentation baseline created
- project authority consolidated
- ER blockers remain benchmark dependent

## New Decisions

- canonical docs outrank experimental bake-off docs
- qualification remains separate from send readiness
- evidence must stay distinct from statements

