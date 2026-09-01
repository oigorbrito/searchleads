# Empirical Harness Reporting Plan V1

Status: `IMPLEMENTATION_PLAN`

This branch implements the methodology-governed reporting layer for the experimental chassis harness. It does not change production authority, add challengers, or introduce winner scoring.

## Methodological basis

The implementation is limited to requirements supported by empirical software-engineering and reproducibility criteria already adopted by the project:

- preserve raw observations and environment metadata;
- derive analysis deterministically from preserved observations;
- keep evidence strength separate from engineering decision state;
- make every claim traceable to its source artifacts;
- represent missing evidence explicitly rather than infer a favorable result;
- keep experiment output machine-readable and auditable.

## Scope

1. Add a deterministic canonical study report aggregator.
2. Add a machine-readable claim contract with separate `evidence_state` and `decision_state`.
3. Add focused tests for determinism, traceability, missing-evidence behavior, and vocabulary validation.
4. Update the empirical-harness and reproducibility documentation to describe the contract and report-generation procedure.

## Explicit non-goals

- no opaque winner score;
- no new challenger;
- no new benchmark workload;
- no statistical test without a concrete research question that requires it;
- no promotion from experimental evidence to production authority;
- no automatic architecture replacement decision.
