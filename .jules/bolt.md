## 2025-02-23 - Avoid O(N^2) Blocking Key Recomputations & Transient Dataclasses in ER

**Learning:** In entity resolution blocking metrics (`evaluate_blocking_corpus`), calling `blocking_keys(record)` inside pairwise combination loops (`combinations(records, 2)`) caused $O(N^2)$ re-computations of expensive normalizations (regex, IDNA encoding, unicode NFKC folding). Additionally, `_wu4` was instantiating transient `CandidateFact` dataclass objects to normalize single string fields.

**Action:** Always precompute entity blocking keys in $O(N)$ time before pairwise comparison loops. Invoke field normalizers directly via `_NORMALIZERS.get(field)` rather than constructing full fact wrappers when normalizing individual string attributes in entity resolution.
