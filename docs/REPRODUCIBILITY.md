# Reproducibility

Status: `ARTIFACT_GUIDE`

This document describes how to reproduce the experimental chassis-harness execution and how to verify the resulting evidence artifacts. It does not claim independent reproduction or ACM artifact badges.

## Artifact inventory

Core harness artifacts:

- `.github/workflows/chassis-bakeoff.yml`: CI execution protocol;
- `tests/experimental/**`: functional probes and comparative experiments;
- `tests/fixtures/**`: curated regression/benchmark fixtures used by those experiments;
- `scripts/chassis_bakeoff_manifest.py`: environment manifest generator;
- `scripts/empirical_observation.py`: opt-in deterministic structured-observation writer;
- `scripts/chassis_bakeoff_report.py`: deterministic evidence aggregator;
- `docs/EMPIRICAL-HARNESS-METHODOLOGY.md`: methodology contract;
- `docs/EMPIRICAL_OBSERVATION_CONTRACT_V1.json`: machine-readable observation contract;
- `docs/EMPIRICAL_CLAIM_CONTRACT_V1.json`: machine-readable claim contract;
- `docs/EMPIRICAL_HARNESS_BLOCKER_REGISTER.md`: blocker ledger that scopes external/runtime blockers without terminating independent work.

External pinned artifact currently used by the workflow:

- `dedupeio/dedupe` commit `3f61e79102910bd355e920a2df7e44c14c9cb247`;
- sparse paths `benchmarks/benchmarks/datasets/restaurant-1.csv` and `restaurant-2.csv`.

## Supported Python environments

The chassis bake-off workflow currently exercises Python 3.11 and 3.12.

The production/internal-RC workflow may exercise additional versions; that does not automatically extend the empirical harness environment.

## Core dependency set

The core bake-off job installs pinned challenger dependencies:

- `followthemoney==4.10.2`
- `nomenklatura==4.14.0`
- `crawlee==1.9.3`
- `rigour==2.3.1`
- `python-stdnum==2.2`

The Yente application probe is isolated and installs `yente==5.5.0` separately.

`pytest` is installed as the test runner. The generated manifest records the version actually resolved in the execution environment.

## Local preparation

From the repository root, install the dependencies required for the study you intend to execute. Do not infer PASS for experiments whose optional dependencies are absent.

A missing optional dependency that causes an experiment to skip is reported as not executed in that environment, not as favorable evidence for either candidate.

## Environment manifest

Generate a manifest before running the experiment:

```text
python scripts/chassis_bakeoff_manifest.py --output tmp/chassis-manifest.json
```

The manifest records:

- repository SHA when available;
- Python version, implementation, and executable;
- OS/runtime metadata;
- versions or explicit absence of the known bake-off dependencies;
- selected GitHub Actions run identifiers when executed in CI.

It does not enumerate arbitrary environment variables and must not contain secrets.

## Core execution

Compile the repository:

```text
python -m compileall -q src scripts
```

Run the normal regression suite and preserve JUnit XML. The regression run explicitly excludes `tests/experimental` so regression correctness and experimental outcomes are separate artifacts:

```text
python -m pytest -q tests --ignore=tests/experimental -W error::ResourceWarning --junitxml=tmp/regression-junit.xml
```

To preserve structured empirical observations, configure an output directory only for the experimental execution.

PowerShell:

```text
$env:SEARCHLEADS_EMPIRICAL_OBSERVATION_DIR = "tmp/observations"
python -m pytest -q -s tests/experimental -W error::ResourceWarning --junitxml=tmp/experimental-junit.xml
```

POSIX shell:

```text
SEARCHLEADS_EMPIRICAL_OBSERVATION_DIR=tmp/observations \
python -m pytest -q -s tests/experimental -W error::ResourceWarning --junitxml=tmp/experimental-junit.xml
```

When the environment variable is absent, the tests still execute but no structured observation bundle is materialized. Absence of that bundle must not be silently treated as equivalent evidence.

The regression suite and the experimental suite are separate artifacts. A regression result must not be interpreted as a benchmark result.

## Failure collection and blocker discipline

The CI workflow is designed to collect as much independent evidence as possible before enforcing the final job result.

For steps whose failure does not make later evidence collection meaningless, the workflow records the step outcome and continues. Regression, experimental probes, canonical report construction, and artifact upload therefore do not automatically disappear merely because an earlier independent block failed.

The final enforcement step still returns a failing job when any required block failed. `continue-on-error` is used for evidence collection, not for converting failure into success.

Examples:

- a failed regression does not suppress experimental JUnit/observation collection;
- a failed experimental probe does not suppress available report/artifact collection;
- a missing or failed external dataset checkout does not prevent independent SearchLeads regression from executing;
- an install/runtime blocker is recorded by the final gate rather than being narrated as a favorable benchmark result;
- artifact upload uses `if: always()` so partial evidence is retained.

A blocker in one block does not authorize conclusions about another block. The final job status and the per-step outcomes must both be consulted when interpreting a run.

Concrete blockers are recorded in `docs/EMPIRICAL_HARNESS_BLOCKER_REGISTER.md`. Each row identifies the smallest affected block, evidence, impact, independent work that may continue, and its unblock condition. Runner failure, missing credentials, an external service, or an absent optional runtime is therefore a blocker-register entry, not an automatic end to the closing wave.

