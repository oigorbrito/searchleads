## 2025-05-18 - Entity Resolution String Normalization & Blocking Key Memoization
**Learning:** Company Entity Resolution (ER) evaluations heavily execute string folding (`unicodedata.normalize`), tokenization (`re.findall`), CandidateFact projections, and blocking key extraction over identical record fields thousands of times across pairwise comparisons.
**Action:** Use `@functools.lru_cache(maxsize=2048)` on pure string processing helpers (`_fold`, `_tokens`, `_wu4`, `blocking_keys`) in ER modules to eliminate $O(N^2)$ redundant unicodedata and regex execution.
