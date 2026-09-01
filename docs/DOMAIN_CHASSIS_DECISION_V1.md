# DOMAIN_CHASSIS_DECISION_V1

Status: `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT`; quantitative execution remains `INFRASTRUCTURE_BLOCKED` until GitHub runners execute steps.

## Decision scope

This decision covers the candidate representation of person identity, company relationship, professional registration, relationship-scoped contacts, relationship-scoped facts, and the raw Evidence bridge.

It does not authorize product migration or merge. PR #113 remains an experiment.

## Decision matrix

| Component | Current SearchLeads | Candidate | Decision | Rationale |
|---|---|---|---|---|
| Person identity | `Person` embeds `company_id` | organization-independent person identity | `REPLACE` | identity and employment/affiliation are different concepts; one person must support multiple companies without mutation or duplication |
| Person↔Company link | embedded `company_id` + relationship evidence | first-class relationship entity | `REPLACE` | provides explicit identity, evidence, role/contact scope and many-company support |
| Company→person snapshot | `Company.person_ids` | derive/query relationships | `REPLACE` | immutable bidirectional snapshots require synchronization and conflict with append-only identity semantics |
| Professional registration | mixed with person/role evidence | person-scoped registration entity | `REPLACE` | CRO/CFO registration is an identity/professional credential, not an organization relationship |
| Corporate contact association | person-level contact reference | relationship-contact association | `COMPOSE` | contact identity can remain reusable, but commercial usability must be scoped to the relevant relationship |
| Professional role facts | person subject | relationship subject when organization-dependent | `COMPOSE` | prevents a role at Company A from qualifying the same identity at Company B |
| Raw Evidence | SearchLeads Evidence store | retain | `KEEP` | captured raw payload, stable evidence identity, replay and integrity are not replaced by FTM statement lineage |
| Evidence integrity | digest/envelope invariants | retain | `KEEP` | required for auditable reprocessing and corruption detection |
| FTM semantic entity/statement model | SearchLeads custom semantic records | FTM semantics + SearchLeads Evidence bridge | `COMPOSE` | FTM is structurally stronger for entities/relations/statements while SearchLeads Evidence is stronger for raw observation identity |
| Qualification | product-specific SearchLeads policy | adapt to new relationship context | `KEEP` | commercial decision is distinct from entity modeling; current contract remains a product policy baseline until challenged separately |

## Candidate domain shape

```text
PersonIdentity
    person_id

Company
    company_id

PersonCompanyRelationship
    relationship_id
    person_id -> PersonIdentity
    company_id -> Company
    evidence_ids[]

ProfessionalRegistration
    registration_id
    person_id -> PersonIdentity
    authority
    number
    status
    evidence_ids[]

ContactPoint
    contact_id
    ...

RelationshipContactLink
    relationship_id -> PersonCompanyRelationship
    contact_id -> ContactPoint
    evidence_ids[]

Intrinsic person facts
    subject_id -> PersonIdentity

Organization-dependent facts
    subject_id -> PersonCompanyRelationship
```

## Migration invariant

Structural migration MUST NOT perform entity resolution.

Required ordering:

1. preserve every legacy Person ID;
2. split each Person into PersonIdentity + PersonCompanyRelationship;
3. move organization-dependent facts to relationship scope;
4. move corporate contact associations to relationship scope;
5. separate ProfessionalRegistration;
6. preserve Evidence and Provenance references;
7. only then run/apply an explicit person-ER decision;
8. repoint relationships to a canonical person identity when and only when ER authorizes it;
9. retain historical observations and Evidence.

A migration that turns two legacy person IDs into one identity before an explicit ER judgement is invalid even if the names match exactly.

## Integrated adversarial gate

`tests/experimental/test_chassis_bakeoff_domain_chassis_integrated.py` adds one integrated gate over the previously separate probes. It checks:

- identity cardinality is preserved by structural split;
- silent merges = 0;
- relationship Evidence is preserved;
- one canonical identity can have two company relationships after an explicit ER phase;
- relationship-scoped role facts do not cross company contexts;
- relationship-scoped corporate contacts do not cross company contexts;
- professional registration is person-scoped and evidence-backed;
- one Evidence may support multiple semantic records;
- one statement may be supported by multiple Evidence records;
- statement identity is not overloaded with Evidence identity.

## Persistence consequence

The existing V3 generic `domain_records` design remains a favorable implementation path for this candidate model. The current experimental persistence probes indicate that new record types can plausibly be added through codec/reference registration without adding physical tables or advancing SQLite `user_version`.

This remains a local-experiment hypothesis until the blocked runner executes the persistence probes.

## FTM mapping

The candidate design maps naturally to FollowTheMoney concepts:

- PersonIdentity → `Person`;
- Company → `Company` / `Organization` as appropriate;
- PersonCompanyRelationship → `Employment`, `Directorship`, or another explicit relationship schema according to semantics;
- ProfessionalRegistration → `Identification`-like representation plus SearchLeads operational status/evidence requirements;
- facts → FTM statements where compatible;
- Evidence → SearchLeads-owned raw observation store linked to statements.

The rule is semantic fit, not forced one-to-one mapping. A generic relationship should not be mislabeled `Employment` merely to fit FTM.

## Decision confidence

High confidence on the structural rejection of `Person.company_id` and mandatory relationship scoping of organization-dependent role/contact data. These are supported by deterministic adversarial counterexamples.

Medium confidence on the exact FTM schema mapping and persistence implementation because the external-library and persistence integration probes have not executed under a working runner in PR #113.

## Consolidated scorecard

See [`SEARCHLEADS_CHASSIS_SCORECARD_V1`](./SEARCHLEADS_CHASSIS_SCORECARD_V1.md) for the current cross-cutting decision table across domain, lineage, normalization, runtime, application chassis and persistence.

## Gate to implementation

This document does not trigger implementation in the product stack. Product implementation waits for the final chassis scorecard. The candidate domain model should be used as the domain challenger in the remaining ER, runtime, application-chassis, and migration-cost comparisons.
