## 2025-05-18 - Pre-computing Record Blocking Keys in Entity Resolution

**Learning:** Calling `blocking_keys(record)` inside pairwise combination loops `combinations(records, 2)` causes expensive feature extraction, normalization (`_wu4`), and string folding to run $O(N^2)$ times (2 * $N(N-1)/2$ calls) instead of $O(N)$ times.

**Action:** Always pre-compute and cache record keys or features prior to $O(N^2)$ evaluation or blocking loops.
