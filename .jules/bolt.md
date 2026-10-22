# Bolt's Performance Journal

## 2025-05-18 - Avoid redundant feature/key generation in pairwise entity resolution benchmarks
**Learning:** In pairwise entity resolution benchmarks (`evaluate_blocking_corpus`), evaluating key generation (`blocking_keys()`) on every pair in `combinations(records, 2)` recalculates expensive string normalization and fact parsing `2 * N * (N - 1) / 2` times instead of `N` times. Precomputing keys per record upfront drops execution time from ~276ms to ~3.6ms per corpus evaluation (~75x speedup).
**Action:** When computing pairwise or cross-record candidate combinations, always pre-calculate per-record features/blocking keys into an indexed collection before looping over pair combinations.
