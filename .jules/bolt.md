## 2025-02-18 - Company Entity Resolution Corpus Blocking Bottleneck
**Learning:** `evaluate_blocking_corpus` in `entity_resolution/company.py` evaluates candidate pairs via `combinations(records, 2)` calling `is_blocked_candidate`, which re-evaluated `blocking_keys` (and nested `_wu4` candidate fact normalization and string folding) N-1 times per record.
**Action:** Pre-compute `blocking_keys` array once per record list before combinations, and use `@lru_cache` on pure helpers (`_fold`, `_wu4`, `blocking_keys`) to avoid redundant normalization and string parsing.
