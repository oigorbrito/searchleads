# DATA_AND_EVIDENCE_MODEL

Status: CANONICAL

## Principles

- raw evidence is first-class and durable
- derived records must not overwrite raw truth
- integrity checks are mandatory
- replay must be deterministic where evidence is unchanged

## Evidence

Evidence represents the original captured artifact plus integrity metadata and source linkage.

## Raw Payload

The raw payload is stored separately from derived statements when the persistence layer supports it.

## Integrity

- storage integrity protects against corruption and tampering
- digest mismatch is an error, not a fallback
- missing integrity metadata is a repair or failure condition, not silent synthesis

## Statements and Provenance

- statements derive from evidence
- provenance records the evidence set and derivation context
- a statement can be replayed from evidence when the source material is available

## Conflicts

- conflicts are explicit records
- conflict state must not be collapsed into canonical truth without an authorized decision

## Persistence

- persistence stores immutable records where possible
- repair may add missing shape metadata
- derived state must be distinguishable from original evidence

## Identity

- evidence identity is distinct from statement identity
- relationship identity is distinct from person identity
- company identity is distinct from person identity

## Reconstructible vs Persisted

- reconstructible state may be recomputed from persisted evidence and rules
- persisted state should be reserved for immutable history, decisions, and operationally useful caches
