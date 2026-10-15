## 2025-05-20 - Memoization and Hoisting in ER Blocking Evaluation
**Learning:** Entity resolution pair matching and corpus blocking evaluations repeat string normalization (`unicodedata.normalize`, case folding) and CandidateFact projections thousands of times across combinations. In addition, nested helper calls (e.g. `_similarity` calling `_tokens` on already-folded strings) caused redundant double-folding.
**Action:** Use `@lru_cache` for pure string normalizations in ER models and hoist `blocking_keys` calculation out of $O(N^2)$ combination loops in corpus evaluation.
