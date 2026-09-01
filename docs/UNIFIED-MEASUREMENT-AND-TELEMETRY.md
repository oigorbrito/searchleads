# Unified Measurement and Telemetry V1

## Work unit

`UNIFIED_MEASUREMENT_AND_TELEMETRY_V1`

This unit resolves #75 by porting the scientific measurement contract from legacy PR #25 onto the current clean stack. Existing work-unit evaluators remain authoritative for their own calibration fixtures; this layer provides one typed vocabulary for comparing what is actually measurable.

## Non-negotiable rule

```text
NO DENOMINATOR / GROUND TRUTH / HUMAN DECISION / COST / TIME
→ UNAVAILABLE(reason)
```

Missing information is never converted to zero and never estimated.

## Metric availability

Every rate is represented by `MetricValue`:

- `AVAILABLE`: numerical value exists, with numerator/denominator where applicable;
- `UNAVAILABLE`: value is `None` and a non-blank reason is mandatory.

A zero denominator produces `UNAVAILABLE`, not `0.0`.

## Discovery

- observed discovery count;
- unique entities;
- duplicate discovery rate;
- bounded coverage only when an explicit finite universe is supplied;
- discovery precision only when relevance ground truth is supplied.

WU17's 12/12 SERPRO result can therefore be represented as bounded source-page coverage. It must not be relabeled as market/web coverage.

## Entity resolution

Given labeled pair counts, the contract computes precision, recall, F1, false merge rate over labeled distinct pairs, and false split rate over labeled duplicate pairs. This supports the measured Company ER and Person ER calibration sets without turning fixture performance into production accuracy.

## Enrichment

The contract measures required-field coverage over explicit subject × field slots; field accuracy only with labeled field truth; provenance coverage over CandidateFacts plus CanonicalFacts whose clean Provenance carries Evidence; and conflict rate over canonical/conflicting evaluated field keys.

## Contacts

Immutable contact snapshots are deduplicated only for metric counting by `owner_id + contact kind + normalized logical value`. Email is case-folded, phone/WhatsApp strip non-digits, and URL-like values strip trailing `/` and case-fold. The latest assessment timestamp wins; ties use status rank solely for measurement snapshot selection. Domain records remain immutable.

`VALIDATED` keeps the SearchLeads meaning of publication corroboration; this contract does not reinterpret it as deliverability.

## Qualification

Qualification precision/recall require explicit labeled ground truth. `UNKNOWN` predictions are not silently converted to negative. Human disagreement requires explicit human decisions. WU20's Dental fixture is a calibration dataset; any report using it must carry a calibration scope rather than a production claim.

## Operation

Cost-per-unit metrics require explicit `total_cost`. Time-per-lead requires explicit elapsed seconds and processed-lead count. Without telemetry these remain `UNAVAILABLE(reason)`.

## Reproducible report entry point

`build_measurement_report(...)` creates a `MeasurementReport` with fixed schema `searchleads_measurement_v1` and mandatory non-blank `scope`. `to_json()` is deterministic (`sort_keys=True`, compact separators).

The caller is responsible for choosing an honest scope, for example `CALIBRATION_FIXTURE`, `BOUNDED_SOURCE_PAGE`, or a specifically identified production run. The contract deliberately does not infer scope from data.

## Verification

```text
FOCUSED_TESTS = 17/17 PASS
LINE_COVERAGE = 100%
BRANCH_COVERAGE = 100%
STATEMENTS = 102
BRANCHES = 40
COMPILEALL = PASS
```

Tests exercise missing denominators, zero denominators, labeled ER, false merge/split, enrichment provenance, logical-contact snapshot dedupe, qualification ground truth/human-review boundaries, missing cost/time telemetry, negative telemetry rejection and deterministic scoped report serialization.

## Gates

```text
MISSING_DENOMINATOR_AS_ZERO = NO
MISSING_GROUND_TRUTH_AS_ZERO = NO
MISSING_COST_AS_ESTIMATE = NO
MISSING_TIME_AS_ESTIMATE = NO
BOUNDED_DISCOVERY_COVERAGE = SUPPORTED
MARKET_COVERAGE_WITHOUT_UNIVERSE = UNAVAILABLE
ER_FALSE_MERGE_RATE = SUPPORTED
ER_FALSE_SPLIT_RATE = SUPPORTED
FIELD_ACCURACY_WITHOUT_LABELS = UNAVAILABLE
CONTACT_SNAPSHOT_DOUBLE_COUNTING = CONTROLLED
QUALIFICATION_WITHOUT_LABELS = UNAVAILABLE
HUMAN_DISAGREEMENT_WITHOUT_DECISIONS = UNAVAILABLE
DETERMINISTIC_SCOPED_REPORT = PASS
```

## Basis

- handoff measurement section
- legacy PR #25 (`11/11 PASS`)
- current WU17 discovery coverage
- current WU18 Person ER calibration
- current WU20 Dental qualification calibration
- issue #75
