# Chassis Bake-Off — Relationship-Scoped Facts

Status: `EXPERIMENTAL / NOT PRODUCTION AUTHORIZED`

## Problem

Separating Person identity from Company relationship is insufficient if relationship-specific facts remain attached to canonical `person_id`.

A role observed in Company A can become visible while evaluating the same canonical Person in Company B. In the current dental qualification engine, title facts are selected by Person subject ID, so identity consolidation can turn an organizational observation into a cross-company fact unless scope is preserved.

## Negative control

`tests/experimental/test_chassis_bakeoff_relationship_fact_scope.py` models one canonical Person with Company-A and Company-B contexts. A dentist role observed only in A is attached at Person scope, matching the current shape.

The probe checks whether that role is also consumed in Company-B qualification. This is a deliberate negative control and is not reported as executed while CI remains blocked before checkout.

## Candidate model

Relationship-specific facts should use the relationship as semantic subject, or an equivalent evidence-backed association:

```text
PersonIdentity
  └─ PersonCompanyRelationship
       ├─ professional_role_title
       ├─ role start/end/status
       └─ relationship-specific contacts
```

Person-intrinsic facts remain on Person identity. Examples may include identity names and credentials when their scope is truly person-wide. Company facts remain on Company.

The field taxonomy therefore needs an explicit scope decision rather than assuming every Person fact survives identity consolidation unchanged.

## Migration order

The safe structural order is:

1. split V1 Person into identity + relationship;
2. move relationship-specific facts to relationship context;
3. preserve CandidateFact/Provenance/Evidence links;
4. run or apply an explicit Person ER decision;
5. repoint relationships to canonical Person identity.

Identity merge before fact rescoping is rejected because it can mix observations from different organizations.

## Compatibility adapter

The current qualification API expects Person-scoped title facts. The experimental probe therefore remaps only facts belonging to the active relationship back to the legacy Person subject at the adapter boundary.

This permits behavior comparison without changing production qualification code during the bake-off.

## Acceptance criteria

- `cross_relationship_role_leak = 0` on adversarial cases;
- Company-A relationship facts are available in Company-A qualification;
- those facts are absent in Company-B qualification unless independently supported;
- CandidateFact evidence IDs and Provenance remain unchanged during rescoping/migration;
- no structural migration performs identity merge implicitly;
- single-company legacy decisions remain behavior-compatible.

Evidence classification: `LOCAL_EXPERIMENT + ENGINEERING_EVIDENCE`.
