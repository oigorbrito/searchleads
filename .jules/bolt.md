## 2025-05-18 - Precompute Blocking Keys for Entity Resolution Corpus Evaluation

**Learning:** In `searchleads.entity_resolution.company`, generating blocking keys (`blocking_keys`) performs text normalization, domain/phone normalization, and regex token extraction. Evaluating combinations across a corpus of records re-evaluated `blocking_keys` $O(N^2)$ times inside pair loops instead of $O(N)$ once per record. Pre-computing keys before pairwise combination checks reduced execution time per call from ~376ms down to ~4.7ms (a ~98.7% speedup).

**Action:** Whenever evaluating pairwise record functions or candidate blocking across record corpora, always pre-compute record-level feature keys/projections $O(N)$ before entering $O(N^2)$ pairwise combination loops.
