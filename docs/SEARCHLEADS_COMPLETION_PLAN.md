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
- contract status: PENDING_BENCHMARK
- benchmark evidence: `registry_only` precision 100.0%, recall 18.5%; `exact_evidence` precision 82.6%, recall 70.4%, false_merge_rate 14.8%

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
- contract status: PASS for local contract tests, decision status remains DEFER
- benchmark evidence: operational auto-match authority is false; operational candidate matches 5/25 with 1 false positive; local contract test suite passed

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

Baseline documentation published
→ legacy contract reconciliation
→ CAP-02 Company ER
→ CAP-03 Person ER
→ CAP-04 Evidence and Persistence alignment
→ CAP-05 Contact Discovery and Validation
→ CAP-06 Qualification
→ CAP-07 Acquisition Runtime
→ integrated E2E and operational readiness

## Current Critical Path Item

legacy contract reconciliation

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
- PERSON_ER_CONTRACT is passable independently of PERSON_ER_TECHNOLOGY_DECISION
- COMPANY_ER remains benchmark-dependent with an exact-evidence challenger that is not yet acceptable as a closed decision

## Failure Reconciliation Matrix

| Test / Failure | Canonical Requirement | Classification | Required action | Blocking capability | Release impact | Status |
|---|---|---|---|---|---|---|
| `tests/test_selective_review.py` contact/lead constructor failures | FR-006, QR-001, QR-002 | TEST_OBSOLETE for some cases; CONTRACT_AMBIGUITY for others | align fixtures to current invariants or restate contract in canonical docs | CAP-04, CAP-05 | medium | open |
| `tests/test_dental_commercial_acceptance.py` defensive policy guard | CR-001, FR-001 | IMPLEMENTATION_REGRESSION if constructor guard is the intended contract, otherwise TEST_OBSOLETE | distinguish construction-time validation from runtime acceptance guard | CAP-06 | medium | open |
| `tests/test_evidence_envelope_consistency.py` mismatch vs integrity error | DR-001, QR-003 | CONTRACT_AMBIGUITY | reconcile expected exception class hierarchy and canonical error semantics | CAP-04 | medium | open |
| `tests/test_person_entity_resolution.py` local contract | FR-004, QR-002 | PASS | retain as local contract evidence; do not infer technology winner | CAP-03 | low | pass |
| experimental chassis bake-off tests | FR-003, FR-004, QR-002 | EXPERIMENTAL_ONLY | keep as evidence only, not implementation gate | CAP-02, CAP-03 | low | evidence only |
| missing external benchmark runtime | FR-003, FR-004 | INFRASTRUCTURE_FAILURE | obtain runnable benchmark path or alternate sanctioned runtime | CAP-02, CAP-03 | high | open |
