## 2025-05-20 - Memoizing string folding and pre-compiling regexes in dental qualification
**Learning:** `unicodedata.normalize` (NFKC and NFKD) and uncompiled regexes in tight qualification loops account for over 60% of total runtime when classifying lead attributes across thousands of candidate facts.
**Action:** Use an inner `@functools.lru_cache` wrapper on string representation (`_fold_str(text: str)`) and pre-compile regular expressions at module scope (`_CEOF_RE`, `_HOF_RE`).
