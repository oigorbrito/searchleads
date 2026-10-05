## 2026-10-05 - Memoizing String Normalization in Entity Resolution Blocking

**Learning:** String normalization routines like `_fold` (which perform NFKC and NFKD unicodedata decomposition, case-folding, and combining-character filtering) and candidate fact normalization (`_wu4`) become major bottlenecks during entity resolution blocking when evaluated across corpus record pairs ($O(N^2)$ pair comparisons). Without caching, 108 records evaluated over 5,778 pairs resulted in thousands of redundant unicodedata decompositions for identical string values.

**Action:** Apply `@functools.lru_cache(maxsize=2048)` to deterministic string folding and domain/phone fact normalization functions in ER modules to ensure record fields are normalized at most once per execution context.
