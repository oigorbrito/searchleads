## 2025-05-20 - Precompute Blocking Keys for Entity Resolution Corpus Evaluation

**Learning:** In entity resolution evaluation functions (`evaluate_blocking_corpus`), comparing all pairs $O(N^2)$ across $N$ records calls feature extraction and normalization (e.g., `blocking_keys` which invokes string normalization, URL parsing, regexes, and domain checks) repeatedly for each record on every pair check ($2 \times \frac{N(N-1)}{2} = N(N-1)$ extractions). Precomputing blocking keys once per record before pair comparison reduced execution time from ~275 ms per run down to ~4 ms per run (~68x speedup for pair checking, ~47x speedup for overall benchmark evaluation).

**Action:** In pairwise or $O(N^2)$ combination loops, precompute record-level features or blocking keys once per record into a lookup structure before comparing pairs.