## Structured observations

Each emitted observation JSON conforms to `docs/EMPIRICAL_OBSERVATION_CONTRACT_V1.json`, uses schema version `searchleads_empirical_observation_v1`, and records:

- stable `observation_id`;
- research question;
- method;
- evidence class;
- structured payload;
- study-specific validity limits.

Observation JSON is raw study output for analysis purposes. It is not a claim and carries no automatic `SUPPORTED` state.

For deterministic benchmarks, the observation should retain individual case/pair outcomes and document why repeated identical executions are not being used to estimate stochastic variance. Aggregate metrics must remain recomputable from the retained outcomes where applicable.

The current observation-producing modules cover runtime/recovery, runtime adapter identity/persistence, FTM↔SearchLeads Evidence bridge cardinality/lineage probes, normalization, normalization-to-ER ablation, and CNPJ oracle/admission probes. Tests that only validate the measurement framework itself are not converted into empirical evidence.

The FTM evidence-bridge probes emit four bounded `FUNCTIONAL_PROBE` observations only when the observation output directory is configured. They establish no active architecture decision and remain `NOT_EVALUATED` until an execution bundle exists.

## Canonical study report

Build a deterministic report from the preserved artifacts:

```text
python scripts/chassis_bakeoff_report.py \
  --study-id local-core-bakeoff \
  --manifest tmp/chassis-manifest.json \
  --junit tmp/regression-junit.xml tmp/experimental-junit.xml \
  --observation-dir tmp/observations \
  --output tmp/study-report.json
```

Individual structured observation JSON files may alternatively be supplied after `--observation`. `--observation-dir` loads the JSON files directly inside the named directory in deterministic path order.

Optional claim files conforming to `docs/EMPIRICAL_CLAIM_CONTRACT_V1.json` may be supplied with repeated values after `--claim`.

The report validates observation schema/evidence class, rejects duplicate observation IDs, and includes SHA-256 hashes for every input artifact. Re-running the report generator over byte-identical inputs with the same `study_id` must produce semantically identical JSON and the same `report_sha256`.

## Claim traceability

Every path listed in a claim's `input_artifacts` must be present in the input bundle passed to the report generator. Every stable `observation_id` listed in the claim's `observations` must also be present in the validated observation bundle.

If either a required artifact or a required observation is missing, the report preserves the claim's declared evidence state as `declared_evidence_state` and materializes the effective `evidence_state` as `INSUFFICIENT_EVIDENCE`.

This behavior prevents a documentation claim from remaining empirically supported after its required evidence has been removed from the reproducible bundle.

## JUnit interpretation boundary

The report generator extracts only execution-state counts from JUnit XML:

- tests;
- passed;
- failures;
- errors;
- skipped.

These counts establish what executed and its test-run state. They do not by themselves establish research validity, production superiority, or an architecture decision.

## Raw artifact preservation in CI

Each bake-off job uploads its `.artifacts/<job>-<python>/` directory with `if: always()`.

This is intended to preserve available evidence even when another test or analysis block fails. A missing file is not silently reconstructed by the analysis layer.

A core job may include:

- `manifest.json`;
- regression and experimental JUnit XML;
- `observations/*.json` for experiments that emit structured observations;
- `study-report.json` containing the validated observation bundle.

A failed job may still contain all of those artifacts if the failure occurred in a block that did not prevent evidence collection. Conversely, an early runtime/setup failure may leave only partial artifacts. Interpret absent downstream artifacts as absent evidence.

## Verification criteria

A reproduction attempt should verify at least:

1. repository SHA is identified;
2. Python/runtime environment is recorded;
3. required dependencies are present at the intended versions;
4. external dataset commit/hash identity is preserved;
5. regression JUnit excludes the experimental directory;
6. experimental JUnit is retained separately;
7. structured observations needed by the research question are retained and schema-valid;
8. deterministic benchmark observations retain individual outcomes or an equivalent recomputable raw representation;
9. canonical report hashes point to the actual input bytes;
10. duplicate observation identifiers are rejected rather than silently overwritten;
11. claims reference present artifacts and observation IDs or are downgraded to `INSUFFICIENT_EVIDENCE`;
12. final workflow failure is not hidden by intermediate evidence-collection continuation;
13. blockers are scoped in the blocker register rather than terminating independent work;
14. no active decision is inferred solely from missing, skipped, static, or passing-probe evidence.

## Reproduction terminology

A second run by the same project is not automatically `EXTERNAL_REPRODUCTION`.

When reporting reproduction, identify whether it is internal or external and describe whether the replication relation is exact, methodological, or conceptual, together with any changes in protocol, data, environment, or implementation.

## Known limitations

- GitHub-hosted execution and local execution can differ in hardware, scheduling, and installed-package resolution metadata.
- JUnit captures execution status, not all raw benchmark measurements.
- Structured observation coverage is intentionally incremental and currently limited to experiments with already-defined research questions and non-JUnit measurements.
- Current observation files preserve measured outcomes, but do not yet encode a universal statistical-analysis layer; analysis remains claim-specific.
- Live operational evidence may require network access or credentials and must be reported separately from offline controlled evidence.
