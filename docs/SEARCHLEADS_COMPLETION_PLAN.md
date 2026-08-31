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
- contract status: PROVISIONAL_COMPOSE
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
- contract status: PASS for local contract tests, decision status is PROVISIONAL_COMPOSE
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
- implementation state: COMPOSED
- verification: runtime probes and integration checks
- acceptance criteria: acquisition path documented and testable
- evidence: experimental runtime docs/tests
- blockers: external runtime execution path still depends on environment/tooling
- exit criteria: runtime choice is documented and wired
- release impact: enables scalable acquisition path
- contract status: COMPOSED

## Critical Path

Baseline documentation published
→ CAP-02 Company ER
→ CAP-03 Person ER
→ CAP-04 Evidence and Persistence alignment
→ CAP-05 Contact Discovery and Validation
→ CAP-06 Qualification
→ CAP-07 Acquisition Runtime
→ integrated E2E and operational readiness

## Current Critical Path Item

CAP-02 Company ER

## Next Unblocked Capability

CAP-02 Company ER

## Blocked Capabilities

- CAP-02 Company ER
- CAP-03 Person ER

## New Evidence

- canonical documentation baseline created
- project authority consolidated
- ER blockers remain benchmark dependent
- `LEGACY_CONTRACT_RECONCILIATION = COMPLETE`
- `INTERNAL_REGRESSION_SUITE = PASS` (`864 passed`, `24 skipped`, `1 xfailed`)
- skips and xfail are classified rather than hidden
- wave 03 local benchmark executed on sanctioned Windows runtime
- `Company ER` and `Person ER` are now `PROVISIONAL_COMPOSE`
- `ENGINEERING_BASELINE_ESTABLISHED = YES` (`fb774cc6ddc4f8c7fc397476f868bd1de3a70506`)

## New Decisions

- canonical docs outrank experimental bake-off docs
- qualification remains separate from send readiness
- evidence must stay distinct from statements
- PERSON_ER_CONTRACT is passable independently of PERSON_ER_TECHNOLOGY_DECISION
- COMPANY_ER is provisionally composed from local benchmark evidence, with external challenger breadth still open
- CAP-07 Acquisition Runtime is canonically COMPOSED, not deferred

## Failure Reconciliation Matrix

| Test / Failure | Canonical Requirement | Classification | Required action | Blocking capability | Release impact | Status |
|---|---|---|---|---|---|---|
| `tests/test_selective_review.py` contact/lead constructor failures | FR-006, QR-001, QR-002 | RESOLVED | fixtures now construct valid current-domain objects | CAP-05 | low | closed |
| `tests/test_dental_commercial_acceptance.py` defensive policy guard | CR-001, FR-001 | RESOLVED | guard test now mutates an otherwise valid decision object and checks runtime rejection | CAP-06 | low | closed |
| `tests/test_evidence_envelope_consistency.py` mismatch vs integrity error | DR-001, QR-003 | RESOLVED | consistency tests now accept digest-mismatch semantics as the current integrity boundary | CAP-04 | low | closed |
| `tests/test_person_entity_resolution.py` local contract | FR-004, QR-002 | PASS | retain as local contract evidence; do not infer technology winner | CAP-03 | low | pass |
| experimental chassis bake-off tests | FR-003, FR-004, QR-002 | EXPERIMENTAL_ONLY | keep as evidence only, not implementation gate | CAP-02, CAP-03 | low | evidence only |
| missing external benchmark runtime | FR-003, FR-004 | INFRASTRUCTURE_FAILURE | obtain runnable benchmark path or alternate sanctioned runtime | CAP-02, CAP-03 | high | open |

## Skip and Xfail Inventory

