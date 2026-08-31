# CLEAN_IMPLEMENTATION_TRANSPLANT_MATRIX_V1

Status: CANONICAL

## Lineage

- engineering_baseline_sha: `fb774cc6ddc4f8c7fc397476f868bd1de3a70506`
- clean_base_sha: `2c3ffcdad2fcc6527f299e8dc0e6a402df36b35d`
- implementation_branch: `work/chassis-implementation-v1`

## Matrix

| Component | Action | Reason |
|---|---|---|
| `Company` | KEEP | canonical company record already exists and remains the root company entity |
| `Person` | TEMPORARY_ADAPTER | legacy observation-scoped person snapshot remains useful during migration, but not as canonical identity |
| `PersonIdentity` | PORT | canonical person identity primitive for relationship-first modeling |
| `PersonCompanyRelationship` | REWRITE | explicit first-class relationship replaces `Person.company_id` semantics |
| `ProfessionalRegistration` | PORT | person-scoped registration primitive is already canonically specified |
| `ContactPoint` | KEEP | contact record remains durable evidence-backed contact storage |
| `RelationshipContactLink` | REWRITE | relationship-scoped contact association prevents cross-company leakage |
| `Evidence` | KEEP | raw evidence remains first-class and integrity-protected |
| `Statement` | PORT | semantic fact representation replaces overloaded fact semantics in the canonical layer |
| `StatementEvidenceLink` | REWRITE | explicit many-to-many bridge is required for statement lineage |
| `Lead` | KEEP | commercial wrapper remains separate from identity decisions |
| `QualificationDecision` | PORT | explicit qualification decision object is required for downstream compatibility |
| `Company.person_ids` | TEMPORARY_ADAPTER | snapshot field can exist only as a compatibility shim during migration |
| `Person.company_id` | TEMPORARY_ADAPTER | legacy field is preserved only until consumers migrate to relationship scope |

## Rules

- Do not silently merge identities during structural migration.
- Preserve legacy IDs where existing consumers require them.
- Prefer relationship derivation over persisted snapshot duplication.
- Keep raw Evidence distinct from any derived semantic statement.
- Use compatibility adapters only when a consumer cannot yet be updated.

## Current Status

- canonical domain types have been added to the clean line
- persistence codecs already round-trip the new types
- remaining work is wiring the canonical types into the operational consumers
