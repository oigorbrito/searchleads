# WORK UNIT 05 REPORT — COMPANY_ENTITY_RESOLUTION_V1

## Scope

This work unit implements a measured, explainable company entity-resolution V1 without performing irreversible automatic fuzzy merges.

Implemented:

- pairwise company comparison;
- explicit identity features (registry ID, domain, phone, name, address, location, CNAE);
- deterministic blocking keys;
- registry-ID hard positive/hard conflict rules;
- exact-evidence and weighted candidate strategies;
- threshold sweep;
- operational triage (`AUTO_MATCH`, `REVIEW`, `DISTINCT`, `INSUFFICIENT_EVIDENCE`);
- a curated labeled benchmark with difficult positive and negative cases;
- reproducible evaluation script.

Not implemented:

- automatic fuzzy Company merge;
- canonical company fusion;
- cluster/B³ evaluation;
- learned model or opaque embedding score;
- source-specific authority weights;
- production-prevalence calibration.

## Labeled benchmark

`tests/fixtures/company_er_v1.json` contains 54 labeled record pairs:

```text
TRUE_DUPLICATE = 27
NOT_DUPLICATE  = 27
TOTAL          = 54
```

The set is deliberately balanced and adversarial rather than prevalence-representative. Negative cases include identical/similar names for different companies, shared domains, shared phones, shared addresses/coworking, same location and industry, different full CNPJ/registry IDs, same-brand entities, units sharing phone/address, and shared domain plus highly similar company names.

This is a `LOCALLY_VERIFIED` engineering benchmark, not an estimate of population accuracy.

## Blocking result

The benchmark contains 108 record instances. Evaluating every possible record combination gives 5,778 pairs.

```text
TRUE_DUPLICATE_PAIRS = 27
CANDIDATE_PAIRS      = 117 / 5,778
BLOCKING_RECALL      = 100.0%
PAIR_REDUCTION       = 98.0%
```

## Matching results

### Strategy A — exact registry only

```text
TP = 5
FP = 0
TN = 27
FN = 22
PRECISION = 100.0%
RECALL = 18.5%
F1 = 31.2%
FALSE_MERGE_RATE = 0.0%
```

### Strategy B — exact multi-signal evidence

```text
TP = 19
FP = 4
TN = 23
FN = 8
PRECISION = 82.6%
RECALL = 70.4%
F1 = 76.0%
FALSE_MERGE_RATE = 14.8%
```

Useful as a review-ranking rule, not acceptable for irreversible auto-merge on this benchmark.

### Strategy C — weighted score threshold sweep

| Threshold | TP | FP | Precision | Recall | F1 | False merge rate |
|---:|---:|---:|---:|---:|---:|---:|
| 0.70 | 26 | 19 | 57.8% | 96.3% | 72.2% | 70.4% |
| 0.72 | 26 | 15 | 63.4% | 96.3% | 76.5% | 55.6% |
| 0.74 | 26 | 15 | 63.4% | 96.3% | 76.5% | 55.6% |
| **0.76** | **26** | **13** | **66.7%** | **96.3%** | **78.8%** | **48.1%** |
| 0.78 | 25 | 13 | 65.8% | 92.6% | 76.9% | 48.1% |
| 0.80 | 24 | 10 | 70.6% | 88.9% | 78.7% | 37.0% |
| 0.82 | 23 | 10 | 69.7% | 85.2% | 76.7% | 37.0% |
| 0.84 | 21 | 10 | 67.7% | 77.8% | 72.4% | 37.0% |
| 0.86 | 18 | 10 | 64.3% | 66.7% | 65.5% | 37.0% |
| 0.88 | 16 | 8 | 66.7% | 59.3% | 62.7% | 29.6% |
| 0.90 | 15 | 5 | 75.0% | 55.6% | 63.8% | 18.5% |
| 0.92 | 14 | 2 | 87.5% | 51.9% | 65.1% | 7.4% |
| 0.94 | 11 | 2 | 84.6% | 40.7% | 55.0% | 7.4% |
| 0.96 | 9 | 2 | 81.8% | 33.3% | 47.4% | 7.4% |

The maximum measured F1 is 78.8% at threshold 0.76, but that configuration falsely merges 13 of the 27 negative pairs. Even threshold 0.92 still creates two false merges. Therefore no weighted threshold is accepted for automatic merge in V1.

## Operational V1 triage

```text
full registry ID equal     -> AUTO_MATCH
full registry ID different -> DISTINCT
strong multi-signal fuzzy  -> REVIEW
otherwise                  -> INSUFFICIENT_EVIDENCE
```

| Disposition | True duplicates | Negative pairs |
|---|---:|---:|
| AUTO_MATCH | 5 | 0 |
| REVIEW | 14 | 4 |
| DISTINCT | 0 | 3 |
| INSUFFICIENT_EVIDENCE | 8 | 20 |

Derived operating numbers:

```text
AUTO_MATCH_PRECISION = 100.0%
AUTO_MATCH_RECALL = 18.5%
REVIEW_QUEUE_YIELD = 77.8%
DUPLICATE_COVERAGE_WITH_REVIEW = 70.4%
```

## Decision

Use **registry-only auto-merge + multi-signal REVIEW**. Do not enable weighted fuzzy auto-merge.

Reason: false merges are destructive and contaminate provenance/contact/company graphs. The current benchmark supports fuzzy evidence as candidate prioritization, not as merge certainty.

Widen automatic merge only after a larger independently labeled source-derived dataset, an explicit cost ratio for false merges vs missed duplicates, and holdout evaluation not used for threshold design. If clustering is introduced, add cluster-level metrics such as B³.

## Tests

```text
TESTS_DISCOVERED = 58
TESTS_EXECUTED = 58
TESTS_PASSED = 58
```

Reproduce metrics:

```bash
python scripts/evaluate_entity_resolution.py
```

## Decision classification

### EVIDENCE_BACKED

- entity matching is separated from normalization, blocking, fusion, and conflict handling;
- evaluation exposes precision/recall tradeoffs instead of hiding them behind one opaque score.

### LOCALLY_VERIFIED

- 100% blocking recall / 98.0% pair reduction on the curated corpus;
- registry-only auto-merge has 0 measured false merges;
- fuzzy/weighted auto-merge has unacceptable measured false-merge behavior on the hardened negatives.

### ENGINEERING_CHOICE

- feature set and V1 blocking keys;
- `SequenceMatcher` + token overlap name similarity;
- weighted feature weights;
- registry conflict veto;
- fuzzy matches routed to REVIEW.

### UNKNOWN

- production duplicate prevalence;
- production precision/recall;
- optimal cost-sensitive threshold on real traffic;
- ICP.