| Test | Classification | Reason | Requirement / capability | Status |
|---|---|---|---|---|
| `tests/experimental/test_chassis_bakeoff_adversarial.py` | EXTERNAL_DEPENDENCY | missing `followthemoney` | CAP-02/CAP-03 benchmark harness | open |
| `tests/experimental/test_chassis_bakeoff_cnpj.py` | EXTERNAL_DEPENDENCY | missing `rigour` | FR-002 / normalization contract probe | open |
| `tests/experimental/test_chassis_bakeoff_dependency_contract.py` | EXTERNAL_DEPENDENCY | dependencies installed only in bake-off workflow | CAP-02/CAP-03 benchmark harness | open |
| `tests/experimental/test_chassis_bakeoff_external_canonical.py` | EXTERNAL_DEPENDENCY | missing `followthemoney` | CAP-02 external canonical corpus | open |
| `tests/experimental/test_chassis_bakeoff_external_regression.py` | EXTERNAL_DEPENDENCY | missing `followthemoney` | CAP-02 external regression corpus | open |
| `tests/experimental/test_chassis_bakeoff_ftm_evidence_bridge.py` | EXTERNAL_DEPENDENCY | missing `followthemoney` | evidence bridge benchmark | open |
| `tests/experimental/test_chassis_bakeoff_ftm_nomenklatura.py` | EXTERNAL_DEPENDENCY | missing `followthemoney` | ER challenger harness | open |
| `tests/experimental/test_chassis_bakeoff_matching.py` | EXTERNAL_DEPENDENCY | missing `followthemoney` | ER challenger harness | open |
| `tests/experimental/test_chassis_bakeoff_nomenklatura_algorithms.py` | EXTERNAL_DEPENDENCY | missing `followthemoney` | ER challenger harness | open |
| `tests/experimental/test_chassis_bakeoff_normalization.py` | EXTERNAL_DEPENDENCY | missing `rigour` | normalization ablation | open |
| `tests/experimental/test_chassis_bakeoff_normalization_er_impact.py` | EXTERNAL_DEPENDENCY | missing `rigour` | normalization ablation / ER impact | open |
| `tests/experimental/test_chassis_bakeoff_person_relationship_lineage.py` | EXTERNAL_DEPENDENCY | missing `followthemoney` | person relationship lineage probe | open |
| `tests/experimental/test_chassis_bakeoff_person_relationship_model.py` | EXTERNAL_DEPENDENCY | missing `followthemoney` | person relationship model probe | open |
| `tests/experimental/test_chassis_bakeoff_professional_registration_model.py` | EXTERNAL_DEPENDENCY | missing `followthemoney` | person relationship / registration probe | open |
| `tests/experimental/test_chassis_bakeoff_provenance.py` | EXTERNAL_DEPENDENCY | missing `followthemoney` | provenance bridge probe | open |
| `tests/experimental/test_chassis_bakeoff_relationship_aggregate_model.py` | EXTERNAL_DEPENDENCY | missing `followthemoney` | relationship aggregate model probe | open |
| `tests/experimental/test_chassis_bakeoff_runtime.py` | EXTERNAL_DEPENDENCY | missing `crawlee` | acquisition runtime probes | open |
| `tests/experimental/test_chassis_bakeoff_runtime_adapter.py` | EXTERNAL_DEPENDENCY | missing `crawlee` | acquisition runtime adapter | open |
| `tests/experimental/test_chassis_bakeoff_runtime_adapter_persistence.py` | EXTERNAL_DEPENDENCY | missing `crawlee` | acquisition runtime adapter persistence | open |
| `tests/experimental/test_chassis_bakeoff_runtime_concurrency.py` | EXTERNAL_DEPENDENCY | missing `crawlee` | acquisition runtime concurrency | open |
| `tests/experimental/test_chassis_bakeoff_runtime_observability.py` | EXTERNAL_DEPENDENCY | missing `crawlee` | acquisition runtime observability | open |
| `tests/experimental/test_chassis_bakeoff_runtime_sessions.py` | EXTERNAL_DEPENDENCY | missing `crawlee` | acquisition runtime sessions | open |
| `tests/experimental/test_chassis_bakeoff_runtime_throttling.py` | EXTERNAL_DEPENDENCY | missing `crawlee` | acquisition runtime throttling | open |
| `tests/experimental/test_chassis_bakeoff_yente_application.py` | EXTERNAL_DEPENDENCY | Yente installed only in isolated bake-off job | separate-service challenger probe | open |
| `tests/test_dental_qualification_benchmark.py::test_benchmark_exact_contract_routing` | INTENTIONAL_OPTIONAL | `TEST_OBSOLETE` superseded by aggregate qualification analysis | legacy benchmark regression | closed |

## Blocker Register

| ID | Capability | Blocker type | Description | Internal/external | Can work continue elsewhere? | Required evidence/action | Owner/tool | Status |
|---|---|---|---|---|---|---|---|---|
| BR-001 | CAP-07 Acquisition Runtime | INFRASTRUCTURE | external runtime execution environment remains unavailable in the current checkout context | external | yes | obtain valid runtime path or sanctioned benchmark environment | CI/runtime | open |
| BR-002 | CAP-02 Company ER / CAP-03 Person ER | EXTERNAL_DEPENDENCY | benchmark challengers require `followthemoney`, `rigour`, or `crawlee` in the bake-off environment | external | yes | run challenger suite in sanctioned bake-off runtime | benchmark harness | open |
