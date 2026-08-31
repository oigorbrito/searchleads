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
- implementation state: VERIFIED
- verification: document inventory and consistency review
- acceptance criteria: charter, requirements, architecture, domain, data, quality, V&V, readiness, traceability, and plan exist
- evidence: created canonical docs in this session
- blockers: none
- exit criteria: baseline docs are authoritative and linked
- release impact: unlocks controlled downstream planning

### CAP-02 Company ER

- objective: close Company ER with conservative benchmark evidence
- requirements: FR-003, QR-002
- dependencies: benchmark harness and curated fixtures
- architecture decision: benchmark-closed ER, no silent merge authority
- implementation state: VERIFIED_PARTIAL
- verification: adversarial benchmark and regression
- acceptance criteria: winner or continued defer with explicit evidence
- evidence: current scorecard and experimental tests
- blockers: external challenger breadth and post-baseline recalibration
- exit criteria: documented decision plus tests aligned
- release impact: unblocks company identity direction
- contract status: PROVISIONAL_COMPOSE
- benchmark evidence: `registry_only` precision 100.0%, recall 18.5%; `exact_evidence` precision 82.6%, recall 70.4%, false_merge_rate 14.8%

### CAP-03 Person ER

- objective: close Person ER with conservative benchmark evidence
- requirements: FR-004, QR-002, DR-003
- dependencies: benchmark harness and curated fixtures
- architecture decision: person identity independent from company relationship
- implementation state: VERIFIED_PARTIAL
- verification: adversarial benchmark and regression
- acceptance criteria: decision on merge/review/abstain behavior
- evidence: current scorecard and experimental tests
- blockers: external challenger breadth and post-baseline recalibration
- exit criteria: documented decision plus tests aligned
- release impact: unblocks person identity direction
- contract status: PASS for local contract tests, decision status is PROVISIONAL_COMPOSE
- benchmark evidence: operational auto-match authority is false; operational candidate matches 5/25 with 1 false positive; local contract test suite passed

### CAP-04 Evidence and Persistence

- objective: preserve raw evidence, integrity, and replay
- requirements: DR-001, QR-003
- dependencies: sqlite persistence and digest verification
- architecture decision: evidence remains separate from derived statements
- implementation state: VERIFIED
- verification: persistence and fault-injection tests
- acceptance criteria: tampering is rejected, replay remains deterministic
- evidence: persistence regression plus canonical domain round-trips
- blockers: none
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
- implementation state: VERIFIED_PARTIAL
- verification: runtime probes, integration checks, and local fallback adapter
- acceptance criteria: acquisition path documented and testable
- evidence: runtime adapter plus application chassis integration tests
- blockers: Crawlee breadth remains external and environment-dependent
- exit criteria: runtime choice is documented and wired
- release impact: enables scalable acquisition path
- contract status: VERIFIED_PARTIAL

### CAP-08 Domain and Persistence Transplant

- objective: transplant canonical domain, persistence codecs, and migration adapters onto the clean implementation line
- requirements: FR-003, FR-004, DR-001, DR-003, QR-002
- dependencies: baseline freeze, clean base, canonical domain records
- architecture decision: preserve legacy adapters while canonical records become first-class
- implementation state: VERIFIED
- verification: domain round-trips, migration, bridge, and ER integration tests
- acceptance criteria: new canonical types persist/load, compatibility layer remains explicit, relationship scope and statement bridge are test-backed
- evidence: canonical domain record tests, structural migration helpers, and full regression
- blockers: acquisition runtime breadth remains external; challenger breadth is post-baseline recalibration
- exit criteria: canonical core transplants without silent merge
- release impact: starts the clean implementation line
- contract status: VERIFIED

### CAP-09 Canonical Consumer Wiring and Operational Integration

- objective: wire canonical consumer flows through the runtime adapter, API chassis, qualification, review, export, and operational E2E
- requirements: FR-001, FR-003, FR-004, FR-005, FR-006, DR-001, DR-002, QR-001, OR-001, OR-002, CR-001
- dependencies: CAP-08, CAP-07, canonical export, and the application chassis
- architecture decision: thin application shell composes the canonical domain and a local fallback runtime adapter while Crawlee remains optional breadth
- implementation state: VERIFIED_PARTIAL
- verification: operational integration tests, health/readiness checks, canonical export, and full regression
- acceptance criteria: canonical consumer scope is explicit, runtime works without Crawlee, API surface exists, and canonical E2E passes
- evidence: canonical operational integration tests and full regression
- blockers: Crawlee breadth remains external; deployment topology remains lightly specified
- exit criteria: consumer wiring is stable and observable
- release impact: advances the system from canonical building blocks to operational integration
- contract status: VERIFIED_PARTIAL

