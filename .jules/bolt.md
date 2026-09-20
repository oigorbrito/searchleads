# Bolt's Journal

## 2025-05-18 - Precomputing Blocking Keys in Entity Resolution Corpus Evaluation
**Learning:** In entity resolution evaluation routines like `evaluate_blocking_corpus`, running pairwise comparisons over `N` records calls `blocking_keys(record)` O(N^2) times if invoked inside `combinations(records, 2)`. Because `blocking_keys` performs normalization, regex substitutions, and URL splitting, this repeated extraction dominates runtime. Precomputing blocking keys per record instance reduces extraction calls from O(N^2) to O(N), yielding a ~60x performance improvement for corpus evaluations.
**Action:** When computing pairwise candidate features over a collection of domain records, always pre-extract and map record-level features/keys before running combination loops.
