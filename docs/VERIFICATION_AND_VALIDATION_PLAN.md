# VERIFICATION_AND_VALIDATION_PLAN

Status: CANONICAL

## Test Taxonomy

### Unit

- purpose: verify isolated functions and invariants
- environment: local Python runtime
- evidence generated: pass/fail test results
- semantics: deterministic failure means code defect or contract mismatch

### Contract

- purpose: verify public model/API contracts
- environment: local runtime, focused fixtures
- evidence generated: contract conformance results
- semantics: contract regressions fail explicitly

### Invariant

- purpose: enforce domain and persistence invariants
- environment: local runtime and ephemeral storage
- evidence generated: invariant violations or passes
- semantics: any silent acceptance of invalid state is a failure

### Migration

- purpose: verify schema and ledger transitions
- environment: sqlite-backed ephemeral database
- evidence generated: migration and repair results
- semantics: corrupted or incompatible schema must be rejected or repaired explicitly

### Adversarial

- purpose: probe false-positive and false-merge risk
- environment: curated benchmark fixtures
- evidence generated: comparison metrics
- semantics: ambiguity should lead to review, not silent merge

### Benchmark

- purpose: compare alternatives under fixed fixtures
- environment: controlled fixture set
- evidence generated: metric table and winner/deferral state
- semantics: no PASS without executable results
- current internal state: local regression suite passed (`879 passed`, `24 skipped`, `1 xfailed`)
- skip semantics: external-dependency skips are classified, not treated as hidden failures
- xfail semantics: retained only when marked `TEST_OBSOLETE` or another explicit intentional category

### Fault Injection

- purpose: verify corruption, tampering, and mismatch handling
- environment: local mutated fixtures or storage
- evidence generated: explicit rejection errors
- semantics: blocked infrastructure is not test failure

### Integration

- purpose: verify component composition
- environment: local repo runtime
- evidence generated: cross-module pass/fail result
- semantics: component contracts must still hold when composed

### E2E

- purpose: verify end-to-end workflow behavior
- environment: full local workflow path
- evidence generated: runnable end-to-end result
- semantics: no hidden mocks for claims of end-to-end coverage

### Operational

- purpose: verify startup, shutdown, recovery, backup, restore, and SEND_READY gating
- environment: local file-backed SQLite and runtime helpers
- evidence generated: operational lifecycle results and recovery artifacts
- semantics: operational readiness is separate from live certification

### Live Certification

- purpose: validate against external/live systems or live operational conditions
- environment: authorized live path
- evidence generated: external confirmation and artifact records
- semantics: live certification is separate from internal verification

## Global Rule

`INFRASTRUCTURE_BLOCKED` != `TEST_FAILED`

If the runner, dependency, or external service is unavailable, report blocked evidence rather than a failing product assertion.
