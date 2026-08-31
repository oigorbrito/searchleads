# SearchLeads Company Entity Resolution v1

## Work unit

`COMPANY_ENTITY_RESOLUTION_V1`

This unit measures and implements a conservative company-record entity-resolution decision layer. It does not merge persisted `Company` objects.

The target identity in V1 is deliberately narrow:

> two observations represent the same registered/operational company entity.

This is **not** a rule for corporate groups, brands, franchises, parent/subsidiary relationships, or establishments that intentionally carry different registry identifiers.

## Pipeline

```text
company observations
→ transparent blocking keys
→ candidate pairs
→ pairwise evidence features
→ experimental strategy evaluation
→ conservative operational triage
→ AUTO_MATCH | REVIEW | DISTINCT | INSUFFICIENT_EVIDENCE
```

No disposition in this work unit mutates persistence.

## Registry namespace boundary

A registry identifier can only become a hard feature when both records provide a compatible supported namespace.

V1 supports:

```text
registry_namespace = br:cnpj
```

For `br:cnpj`, formatting punctuation/whitespace is removed and the current 14-character `0-9A-Z` representation is accepted. This remains an ER comparison rule scoped to the CNPJ namespace; WU4's generic `business_registry_id` stays unsupported as a generic normalizer.

Consequences:

- same valid CNPJ + same namespace → exact registry signal;
- different valid CNPJs + same namespace → registry conflict;
- same literal ID under unsupported/unknown namespace → no hard registry signal;
- same literal ID under different namespaces → not comparable;
- malformed CNPJ value → not a registry signal.

A registry conflict means `DISTINCT` for the **same-registered-entity** target. It does not claim the organizations are commercially unrelated.

## Pairwise features

`MatchFeatures` records transparent signals:

- namespaced full-registry exact/conflict;
- exact domain after WU4 domain representation;
- exact phone after WU4 phone representation;
- name similarity;
- address-token Jaccard similarity;
- exact folded city + state;
- exact digit representation of CNAE.

Name/address folding is local ER comparison preparation: case/diacritics/whitespace are folded for similarity only. It is not persisted back into WU4 candidate facts.

Invalid domains or phones rejected by WU4 do not become ER signals.

## Blocking

Candidate generation uses a union of transparent keys:

- `registry:<namespace>:<normalized-id>`;
- normalized exact domain;
- normalized exact phone;
- first normalized name-token prefix;
- first name-token prefix + folded city.

The benchmark contains 54 labeled pairs (27 duplicate / 27 negative) and therefore 108 independently keyed observation records for corpus-level blocking.

Measured corpus result:

```text
TOTAL_POSSIBLE_PAIRS = 5,778
TRUE_DUPLICATE_PAIRS = 27
CANDIDATE_PAIRS = 117
BLOCKING_RECALL = 100.0%
PAIR_REDUCTION = 98.0%
```

This is a local curated benchmark, not production coverage.

## Evaluated matching strategies

### 1. Registry-only

Hard match only for exact supported namespaced full registry identifier; registry conflict is a veto.

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

High precision, insufficient recall as a full ER system.

### 2. Exact multi-signal evidence

Without registry conflict, candidate pairs may match experimentally when domain/phone/location exactness is combined with minimum name similarity.

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

This is useful for **review routing**, not automatic irreversible merge.

### 3. Weighted score sweep

Weights are retained only as an experimental comparison instrument:

- name similarity: 0.40;
- domain exact: 0.25;
- phone exact: 0.15;
- address similarity: 0.10;
- location exact: 0.05;
- CNAE exact: 0.05;
- available-feature weights are renormalized when fields are missing.

Selected measured thresholds:

| Threshold | Precision | Recall | F1 | False-merge rate |
| ---: | ---: | ---: | ---: | ---: |
| 0.70 | 57.8% | 96.3% | 72.2% | 70.4% |
| 0.76 | 66.7% | 96.3% | **78.8%** | **48.1%** |
| 0.80 | 70.6% | 88.9% | 78.7% | 37.0% |
| 0.90 | 75.0% | 55.6% | 63.8% | 18.5% |
| 0.92 | 87.5% | 51.9% | 65.1% | **7.4%** |
| 0.96 | 81.8% | 33.3% | 47.4% | **7.4%** |

