# Chassis Bake-Off — Relationship-Scoped Contacts

Status: `EXPERIMENTAL / NOT PRODUCTION AUTHORIZED`

## Problem

The current `ContactPoint` owner is a `Person` or `Company`. That is adequate while a Person is structurally tied to exactly one Company.

Once Person identity is separated from organizational relationships, a Person-owned corporate contact can become ambiguous. A validated address such as `ana@company-a.example` must not automatically satisfy a validated-contact gate while evaluating the same Person in the context of Company B.

## Negative control

`tests/experimental/test_chassis_bakeoff_relationship_contact_scope.py` constructs one Person identity with two legacy relationship contexts and one validated Person-owned email associated with Company A.

Under the current qualification API, the contact is selected by:

```text
owner_id in {person.person_id, person.company_id}
```

Therefore a Person-owned contact is visible in both company contexts.

This is an intentional negative-control probe, not a claim of executed failure while CI remains blocked.

## Candidate fix

A minimal compatibility design adds an evidence-backed association:

```text
RelationshipContactLink
  relationship_id
  contact_id
  evidence_ids
```

Qualification receives only contacts linked to the active Person↔Company relationship (plus any explicitly company-owned contacts allowed by policy).

A more invasive alternative is allowing `ContactPoint.owner_id` to point directly at a relationship entity. The bake-off does not choose between these representations yet.

## Acceptance criteria

A contact-scoping design may replace the current ownership rule only if executed tests demonstrate:

- validated Company-A contact satisfies the Company-A relationship gate;
- the same contact does not satisfy Company-B relationship gate without independent association Evidence;
- `cross_relationship_contact_leak = 0` on adversarial fixtures;
- discovery and validation Evidence remain reachable;
- generic personal contacts, when policy allows them to span relationships, can be represented without duplicating ContactPoint payloads;
- existing single-company behavior remains compatible.

## Architectural implication

The current candidate domain becomes:

```text
PersonIdentity
  ├─ PersonCompanyRelationship
  │    └─ RelationshipContactLink → ContactPoint
  └─ ProfessionalRegistration
```

Identity, organizational relationship, contact applicability, and professional-registration status are separate claims with separate Evidence.

Evidence classification: `LOCAL_EXPERIMENT + ENGINEERING_EVIDENCE`.
