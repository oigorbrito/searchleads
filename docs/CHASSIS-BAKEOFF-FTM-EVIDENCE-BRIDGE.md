# FollowTheMoney statement ↔ SearchLeads Evidence bridge

Status: `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT`.

## Question

Can FollowTheMoney become the semantic entity/statement chassis without losing SearchLeads' stronger raw-Evidence and reprocessing guarantees?

The answer cannot be inferred from `dataset` and `origin` alone. The identifier semantics differ.

## Statement identity is not Evidence identity

FollowTheMoney `Statement` has:

- `id`;
- `entity_id` / `canonical_id`;
- schema/property/value;
- dataset;
- origin;
- first/last seen timestamps.

Its generated ID is a hash of statement semantics such as dataset/entity/property/value. Equality is ID-based.

SearchLeads `Evidence` instead identifies one captured observation/raw payload. One captured page can support multiple different facts/statements, and one semantic fact can be supported by multiple Evidence records.

Therefore:

```text
FTM statement_id != SearchLeads evidence_id
```

Reusing one `evidence_id` as the ID of several FTM statements is unsafe because distinct statements would compare as the same statement identity.

## Candidate bridge

The experiment defines a sidecar concept:

```text
StatementEvidenceLink
    statement_id
    evidence_ids[]
```

This provides both cardinalities required by SearchLeads:

```text
one Evidence -> many semantic statements
many Evidence -> one semantic statement
```

The raw payload itself remains in SearchLeads Evidence persistence.

## Responsibility split

Candidate architecture:

### FollowTheMoney statement layer

Responsible for:

- semantic entity/property representation;
- statement identity;
- dataset and origin metadata;
- first/last-seen metadata;
- canonical entity relationships;
- generic entity graph semantics.

### SearchLeads Evidence layer

Responsible for:

- stable captured-observation identity;
- raw payload preservation;
- storage-integrity checks;
- source capture metadata;
- replay/reprocessing input;
- mandatory evidence policy for commercial facts/relationships.

### Bridge layer

Responsible for:

- mapping semantic statements to the exact Evidence records supporting them;
- preserving many-to-many lineage without overloading either identifier namespace.

## Executable probes

`tests/experimental/test_chassis_bakeoff_ftm_evidence_bridge.py` covers:

1. one SearchLeads Evidence record supporting multiple distinct FTM statements;
2. negative control proving that reusing the Evidence ID as FTM statement ID creates statement-identity collision;
3. one FTM statement linked to multiple Evidence records;
4. simultaneous preservation of FTM dataset/origin/time metadata and SearchLeads raw payload/reprocessing identity.

## Decision consequence

`ENGINEERING_EVIDENCE`: FollowTheMoney `dataset`/`origin` lineage is useful but is not a drop-in replacement for SearchLeads Evidence identity.

`ENGINEERING_EVIDENCE`: SearchLeads does not need to duplicate the full FTM semantic graph merely to keep stronger Evidence. The two responsibilities can be composed with an explicit mapping layer.

`HYPOTHESIS`: if the wider chassis bake-off succeeds, the preferable migration path is:

```text
raw/source capture
       |
SearchLeads Evidence store
       |
StatementEvidenceLink
       |
FTM statements/entities
       |
Nomenklatura identity resolution
       |
SearchLeads qualification/commercial policy
```

This remains experimental until the regression and bake-off suites execute on a functioning runner.