### CAP-10 Operational Readiness, Recovery, and Send Gates

- objective: prove the system can be installed, started, observed, backed up, restored, recovered, and certified up to explicit external blockers
- requirements: OR-001, OR-002, OR-003, OR-004, CR-001, CR-002
- dependencies: CAP-09, operational lifecycle helpers, backup/restore path, live certification matrix, and SEND_READY state machine
- architecture decision: keep operational readiness separate from commercial send readiness and external live certification
- implementation state: VERIFIED_PARTIAL
- verification: startup/readiness checks, backup/restore, crash/recovery, structured events, live certification plan, and full regression
- acceptance criteria: local install/startup/recovery path is reproducible, operational health is explicit, and external certification remains a separate gate
- evidence: operational readiness tests, persistence backup/restore, and live certification matrix
- blockers: live certification and compliance remain external
- exit criteria: operational readiness is internally proven and externally blocked items are explicit
- release impact: advances the product from operational integration to operational control
- contract status: VERIFIED_PARTIAL

## Critical Path

Baseline documentation published
→ CAP-08 Domain and Persistence Transplant
→ CAP-04 Evidence and Persistence alignment
→ CAP-05 Contact Discovery and Validation
→ CAP-06 Qualification
→ CAP-07 Acquisition Runtime
→ CAP-09 Canonical Consumer Wiring and Operational Integration
→ CAP-10 Operational Readiness, Recovery, and Send Gates
→ integrated E2E and operational readiness

## Current Critical Path Item

CAP-10 Operational Readiness, Recovery, and Send Gates

## Next Unblocked Capability

CAP-10 Operational Readiness, Recovery, and Send Gates

## Blocked Capabilities

- none

## New Evidence

- canonical documentation baseline created
- project authority consolidated
- ER blockers remain benchmark dependent
- `LEGACY_CONTRACT_RECONCILIATION = COMPLETE`
- `INTERNAL_REGRESSION_SUITE = PASS` (`864 passed`, `24 skipped`, `1 xfailed`) at the wave 03 / baseline checkpoint
- skips and xfail are classified rather than hidden
- wave 03 local benchmark executed on sanctioned Windows runtime
- `Company ER` and `Person ER` are now `PROVISIONAL_COMPOSE`
- `ENGINEERING_BASELINE_ESTABLISHED = YES` (`fb774cc6ddc4f8c7fc397476f868bd1de3a70506`)
- clean implementation line created from the engineering baseline
- baseline freeze document recorded
- clean implementation transplant matrix recorded
- CAP-08 verified on the clean implementation line
- CAP-04 verified against the persistence regression and canonical round-trips
- CAP-07 verified partially with the local fallback runtime adapter and chassis
- CAP-09 canonical operational integration tests passed
- full regression suite passed with `868 passed`, `24 skipped`, `1 xfailed` at the wave 04 checkpoint
- full regression suite now passes with `872 passed`, `24 skipped`, `1 xfailed`
- CAP-10 operational readiness tests cover startup, health, readiness, backup, restore, recovery, SEND_READY, and live certification planning
- full regression suite now passes with `879 passed`, `24 skipped`, `1 xfailed`

## New Decisions

- canonical docs outrank experimental bake-off docs
- qualification remains separate from send readiness
- evidence must stay distinct from statements
- PERSON_ER_CONTRACT is passable independently of PERSON_ER_TECHNOLOGY_DECISION
- COMPANY_ER is provisionally composed from local benchmark evidence, with external challenger breadth still open
- CAP-07 Acquisition Runtime is verified partially on the local fallback adapter, not deferred
- CAP-08 Domain and Persistence Transplant is verified on the clean implementation line
- CAP-04 Evidence and Persistence is verified on the clean implementation line
- CAP-09 Canonical Consumer Wiring and Operational Integration is the next operational path
- BR-001 now narrows to Crawlee breadth, not the baseline runtime adapter
- CAP-10 Operational Readiness, Recovery, and Send Gates is the next operational path
- operational lifecycle helpers now cover startup, shutdown, backup, restore, recovery, and SEND_READY gating
- operational readiness remains separate from commercial SEND_READY and external live certification

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
| BR-003 | CAP-10 Operational Readiness / External Certification | EXTERNAL_DEPENDENCY | live source certification, compliance sign-off, and send authorization remain external to the current repo | external | yes | execute live certification matrix in an authorized environment and record the evidence IDs | operations/compliance | open |
