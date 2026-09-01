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

## Structured observation contract

Experimental measurements that are needed to interpret a research question must be persisted as structured JSON rather than existing only in stdout or a human scorecard.

The machine-readable contract is `docs/EMPIRICAL_OBSERVATION_CONTRACT_V1.json`. The current observation envelope is `searchleads_empirical_observation_v1` and contains:

- `observation_id`: stable identifier for the observation artifact;
- `research_question`: the question the observation addresses;
- `method`: the concrete procedure class used to obtain it;
- `evidence_class`: one value from the evidence taxonomy above;
- `payload`: raw structured outcomes and measurements needed for later analysis;
- `validity_limits`: study-specific limits on what may be inferred.

`scripts/empirical_observation.py` writes these files only when `SEARCHLEADS_EMPIRICAL_OBSERVATION_DIR` is configured. Local tests therefore remain executable without manufacturing an evidence bundle.

Observation files are deterministic with respect to their supplied content: no current timestamp or random report identifier is inserted. Reusing an `observation_id` with different content in one output directory is rejected.

An observation is not a claim and is not a decision. The observation layer must not assign empirical `SUPPORTED` merely because a test assertion passed. Evidence state belongs to a claim after the required observations, execution artifacts, analysis, and validity limits are available.

## Initial structured-observation scope

Structured output is initially enabled only where the current tests already contain a concrete empirical or functional research question and non-JUnit measurements:

- runtime retry/state/recovery probes;
- runtime adapter identity, retry mapping, and filesystem persistence probes;
- runtime capability inspection, explicitly classified as `STATIC_INSPECTION`;
- FollowTheMoney↔SearchLeads Evidence bridge cardinality, identifier-overload negative control, and lineage-responsibility probes;
- company-name normalization comparison on the frozen adversarial corpus;
- legal-form collision guard ablation;
- downstream company-ER normalization ablation;
- registry-conflict invariant under aggressive name normalization;
- CNPJ comparison with the declared Receita/Serpro oracle;
- checksum-invalid CNPJ planner-admission probe.

This list is not a requirement to convert every experimental test. Tests whose only purpose is validating the measurement implementation itself are not promoted into empirical observations.

Additional tests should emit structured observations only when their research question requires measurements that are not adequately represented by preserved execution-state artifacts.

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

`observations` is a list of stable `observation_id` values required by the claim, not free-form prose.

A claim cannot use `winner`, `better`, popularity, feature count, or a composite opaque score as evidence.

## Traceability rule

Every file named by `input_artifacts` must be present in the artifact bundle used to build the canonical study report. Every `observation_id` named by a claim must also be present in the validated observation bundle.

If either a required input artifact or a required observation is missing, `scripts/chassis_bakeoff_report.py` materializes the effective evidence state as `INSUFFICIENT_EVIDENCE`. It preserves the declared state separately as `declared_evidence_state` for auditability.

The report also records whether the current evidence is eligible to support an active decision. Missing inputs, missing observations, or an evidence state weaker than `SUPPORTED` never authorize an active architecture decision from the harness.

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

A deterministic benchmark may justify not repeating byte-identical computations when repeated executions would not estimate stochastic variance, but it must retain the individual case/pair outcomes needed to recompute its aggregate metrics.

A functional probe must not be relabeled as a benchmark merely because it produces a number.

A regression fixture must not be relabeled as production ground truth.

Metrics that require ground truth are `UNAVAILABLE(reason)` when defensible ground truth is absent.

## Analysis discipline

`scripts/chassis_bakeoff_report.py` performs deterministic evidence aggregation. It validates the structured-observation envelope, rejects duplicate `observation_id` values, hashes each observation artifact, and preserves the observation payload in the canonical report.

It does not:

- compute a winner score;
- apply arbitrary weights;
- promote a feature-presence observation into production benefit;
- convert a synthetic benchmark into a universal conclusion;
- convert a passing functional probe directly into an active architecture decision;
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
