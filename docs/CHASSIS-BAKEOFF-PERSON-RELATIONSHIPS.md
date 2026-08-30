# Chassis Bake-Off — Person Relationship Model V1

## Question

Should SearchLeads continue embedding one `company_id` and relationship Evidence inside each `Person`, or should person identity be independent while professional/company relationships become first-class entities?

The current SearchLeads design is a baseline, not a protected invariant. The FollowTheMoney 4.10.2 `Directorship` model is the current challenger.

## Current SearchLeads model

`Person` contains:

```text
person_id
company_id
relationship_evidence_ids
candidate_fact_ids
canonical_fact_ids
contact_point_ids
```

Construction requires a non-empty `company_id` and at least one relationship Evidence ID.

Persistence uses `(record_type, record_id)` as immutable identity. Reusing one `person_id` with a different `company_id` therefore attempts to reuse the same immutable Person ID with different content and raises `PersistenceConflictError`.

This means the current model couples:

```text
person identity
    +
company relationship context
```

in one persisted record.

## FollowTheMoney challenger

FollowTheMoney 4.10.2 separates the concepts:

```text
Person
Organization / Company
Directorship
```

`Directorship` is a non-matchable relationship entity. It requires `director` and `organization`, and natively carries relationship context including:

- `role`;
- `status`;
- `startDate`;
- `endDate`;
- `sourceUrl`;
- proof/document references and other inherited interval metadata.

A single `Person` ID can therefore participate in multiple distinct relationship entities without mutating or duplicating the Person identity.

## Executable probes

`test_chassis_bakeoff_person_relationship_model.py` tests:

1. a standalone FTM Person plus a Directorship to one company;
2. role/start-date/source URL on the relationship rather than on Person;
3. one FTM Person ID linked to two organizations through two separate Directorship entities;
4. the equivalent SearchLeads attempt using one `person_id` and two company contexts;
5. the expected SearchLeads persistence conflict caused by embedding `company_id` in immutable Person content;
6. a neutral concept scorecard that does not assume either model wins.

The existing FTM/Nomenklatura scorecard was also corrected: standalone Person identity is no longer described as a SearchLeads advantage. Relationship modeling and Evidence enforcement are separate dimensions.

## Evidence trade-off

The challenger is stronger on identity/context separation and multi-organization representation, but SearchLeads currently has a stronger hard construction rule for relationship Evidence.

These are not mutually exclusive ideas.

A candidate model, pending execution and broader tests, is:

```text
Person identity
    |
    +-- ProfessionalRelationship / Directorship-like entity
            person_id
            company_id
            role
            start/end dates
            relationship Evidence IDs
            relationship CandidateFacts / Provenance
```

This would preserve SearchLeads' requirement that a commercial person-company association be evidence-backed while adopting the external idea that employment/directorship context should not define person identity.

## Why this matters for SearchLeads

The current embedded model can become problematic when a person:

- serves two companies at the same time;
- changes employer;
- has multiple roles over time;
- is a board member at one company and employee at another;
- appears in historical and current relationship evidence;
- must be resolved as one human identity before commercial qualification chooses the relevant company relationship.

A relationship entity can represent these states without forcing duplicate Person identities or overwriting history.

## Decision metrics

The model decision should eventually measure:

- number of Person identity duplicates caused by company changes/multiple affiliations;
- false person merges and false splits;
- ability to preserve historical relationships;
- ability to express overlapping roles;
- amount of custom schema/persistence code;
- Evidence/provenance completeness at relationship level;
- qualification correctness when a person has multiple company contexts;
- migration complexity from current persisted Person records.

The structural persistence-conflict probe is engineering evidence, not a market prevalence estimate. We do not yet know how frequently multi-company professionals occur in the target lead population.

## Current candidate direction

If the executable probes behave as inspected, the FTM relationship-entity idea is the stronger conceptual baseline for identity modeling, while the SearchLeads Evidence requirement remains a candidate policy to add on top.

This is deliberately a compositional conclusion, not loyalty to either implementation:

```text
FTM relationship separation
+
SearchLeads evidence-backed relationship policy
```

may outperform both original models.

No production migration is authorized by this experiment. The GitHub Actions runner still fails before test steps, so no local pytest PASS is claimed yet.