The best F1 threshold (`0.76`) falsely merges 13 of 27 negatives. Even `0.92` and `0.96` still produce two false merges. Therefore no weighted threshold is approved for automatic merge in V1.

## Operational triage policy

The policy deliberately prioritizes avoiding irreversible false merges:

```text
supported namespaced registry conflict
→ DISTINCT

supported namespaced registry exact
→ AUTO_MATCH

exact multi-signal evidence rule passes
→ REVIEW

otherwise
→ INSUFFICIENT_EVIDENCE
```

Measured benchmark routing:

| Disposition | True duplicates | Negatives |
| --- | ---: | ---: |
| `AUTO_MATCH` | 5 | 0 |
| `REVIEW` | 14 | 4 |
| `DISTINCT` | 0 | 3 |
| `INSUFFICIENT_EVIDENCE` | 8 | 20 |

Derived local metrics:

```text
AUTO_MATCH_PRECISION = 100.0%
AUTO_MATCH_RECALL = 18.5%
REVIEW_QUEUE_YIELD = 77.8%
DUPLICATE_COVERAGE_WITH_AUTO_PLUS_REVIEW = 70.4%
```

The low auto-match recall is intentional: unresolved candidates remain review/insufficient rather than being force-merged.

## Benchmark limitations

The 54-pair corpus is deliberately adversarial/balanced and includes shared domains, shared phones, shared addresses, generic/similar names, same-location/industry cases, and conflicting registries. It is suitable for deterministic local calibration but **not** a production prevalence or accuracy estimate.

Known limitations:

- balanced 50/50 class prevalence is artificial;
- examples are curated rather than sampled from a production lead stream;
- exact CNPJ labels dominate the approved auto-match set;
- no temporal company lifecycle/renaming/merger data;
- no corporate-group relationship model;
- no learned weights;
- no human-review outcomes yet;
- no external ground-truth dataset.

Any future relaxation of auto-match requires new labeled evidence and explicit false-merge evaluation.

## Reproducibility

`scripts/evaluate_entity_resolution.py` loads `tests/fixtures/company_er_v1.json` and prints:

- benchmark composition;
- corpus blocking metrics;
- registry-only and exact-evidence metrics;
- weighted threshold sweep;
- operational triage counts and derived metrics.

The exact key benchmark numbers are also asserted in tests so metric drift fails CI.

## Verification

Current clean-stack verification after WU5 implementation:

- WU5 focused tests: 33/33 PASS before final documentation regression;
- full clean stack before documentation-only changes: 286/286 PASS;
- measured package line coverage: 100% across 1,051 statements;
- evaluation script reproduces the metrics recorded above.

Final PR verification is rerun after documentation/publication alignment.

## Gates

```text
BENCHMARK_DEFINED = YES
BLOCKING_MEASURED = YES
BLOCKING_RECALL = 100.0% LOCAL_BENCHMARK
PAIR_REDUCTION = 98.0% LOCAL_BENCHMARK
AUTO_MATCH_POLICY = EXACT_SUPPORTED_NAMESPACED_REGISTRY_ONLY
AUTO_MATCH_FALSE_POSITIVES = 0/27 LOCAL_BENCHMARK
FUZZY_AUTO_MERGE = NO
WEIGHTED_SCORE_OPERATIONAL_AUTHORITY = NO
SELECTIVE_REVIEW = YES
PERSISTED_COMPANY_MERGE = NO
ICP_DEFINED = NO
B2B_ASSUMPTION = PROVISIONAL
```

## Dependency note

WU3's live BrasilAPI smoke remains separately blocked by execution-environment DNS. WU5 uses the deterministic candidate/normalization contracts already tested and does not relabel that external gate as passed.

## Next work

The next staged capability should consume ER decisions without erasing evidence: explicit canonicalization/fusion/conflict handling or the next work unit specified by the project handoff. Any persistent merge operation must preserve reversibility/provenance and should not be inferred from the experimental weighted score.
