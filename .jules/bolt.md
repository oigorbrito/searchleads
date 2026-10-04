# Bolt's Journal - Critical Learnings

## 2025-05-18 - Memoizing Entity Resolution Blocking Keys
**Learning:** `CompanyRecord` instances in `searchleads.entity_resolution.company` are frozen dataclasses (`frozen=True`, `slots=True`), making them hashable and ideal for `functools.lru_cache`. In $O(N^2)$ pairwise blocking evaluations (such as `evaluate_blocking_corpus`), computing `blocking_keys` without memoization causes severe overhead from repeated string normalization (`_fold`, `_tokens`, `_registry`) and candidate fact creation (`_wu4`). Decorating `blocking_keys` with `@lru_cache(maxsize=4096)` yields a ~30-38x speedup (reducing per-run evaluation time from ~0.28s to ~0.007s).
**Action:** When implementing or evaluating entity resolution and blocking algorithms with immutable record data structures, always memoize record key extraction to prevent redundant normalization in pairwise comparisons.
