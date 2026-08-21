# WORK UNIT 06 REPORT — COMPANY_FIELD_FUSION_AND_TRUTH_DISCOVERY_V1

## Scope

This work unit implements conservative per-field fusion over existing `CandidateFact` records and makes conflicting values explicit. It does not add a source-authority ranking, learned truth-discovery weights, contact discovery, person discovery, lead qualification, or cross-company merge automation.

## Implemented behavior

```text
CandidateFact[] for one subject + predicate
→ effective value = normalized_value when present, else raw_value
→ group equivalent values
→ unanimous value: CanonicalFact
→ disagreement: open Conflict
```

Canonical provenance is the union of supporting evidence IDs. Candidate facts remain unchanged. IDs are deterministic from subject, predicate, candidate set, and canonical value where applicable.

## Conflict policy

V1 deliberately does **not** treat observation count as truth. When values disagree, a majority value and support ratio may be reported as diagnostics, but no canonical fact is created automatically.

Reason: repeated/correlated observations can make a stale or wrong value appear to have majority support, and the current system has no validated source-independence or source-authority model.

## Benchmark

Curated local benchmark: **32 scenarios**.

Categories:

- 10 unanimous scenarios;
- 8 normalized-equivalent scenarios;
- 6 cases where naive majority happens to be correct;
- 4 cases where correlated repeated observations make naive majority wrong;
- 4 unresolved ties where available evidence should not produce a canonical value.

### Conservative unanimous policy

```text
auto_canonical = 18
correct_auto = 18
false_auto = 0
open_conflicts = 14
auto_precision = 100.0%
known_truth_coverage = 64.3%  (18 / 28 truth-known scenarios)
```

### Naive majority diagnostic

```text
correct = 24
wrong_or_overclaim = 8
overall_accuracy = 75.0%
known_truth_accuracy = 85.7%  (24 / 28)
unresolved_conflict_overclaims = 4 / 4
correlated_wrong_majorities = 4 / 4
```

The benchmark therefore supports the conservative policy for automatic canonicalization. Majority is useful as review context, not as truth.

## Validation

```text
TESTS_DISCOVERED = 72
TESTS_EXECUTED = 72
TESTS_PASSED = 72
```

Reproduce:

```bash
python -m unittest discover -s tests -v
python scripts/evaluate_field_fusion.py
```

## Gate

```text
PER_FIELD_FUSION = PASS
NORMALIZED_EQUIVALENCE = PASS
CANONICAL_FACT_PROVENANCE = PASS
CONFLICTS_EXPLICIT = PASS
CONFLICTS_PERSISTED = PASS
MAJORITY_SILENT_SELECTION = DISABLED
TESTS = PASS
```

## Decision classification

### EVIDENCE_BACKED

- per-fact provenance is retained through fusion;
- competing values remain representable instead of being destructively overwritten.

### LOCALLY_VERIFIED

- unanimous policy produced zero false automatic canonicals on the curated benchmark;
- naive majority failed on all four correlated-majority adversarial cases and overclaimed all four unresolved ties.

### ENGINEERING_CHOICE

- use normalized value when present, otherwise raw value;
- exact effective-value unanimity as the V1 auto-canonical rule;
- deterministic IDs;
- majority exposed only as diagnostic.

### UNKNOWN

- source reliability weights;
- temporal truth-decay model;
- dependence/correlation between sources;
- learned truth-discovery algorithm;
- production conflict prevalence and accuracy.

## Limitation

The 32-scenario benchmark is curated and adversarial. It is suitable for policy selection and regression testing, not a production accuracy estimate. The project currently has only one real source adapter, so true multi-source truth discovery cannot yet be locally validated on real conflicting feeds.

## Next work unit

Per roadmap: `CONTACT_DISCOVERY_V1`.
