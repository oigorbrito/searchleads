# Bolt's Journal - Critical Performance Learnings

## 2026-10-09 - Pre-calculating Blocking Keys in Pairwise Corpus Evaluations
**Learning:** In entity resolution blocking algorithms (`evaluate_blocking_corpus`), evaluating `is_blocked_candidate(left, right)` inside an $O(N^2)$ pairwise comparison loop recalculates `blocking_keys(record)` $N(N-1)$ times instead of $N$ times. Since `blocking_keys` invokes expensive field normalizations, NFKC/NFKD unicode operations, regex string manipulation, and CandidateFact projections, this causes massive redundant work.
**Action:** When computing pairwise comparisons across $N$ records in a corpus, always precalculate per-record features/keys in a single $O(N)$ pass prior to looping over combinations $O(N^2)$.
