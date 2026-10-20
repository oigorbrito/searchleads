## 2026-03-30 - Precompute per-record features in O(N^2) pairwise evaluation loops

**Learning:** Pairwise corpus evaluation functions (e.g. `evaluate_blocking_corpus`) iterating over $O(N^2)$ combinations call single-record extraction functions (`blocking_keys`) $2 \times \binom{N}{2}$ times. When feature extraction includes normalization, regexes, or object creation, recomputing per record inside the loop dominates runtime.
**Action:** Always precompute per-record features into a hash map before running $O(N^2)$ pairwise comparisons, and memoize pure record feature extraction functions using `@lru_cache`.
