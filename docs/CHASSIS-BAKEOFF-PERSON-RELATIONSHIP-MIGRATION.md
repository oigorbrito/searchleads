# Person identity / relationship migration bake-off

Status: `LOCAL_EXPERIMENT` + `ENGINEERING_EVIDENCE`; execution results remain unavailable until a GitHub runner actually executes the workflow.

## Problem under test

The current SearchLeads `Person` record embeds:

- `person_id`;
- `company_id`;
- `relationship_evidence_ids`.

Persistence treats `Person` as immutable by `person_id`. As a result, one stable person identity cannot be persisted against a second company under the same `person_id` without changing the stored `Person` payload and triggering `PersistenceConflictError`.

The current `Company.person_ids` field is also an immutable aggregate snapshot, which creates a second synchronization problem when people are discovered after the company was already persisted.

FollowTheMoney provides a structurally different baseline: independent `Person` entities plus first-class relationship entities such as `Employment` and `Directorship`. These relationship entities carry organization context, role, temporal bounds and source/lineage fields.

The experiment does **not** assume that FollowTheMoney should replace the SearchLeads domain wholesale. It tests whether SearchLeads should adopt the separation of identity from professional relationship while retaining stricter Evidence requirements.

## Candidate shape

Experimental compatibility tests use two concepts:

```text
PersonIdentityCandidate
  person_id
  candidate_fact_ids
  canonical_fact_ids
  contact_point_ids

PersonCompanyRelationshipCandidate
  relationship_id
  person_id
  company_id
  evidence_ids  # mandatory
```

The candidate deliberately keeps mandatory SearchLeads Evidence references on the relationship. This is stricter than accepting an un-sourced generic relation.

## Direct migration surface observed

### 1. Domain and persistence

Current coupling:

- `Person.company_id` stores organization context on the identity record;
- `Person.relationship_evidence_ids` stores evidence for that context on the identity record;
- `SQLiteRepository._assert_references(Person)` requires the embedded company and relationship Evidence;
- immutable `(record_type, record_id)` persistence prevents the same `person_id` from changing company context.

Candidate direction:

- persist person identity independently;
- persist one or more relationship records referencing person + company + Evidence;
- make company/person aggregate lists derived views or indexes rather than immutable source-of-truth snapshots.

### 2. Person discovery

`CompanyPeopleSource.ingest()` currently creates observation-scoped `Person` records with `company_id` and page Evidence embedded in the person.

Candidate direction:

- create or resolve a person observation/identity independently;
- create a relationship observation for `(person, company)` using the captured page Evidence;
- keep role facts associated with the relationship context where appropriate rather than treating company context as part of person identity.

This is particularly important because the current observation `person_id` itself includes `company_id` in its digest material. That construction makes cross-company identity convergence impossible without a later identity-resolution layer creating a different canonical representation.

### 3. Person entity resolution

`PersonRecord` currently includes `company_id` and `relationship_evidence_ids`. This does not necessarily need to disappear: these values are useful *observation-context features*.

Candidate direction:

- keep `company_id` and relationship Evidence on the ER observation/context record;
- do not keep them on the canonical person identity;
- allow the same canonical person to have observations/relationships at multiple organizations.

This preserves useful features such as `same_company` without defining company membership as identity.

### 4. Dental qualification

`qualify_dental_person()` currently derives:

```text
subjects = {person.person_id, person.company_id}
evidence = set(person.relationship_evidence_ids)
```

and materializes a decision keyed by both person and company.

That commercial semantics is correct: qualification is contextual to a person-company combination. The coupling mechanism is what is replaceable.

Candidate direction:

```text
qualify_dental_person(
    person_identity,
    relationship_context,
    ...
)
```

The qualification decision should continue to include both `person_id` and `company_id`, and two relationships for the same person should be independently qualifiable.

The migration probe verifies that a compatibility adapter can reconstruct the existing V1 input and produce an identical V1 decision for existing one-company records.

### 5. Contact and lead model

These areas require less conceptual change:

- `ContactPoint.owner_id` can continue to point at the stable person identity;
- `Lead` is already a company-linked commercial wrapper and should remain distinct from person identity;
- validated-contact policy can continue to be applied in a person-company qualification context.

## Executable migration probes

`tests/experimental/test_chassis_bakeoff_person_relationship_migration.py` covers:

1. V1 `Person` -> identity + relationship -> V1 round-trip without field loss;
2. one identity with two independent company relationships;
3. dental qualification equivalence through a compatibility adapter;
4. independent company-specific qualification decisions for the same person identity;
5. Person ER record equivalence during an adapter-based migration;
6. rejection of a relationship attached to the wrong person identity.

Existing relationship bake-off probes additionally demonstrate:

- current persistence conflict for one `person_id` across two companies;
- FollowTheMoney `Directorship` support;
- FollowTheMoney `Employment` support;
- relationship role/time/source lineage;
- current immutable company aggregate synchronization pressure.

## Decision metrics

This migration is not approved merely because it is conceptually cleaner. Promotion requires measured outcomes.

### Semantic regression

For frozen V1 fixtures:

- qualification status must remain identical;
- fit, intent and priority must remain identical;
- decision Evidence sets must remain identical;
- contact ownership must remain resolvable;
- existing Person ER triage results must remain identical unless a separately justified ER change is being measured.

Target during compatibility migration: `100%` exact semantic parity on the frozen V1 regression corpus.

### Representation capability

Required new cases:

- one person / two companies;
- one person / concurrent roles;
- one person / historical and current relationships;
- relationship-specific contradictory role evidence;
- same-name distinct people at the same company;
- same person moving between companies.

The candidate must represent these cases without duplicating canonical person identity solely because company context changed.

### Data integrity

Every accepted professional relationship must still be traceable to SearchLeads Evidence. A generic relationship object without accepted Evidence is not sufficient for commercial qualification.

### Migration cost

Record at implementation time:

- production files changed;
- persisted record types added/changed;
- schema migration complexity;
- fixture migration count;
- compatibility adapter LOC;
- regression tests changed;
- data rewrite/backfill requirements.

Do not use LOC alone as a quality metric. It is only one maintenance-cost input.

## Provisional engineering conclusion

`ENGINEERING_EVIDENCE`: embedding one company relationship in canonical `Person` creates an unnecessary identity/context coupling and observable persistence conflicts for multi-organization people.

`ENGINEERING_EVIDENCE`: first-class professional relationship entities provide a better representation for multi-company, temporal and role-specific contexts.

`SEARCHLEADS_PRODUCT_REQUIREMENT`: accepted commercial relationships must remain Evidence-backed.

`HYPOTHESIS`: the best target model is therefore not pure SearchLeads V1 and not pure FollowTheMoney. It is an independent person identity plus first-class relationship records, with SearchLeads Evidence/provenance constraints layered on those relationships.

No production migration should begin until the executable compatibility probes run successfully and the wider regression suite executes on a functioning runner.
