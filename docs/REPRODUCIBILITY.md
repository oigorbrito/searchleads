# Reproducibility

Status: `ARTIFACT_GUIDE`

This document describes how to reproduce the experimental chassis-harness execution and how to verify the resulting evidence artifacts. It does not claim independent reproduction or ACM artifact badges.

## Artifact inventory

Core harness artifacts:

- `.github/workflows/chassis-bakeoff.yml`: CI execution protocol;
- `tests/experimental/**`: functional probes and comparative experiments;
- `tests/fixtures/**`: curated regression/benchmark fixtures used by those experiments;
- `scripts/chassis_bakeoff_manifest.py`: environment manifest generator;
- `scripts/chassis_bakeoff_report.py`: deterministic evidence aggregator;
- `docs/EMPIRICAL-HARNESS-METHODOLOGY.md`: methodology contract;
- `docs/EMPIRICAL_CLAIM_CONTRACT_V1.json`: machine-readable claim contract.

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

Run the normal regression suite and preserve JUnit XML:

```text
python -m pytest -q -W error::ResourceWarning --junitxml=tmp/regression-junit.xml
```

Run the experimental suite and preserve JUnit XML:

```text
python -m pytest -q -s tests/experimental -W error::ResourceWarning --junitxml=tmp/experimental-junit.xml
```

The regression suite and the experimental suite are separate artifacts. A regression result must not be interpreted as a benchmark result.

## Canonical study report

Build a deterministic report from the preserved artifacts:

```text
python scripts/chassis_bakeoff_report.py \
  --study-id local-core-bakeoff \
  --manifest tmp/chassis-manifest.json \
  --junit tmp/regression-junit.xml tmp/experimental-junit.xml \
  --output tmp/study-report.json
```

Optional structured observation JSON files may be supplied with repeated values after `--observation`.

Optional claim files conforming to `docs/EMPIRICAL_CLAIM_CONTRACT_V1.json` may be supplied with repeated values after `--claim`.

The report includes SHA-256 hashes for every input artifact. Re-running the report generator over byte-identical inputs with the same `study_id` must produce semantically identical JSON and the same `report_sha256`.

## Claim traceability

Every path listed in a claim's `input_artifacts` must be present in the input bundle passed to the report generator.

If an input is missing, the report preserves the claim's declared evidence state as `declared_evidence_state` and materializes the effective `evidence_state` as `INSUFFICIENT_EVIDENCE`.

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

This is intended to preserve available evidence even when a later test step fails. A missing file is not silently reconstructed by the analysis layer.

A successful job may include:

- `manifest.json`;
- regression and/or experimental JUnit XML;
- `study-report.json`.

A failed job may contain only the artifacts produced before failure. Interpret absent downstream artifacts as absent evidence.

## Verification criteria

A reproduction attempt should verify at least:

1. repository SHA is identified;
2. Python/runtime environment is recorded;
3. required dependencies are present at the intended versions;
4. external dataset commit/hash identity is preserved;
5. JUnit artifacts are retained;
6. canonical report hashes point to the actual input bytes;
7. claims reference present artifacts or are downgraded to `INSUFFICIENT_EVIDENCE`;
8. no active decision is inferred solely from missing, skipped, or static evidence.

## Reproduction terminology

A second run by the same project is not automatically `EXTERNAL_REPRODUCTION`.

When reporting reproduction, identify whether it is internal or external and describe whether the replication relation is exact, methodological, or conceptual, together with any changes in protocol, data, environment, or implementation.

## Known limitations

- GitHub-hosted execution and local execution can differ in hardware, scheduling, and installed-package resolution metadata.
- JUnit captures execution status, not all raw benchmark measurements.
- Individual experimental modules must emit structured observation artifacts when their scientific claim depends on measurements not represented by JUnit.
- Live operational evidence may require network access or credentials and must be reported separately from offline controlled evidence.
