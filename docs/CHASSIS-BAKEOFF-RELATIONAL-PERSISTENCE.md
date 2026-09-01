# Chassis Bake-Off — Relational Persistence Candidate

Status: `EXPERIMENTAL_PROTOCOL / NOT PRODUCTION AUTHORIZED`.

This study evaluates whether first-class Person↔Company relationship records can replace embedded organizational snapshots while preserving SearchLeads Evidence, persistence integrity, qualification semantics, and Person ER behavior.

The baseline is not protected, and the candidate is not presumed superior.

## Research question

Can a first-class relationship model satisfy the declared SearchLeads integrity and compatibility requirements without introducing unacceptable migration or synchronization cost?

Claims about lower long-term cost, better maintainability, or superior representation require evidence appropriate to those constructs. Structural plausibility alone does not establish them.

## Evidence classification

Under the current harness methodology:

- external/library domain-model inspection is `STATIC_INSPECTION`;
- migration, persistence, compatibility, and fault checks are `FUNCTIONAL_PROBE` when executed;
- claims about time, code-change burden, or operational cost require a declared comparative method and may qualify as `CONTROLLED_BENCHMARK` only when the protocol supports that interpretation.

Source-code occurrence counts are migration-surface observations, not quality metrics.

## Candidate domain split

```text
PersonIdentity
  person_id
  identity fact/contact references

PersonCompanyRelationship
  relationship_id
  person_id
  company_id
  evidence_ids
  role/temporal facts may attach to the relationship

ProfessionalRegistration
  registration_id
  person_id
  authority
  number
  jurisdiction
  operational status
  evidence_ids
```

A professional registration is not an organizational employment relationship. Absence of an end date is not proof of current active registration.

## Migration invariant

The migration protocol is intentionally conservative:

1. each persisted legacy `Person` becomes one identity with the same ID;
2. the embedded company link becomes a separate relationship record;
3. relationship Evidence moves to that relationship;
4. no cross-company Person IDs are merged during structural migration;
5. only a separate explicit ER decision may later repoint multiple relationships to one canonical Person identity.

A schema refactor must not silently become an identity-resolution decision.

## Persistence hypothesis

SearchLeads v3 uses generic domain-record persistence rather than physical person/company columns. This supports a testable hypothesis that relationship and registration records can reuse the current physical storage shape.

A successful round-trip probe may establish functional compatibility under its declared conditions. It does not establish that the model lowers production cost or is universally preferable.

Production adoption would still require explicit public domain/API, codec, semantic-reference, migration, discovery, qualification-context, ER-context, and regression changes.

## Executable probes

### Relational persistence

`test_chassis_bakeoff_relationship_persistence.py` checks declared properties such as:

- one Person identity with multiple company relationships;
- no silent Person merge during structural migration;
- Evidence references retained;
- registration separated from company relationship;
- stable-ID behavior retained.

### Generic domain-record reuse

`test_chassis_bakeoff_generic_domain_record_reuse.py` checks whether candidate record types can reuse current repository mechanics and integrity guards without a physical schema change under the tested scenario.

### Migration surface

`test_chassis_bakeoff_relationship_migration_cost.py` records code-surface observations such as occurrences/files containing embedded relationship references.

These counts can scope migration work. They do not, by themselves, establish maintainability or lower long-term cost.

## Acceptance criteria

A bounded functional recommendation requires traceable evidence that, under the declared scenarios:

1. legacy single-company semantics can round-trip losslessly;
2. structural migration performs zero silent Person merges;
3. one identity can hold multiple company relationships without rewriting identity snapshots;
4. relationship and registration states retain explicit Evidence references;
5. qualification behavior remains equivalent when given equivalent relationship context;
6. Person ER can consume company context without embedding company identity inside canonical Person identity;
7. stable-ID and reference-integrity guards remain effective.

A claim that the candidate reduces migration burden or long-term synchronization cost requires an additional measurement design appropriate to that claim. It must not be inferred from the functional probes alone.

## Rejection conditions

Reject the candidate under the evaluated scope if reproducible execution shows:

- loss of raw/Evidence lineage;
- implicit Person merges;
- ambiguous company context in qualification;
- weaker corruption/reference detection;
- functional incompatibility that violates the declared SearchLeads invariants.

Claims about maintenance burden or cost require separate acceptance/rejection criteria and observations.

## Decision state

Production adoption remains `DEFER` unless a current machine-readable claim bundle references the required evidence and its evidence state authorizes an active decision.

The historical architectural preference for a composed first-class relationship model may be preserved as decision history, but it is not an empirical winner declaration.
