# Chassis Bake-Off — Relational Persistence Candidate

Status: `EXPERIMENTAL / NOT PRODUCTION AUTHORIZED`

## Question

Can SearchLeads replace the embedded `Person.company_id` and `Company.person_ids` snapshot model with first-class relationship records while preserving Evidence, immutable persistence, qualification semantics, and Person ER behavior at lower long-term synchronization cost?

The SearchLeads model is a baseline, not a protected design.

## Evidence classification

- `ENGINEERING_EVIDENCE`: FollowTheMoney models organizational relationships as first-class entities such as `Employment` and `Directorship` rather than embedding one organization in Person identity.
- `ENGINEERING_EVIDENCE`: SearchLeads v3 persistence stores domain objects in a generic `(record_type, record_id, payload_json, digest)` table; organization/person fields are not physical columns.
- `LOCAL_EXPERIMENT`: executable migration, persistence, compatibility, and fault probes in `tests/experimental/`.
- `HYPOTHESIS`: first-class relationships will reduce synchronization burden and improve multi-organization representation without unacceptable complexity.

No benchmark result is considered executed while GitHub Actions jobs terminate before checkout with `steps=null`.

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

The three concepts are independent. A CRO/CFO professional registration is not an organizational employment relationship, and absence of an end date is not proof of current active registration.

## Migration rule

V1 migration is intentionally conservative:

1. each persisted V1 `Person` becomes one `PersonIdentity` with the same ID;
2. its embedded company link becomes one relationship record;
3. `relationship_evidence_ids` move to that relationship;
4. no cross-company Person IDs are merged during structural migration;
5. only an explicit ER decision may later repoint multiple relationships to one canonical Person identity.

This prevents a schema refactor from silently becoming an identity-resolution decision.

## Persistence hypothesis

The current physical `domain_records` table is generic. The executable probe extends the in-process record codec registry and semantic reference rules with experimental types while keeping schema version 3 and the same physical tables.

If the probe passes, adding relationship/registration domain records does **not** by itself require a new physical SQLite table or schema-version increment. Production adoption would still require:

- public domain classes and exports;
- codec registry entries;
- stable ID-field entries;
- semantic reference rules;
- V1 data migration/compatibility logic;
- discovery adapter changes;
- qualification context adapter or API change;
- Person ER observation-context adapter;
- regression and migration tests.

A future schema version could still be justified for indexes or performance, but it is not a semantic prerequisite for the first-class relation model.

## Executable probes

### Relational persistence

`test_chassis_bakeoff_relationship_persistence.py`

Measures:

- one Person identity with two company relationships;
- zero Company snapshot mutation requirement;
- no silent ER during lossless migration;
- explicit ER convergence as a separate operation;
- mandatory existing Evidence for relationship and registration;
- professional registration independent of company relationship;
- immutable stable-ID conflict behavior.

### Generic domain-record reuse

`test_chassis_bakeoff_generic_domain_record_reuse.py`

Measures:

- candidate identity/relationship/registration round-trip through current repository mechanics;
- schema version before/after;
- physical table set before/after;
- reuse of existing MissingReference guards.

### Migration code surface

`test_chassis_bakeoff_relationship_migration_cost.py`

Reports actual source-code occurrence/file counts for:

- `person.company_id` access;
- `Person(...)` construction;
- `Company.person_ids` snapshots;
- relationship Evidence references.

These are migration-surface measurements, not quality metrics.

## Acceptance gates

The relational model is a candidate for promotion only if executed tests show all of the following:

1. `LOSSLESS_V1_ROUNDTRIP = PASS` for legacy single-company semantics.
2. `SILENT_PERSON_MERGES = 0` during structural migration.
3. one identity can hold multiple company relationships without rewriting identity or Company snapshots.
4. every accepted relationship and professional-registration state retains explicit SearchLeads Evidence references.
5. current qualification outcome and decision identity remain equivalent when supplied the same relationship context.
6. Person ER retains company context as an observation/relationship feature without requiring it inside canonical Person identity.
7. persistence stable-ID immutability remains enforced.
8. current schema integrity/identity guards remain effective.
9. migration code surface and custom adapter burden are materially smaller than retaining synchronized embedded references.

## Rejection conditions

Reject this candidate if any of the following is observed:

- loss of Evidence/raw reprocessing lineage;
- implicit Person merges during migration;
- ambiguous company context in qualification;
- weaker corruption/reference detection;
- substantial fork-specific persistence machinery merely to imitate first-class relations;
- executed regression degradation that cannot be isolated and repaired cheaply.

## Current provisional architectural direction

The strongest candidate is not pure FollowTheMoney and not the current SearchLeads model. It is a composition:

```text
SearchLeads raw Evidence + integrity
        ↓ explicit links
FTM-style entity/relationship semantics
        ↓
Nomenklatura / measured ER
        ↓
SearchLeads qualification and commercial policy
```

Production adoption remains `UNDECIDED_PENDING_EXECUTED_TESTS`.
