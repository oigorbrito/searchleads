# Empirical Harness Methodology

Status: `METHODOLOGY_CONTRACT`

## Purpose

The SearchLeads empirical harness produces bounded observations and evidence-backed engineering input. It is not production authority and does not promote a challenger, dependency, architecture, commercial state, or compliance decision by itself.

## Evidence taxonomy

Every material claim must identify one evidence class:

- `STATIC_INSPECTION`
- `FUNCTIONAL_PROBE`
- `CONTROLLED_BENCHMARK`
- `INTERNAL_REPRODUCTION`
- `EXTERNAL_REPRODUCTION`
- `LIVE_OPERATIONAL_EVIDENCE`
- `HUMAN_OR_EXTERNAL_AUTHORITY`

Evidence classes do not automatically upgrade into stronger classes.

## Evidence state and decision state

Evidence state:

- `SUPPORTED`
- `PARTIALLY_SUPPORTED`
- `NOT_SUPPORTED`
- `NOT_EVALUATED`
- `INSUFFICIENT_EVIDENCE`
- `REPLICATION_REQUIRED`

Decision state:

- `ADOPT`
- `COMPOSE`
- `RETAIN`
- `DEFER`
- `REJECT`
- `HISTORICAL_DECISION`

Decision labels are not evidence. Passing tests or functional probes do not automatically authorize an active architecture or commercial decision.

## Structured observations

Machine-readable observations conform to `docs/EMPIRICAL_OBSERVATION_CONTRACT_V1.json` and use schema version `searchleads_empirical_observation_v1`.

`scripts/empirical_observation.py` writes deterministic observation JSON only when `SEARCHLEADS_EMPIRICAL_OBSERVATION_DIR` is configured. Reusing one `observation_id` with different content is rejected.

An observation is not a claim. It must not be promoted to `SUPPORTED` merely because a test assertion passed.

## Claims and traceability

Machine-readable claims conform to `docs/EMPIRICAL_CLAIM_CONTRACT_V1.json`.

Every path named by `input_artifacts` must be present in the evidence bundle. Every `observation_id` named by a claim must be present in the validated observation bundle.

If required evidence is missing, `scripts/chassis_bakeoff_report.py` preserves the declared state as `declared_evidence_state` and materializes effective `evidence_state=INSUFFICIENT_EVIDENCE`.

Missing inputs, missing observations, `DEFER`, `HISTORICAL_DECISION`, or evidence weaker than `SUPPORTED` cannot authorize an active decision from the harness.

## Raw evidence retention

Preserve when applicable:

- repository SHA;
- Python/runtime metadata;
- relevant dependency versions or explicit absence;
- raw JUnit XML;
- structured observation JSON;
- claim files;
- SHA-256 of input artifacts;
- deterministic derived report.

A summary does not replace raw evidence.

## Benchmark discipline

A controlled benchmark must identify its research question, baseline, challenger, workload, environment, metrics, procedure, repetitions or justification, analysis, limitations, and threats to validity.

A functional probe must not be relabeled as a benchmark merely because it emits a number. A regression fixture is not production ground truth.

## Interpretation boundary

Use these distinctions:

- `OBSERVATION`: directly recorded behavior or fact;
- `HYPOTHESIS`: proposition requiring evaluation;
- `EMPIRICAL_RESULT`: result under a declared method and context;
- `INTERPRETATION`: bounded meaning assigned to the result;
- `DECISION`: engineering action recorded separately from evidence state.

The harness must not convert feature presence, popularity, a synthetic score, skipped execution, or missing evidence into superiority or production authority.

## Blocker discipline

Missing optional dependencies, runner provisioning, credentials, external services, or unavailable datasets are blockers for the smallest affected block. They do not convert unexecuted work into PASS and do not terminate independent work in the same closure wave.
