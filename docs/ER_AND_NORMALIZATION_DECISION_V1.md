# ER_AND_NORMALIZATION_DECISION_V1

Status: `HISTORICAL_DECISION_RECORD`.

This file preserves earlier engineering decisions for entity resolution, normalization, and identifier validation. It is not a canonical benchmark result under the current empirical harness methodology.

## Scope

The historical record covers:

- Company ER;
- Person ER;
- normalization;
- CNPJ canonicalization/validation;
- benchmark-harness quality constraints.

## Methodological reading rule

Legacy decision labels such as `COMPOSE`, `REPLACE`, and `PROVISIONAL_COMPOSE` are engineering decisions, not evidence states.

A current comparative ER or normalization claim must identify preserved input artifacts, a declared method, its validity limits, and an `evidence_state` under `EMPIRICAL-HARNESS-METHODOLOGY.md`.

If the raw benchmark inputs/results needed for a legacy claim are not present in the current reproducible bundle, the current state is `INSUFFICIENT_EVIDENCE` or `NOT_EVALUATED` rather than an inferred winner.

## Historical decisions

| Component | Historical decision | Current interpretation |
|---|---|---|
| Company ER | `PROVISIONAL_COMPOSE` | historical review-first composition; current comparative superiority requires traceable controlled evidence |
| Person ER | `PROVISIONAL_COMPOSE` | historical review-first composition with no general auto-match authority; comparative quality requires traceable controlled evidence |
| Normalization boundary | `COMPOSE` | raw values remain separate from normalization features and identity decisions; library superiority is a separate empirical question |
| CNPJ validation | `REPLACE` for shape-only admission control | correctness distinction between canonicalization and formal validation is retained; comparative library superiority is not implied |

Under the current vocabulary these are preserved as historical decision provenance, not as `SUPPORTED` empirical claims by themselves.

## Boundary invariants retained

The following design constraints remain independently meaningful:

```text
raw source value
    -> explicit normalization/canonicalization
    -> feature or validated identifier
    -> entity-resolution or routing decision as a separate step
```

- raw source values and Evidence remain intact;
- normalized strings do not authorize identity merge by themselves;
- legal-form removal or other lossy transforms remain explicit policy choices;
- Company ER and Person ER remain separate research/evaluation questions;
- CNPJ canonicalization and CNPJ validity are distinct concepts;
- invalid identifiers should not be admitted to network routing merely because their shape can be normalized.

These are product/correctness boundaries. They do not establish that one candidate library is empirically better than another.

## Harness properties worth preserving

The original harness intentionally separated several sources of bias/confounding:

- Company and Person ER are evaluated separately;
- calibration/training inputs are separated from held-out evaluation where the study defines those roles;
- external canonical data is not silently fed into matcher features when it is intended as evaluation data;
- normalization ablations hold non-normalization behavior fixed where possible;
- identifier canonicalization is tested separately from validity.

These properties support a defensible protocol, but protocol quality does not imply a benchmark outcome.

## Current claim states

| Claim | Required evidence | Current state absent a canonical artifact bundle |
|---|---|---|
| one Company ER candidate has better precision/recall or false-merge behavior | labeled ground truth + controlled comparable execution + raw observations | `NOT_EVALUATED` |
| one Person ER candidate has better false-merge/false-split behavior | labeled ground truth + controlled comparable execution + raw observations | `NOT_EVALUATED` |
| a normalization candidate improves downstream ER | controlled ablation with fixed matcher/workload + raw observations | `NOT_EVALUATED` |
| shape-only CNPJ canonicalization is equivalent to formal validation | official validity contract contradicts equivalence | `NOT_SUPPORTED` |
| formal validation can reject invalid identifiers that shape normalization accepts | functional/official-contract evidence | `SUPPORTED` as a correctness distinction, not a library winner |

## No opaque winner language

The following are not authorized by this file alone:

- `winner`;
- `best matcher`;
- `better normalization`;
- `strong +` quality assertions;
- production-accuracy claims;
- universal ER superiority.

A current claim may use a bounded comparative statement only when the canonical report points to the raw observations and validity limits that support it.

## Current authority

Use this record to understand historical architecture choices and invariants. Use the empirical harness artifacts and machine-readable claim contract for current evidence authority.
