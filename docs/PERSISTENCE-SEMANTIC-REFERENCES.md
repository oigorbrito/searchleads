# Persistence semantic reference invariants v1

The public `searchleads.persistence.SQLiteRepository` enforces semantic coherence in addition to existence checks.

A fact lineage is valid only when persisted references agree on both `subject_id` and `field_name`:

- `CandidateFact` -> `Provenance`
- `Provenance.derived_from_fact_ids` -> `CandidateFact`
- `CanonicalFact` -> supporting `CandidateFact` records and its `Provenance`
- `Conflict` -> participating `CandidateFact` records

The underlying SQLite codec/storage implementation is unchanged. These checks execute before insert and fail closed with `SemanticReferenceError`.

This prevents an existing but unrelated fact/provenance record from satisfying referential integrity merely because its ID exists.

## Public persistence import boundary

Runtime code and repository scripts must obtain persistence services through `searchleads.persistence` rather than importing `searchleads.persistence.ledger`, `searchleads.persistence.semantic`, or `searchleads.persistence.sqlite` directly.

This keeps semantic-reference validation and migration-ledger repair on the effective repository path. A repository-level AST guard scans `src/searchleads` outside the persistence implementation plus `scripts` and fails when those internal modules are imported directly.
