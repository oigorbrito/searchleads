# Empirical Harness Methodology

Status: `METHODOLOGY_CONTRACT`

## Purpose

The chassis bake-off is an experimental harness. It may produce observations, controlled comparisons, hypotheses, and evidence-backed engineering input. It is not production authority and does not promote a challenger by itself.

The harness follows the project's adopted methodological references:

- ACM SIGSOFT Empirical Standards for Software Engineering Research, especially the General Standard, Engineering Research, Benchmarking of Software Systems, and Replication guidance when applicable;
- ACM Artifact Review and Badging criteria as internal quality guidance for documented, consistent, complete, exercisable, and verifiable artifacts.

The project does not claim ACM badges from this internal use.

## Evidence taxonomy

Every material claim must identify one evidence class:

- `STATIC_INSPECTION`: API, documentation, or source inspection. It may establish capability presence or generate a hypothesis, but does not establish comparative operational benefit.
- `FUNCTIONAL_PROBE`: a bounded executable demonstration under declared conditions. It establishes that the tested behavior occurred under those conditions.
- `CONTROLLED_BENCHMARK`: a repeated or otherwise methodologically justified comparison under a declared workload and environment.
- `INTERNAL_REPRODUCTION`: a repeated study by the same project/team with the relevant protocol and artifacts identified.
- `EXTERNAL_REPRODUCTION`: a reproduction by an independent party or team under an explicitly described replication relation.
- `LIVE_OPERATIONAL_EVIDENCE`: evidence from a bounded real-source or operational execution. It is not automatically a controlled benchmark.
- `HUMAN_OR_EXTERNAL_AUTHORITY`: legal, professional, compliance, or other authority outside the experimental harness.

Evidence classes do not automatically upgrade into stronger classes.

## Evidence state and decision state are independent

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

A decision label is not evidence. In particular, `ADOPT`, `COMPOSE`, `RETAIN`, and `REJECT` do not mean that an empirical claim is supported.

Historical architecture documents may retain their recorded engineering decisions while explicitly distinguishing those decisions from the evidence available at the time.

## Claim contract

Machine-readable claims use `EMPIRICAL_CLAIM_CONTRACT_V1.json` and contain, at minimum:

- `claim_id`
- `research_question`
- `method`
- `evidence_class`
- `input_artifacts`
- `observations`
- `analysis`
- `validity_limits`
- `supported_conclusion`
- `unsupported_conclusions`
- `evidence_state`
- `decision_state`

A claim cannot use `winner`, `better`, popularity, feature count, or a composite opaque score as evidence.

## Traceability rule

Every file named by `input_artifacts` must be present in the artifact bundle used to build the canonical study report.

If a required artifact is missing, `scripts/chassis_bakeoff_report.py` materializes the effective evidence state as `INSUFFICIENT_EVIDENCE`. It preserves the declared state separately as `declared_evidence_state` for auditability.

The report also records whether the current evidence is eligible to support an active decision. Missing inputs or an evidence state weaker than `SUPPORTED` never authorize an active architecture decision from the harness.

## Raw evidence retention

The harness preserves, when available:

- repository SHA;
- Python implementation and version;
- platform/runtime metadata;
- dependency versions or explicit absence;
- raw JUnit XML;
- structured observation JSON when a probe produces it;
- claim files;
- SHA-256 for every input artifact;
- the canonical derived study report.

A summary does not replace raw observations.

## Benchmark discipline

A benchmark must identify its research question, baseline, challenger, workload, environment, metrics, procedure, repetitions or justification for limited executions, analysis method, limitations, and threats to validity.

A functional probe must not be relabeled as a benchmark merely because it produces a number.

A regression fixture must not be relabeled as production ground truth.

Metrics that require ground truth are `UNAVAILABLE(reason)` when defensible ground truth is absent.

## Analysis discipline

`scripts/chassis_bakeoff_report.py` performs deterministic evidence aggregation. It does not:

- compute a winner score;
- apply arbitrary weights;
- promote a feature-presence observation into production benefit;
- convert a synthetic benchmark into a universal conclusion;
- promote experimental output into production authority.

It may summarize JUnit execution states and preserve structured observations, but interpretation belongs in explicit claims with validity limits.

## Claims and language

Use these distinctions in documentation:

- `OBSERVATION`: directly recorded behavior or static fact;
- `HYPOTHESIS`: proposition requiring empirical evaluation;
- `EMPIRICAL_RESULT`: result produced under a declared method and context;
- `INTERPRETATION`: bounded meaning assigned to the result;
- `DECISION`: engineering action, recorded separately from evidence state.

Terms such as `REPLACE`, `COMPOSE`, or `RETAIN` are decision vocabulary only. They must not be used as shorthand for empirical superiority.

## Threats to validity

Threats must be specific to the study. When applicable, address construct, internal, conclusion, and external validity, together with reliability, objectivity, and reproducibility.

A generic threats checklist is insufficient.

## Suggestions

A future harness improvement is eligible only when it identifies:

- motivation;
- methodological basis or demonstrated functional need;
- current evidence;
- missing evidence;
- experiment required;
- acceptance/rejection criteria;
- threats;
- decision state.

Otherwise classify it as `UNSUPPORTED_SUGGESTION` and do not implement it solely as a harness recommendation.
