# Company Field Fusion and Truth Discovery v1

## Work unit

`COMPANY_FIELD_FUSION_AND_TRUTH_DISCOVERY_V1`

This unit converts homogeneous company candidate facts into either an evidence-linked canonical value or an explicit unresolved conflict. It does not merge Company entities and does not claim that simple source majority equals truth.

## Pipeline

```text
candidate facts for one company + one field
→ choose effective representation (normalized if present, else raw)
→ group exact effective values
→ compute support diagnostics
→ unanimous agreement: fusion Provenance + CanonicalFact
→ disagreement: open Conflict
```

## Safety rules

- one `subject_id` and one `field_name` per fusion operation;
- duplicate `fact_id` input is rejected rather than counted twice;
- source candidates are never rewritten;
- canonical IDs and fusion provenance IDs are deterministic from subject, field, parent candidates, and value;
- canonical provenance unions all evidence IDs and records every parent candidate in `derived_from_fact_ids`;
- disagreement never selects a majority winner automatically;
- majority value/support ratio are diagnostics only.

## Benchmark

The deterministic local fixture has 32 adversarial scenarios:

- 10 raw unanimous scenarios;
- 8 normalized-equivalent scenarios;
- 6 scenarios where naive majority happens to be correct;
- 4 correlated-source scenarios where naive majority is wrong;
- 4 unresolved ties.

Known truth exists for 28/32 scenarios; ties deliberately have no truth label.

### Conservative unanimous policy

```text
AUTO_CANONICAL = 18
CORRECT_AUTO_CANONICAL = 18
FALSE_AUTO_CANONICAL = 0
OPEN_CONFLICTS = 14
AUTO_PRECISION = 100.0%
KNOWN_TRUTH_COVERAGE = 64.3% (18/28)
```

### Naive majority diagnostic

```text
CORRECT = 24
WRONG_OR_OVERCLAIM = 8
OVERALL_ACCURACY = 75.0%
KNOWN_TRUTH_ACCURACY = 85.7%
CORRELATED_WRONG_MAJORITY = 4/4
UNRESOLVED_TIE_OVERCLAIM = 4/4
```

The benchmark demonstrates why V1 refuses to convert support count into truth authority: correlated stale observations can outvote a newer/correct observation, and a deterministic tie-break can fabricate certainty where truth is deliberately unknown.

## Verification after runtime reconstruction

The execution runtime was recycled after the earlier 308-test run, so the head of PR #46 was re-read from GitHub by commit SHA before WU6 publication. The new WU6 module was then re-executed independently:

```text
WU6_FOCUSED_TESTS = 23/23 PASS
WU6_MODULE_LINE_COVERAGE = 100%
WU6_MEASURED_STATEMENTS = 134
BENCHMARK_REPRODUCED = PASS
PYTHON_MODULE_COMPILE = PASS
```

The existing clean base remains the published PR #46 snapshot, where the prior exact regression was 286/286 and 100% line coverage across 1,051 statements. That prior full-suite count is not relabeled as a fresh current-runtime full regression.

## Gate

```text
HOMOGENEOUS_FIELD_FUSION = PASS
RAW_CANDIDATES_REWRITTEN = NO
NORMALIZED_VALUE_PREFERRED_WHEN_PRESENT = YES
UNANIMOUS_CANONICALIZATION = PASS
DISAGREEMENT_AS_CONFLICT = PASS
FUSION_PROVENANCE = PASS
DERIVED_FROM_FACT_IDS = PASS
DUPLICATE_FACT_SUPPORT_INFLATION = BLOCKED
MAJORITY_OPERATIONAL_AUTHORITY = NO
SOURCE_AUTHORITY_WEIGHTS = NOT_DEFINED
FOCUSED_TESTS = PASS
LINE_COVERAGE_NEW_MODULE = 100%
ICP_DEFINED = NO
B2B_ASSUMPTION = PROVISIONAL
```

## Next work unit

`CONTACT_DISCOVERY_V1`.
