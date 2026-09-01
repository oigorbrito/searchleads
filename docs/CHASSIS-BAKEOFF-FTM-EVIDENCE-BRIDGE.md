# FollowTheMoney statement ↔ SearchLeads Evidence bridge

Status: `LOCAL_EXPERIMENT`.

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

When `SEARCHLEADS_EMPIRICAL_OBSERVATION_DIR` is configured, those probes emit these stable structured observations:

- `ftm-evidence-bridge-one-to-many-v1`;
- `ftm-evidence-id-overload-negative-control-v1`;
- `ftm-evidence-bridge-many-to-one-v1`;
- `ftm-searchleads-lineage-responsibility-split-v1`.

All four are `FUNCTIONAL_PROBE` observations. They record bounded identifier/cardinality behavior under the pinned environment; they do not assign `evidence_state` or an architecture decision.

## Interpretation boundary

`OBSERVATION`: the current probe design tests whether explicit sidecar mapping can preserve the two required Evidence↔statement cardinalities while keeping FTM lineage fields separate from SearchLeads raw-Evidence identity.

`OBSERVATION`: the negative control intentionally forces one `evidence_id` onto two semantically distinct FTM statements and checks the resulting identity collision. This demonstrates that the specific identifier-overloading mapping is unsafe; it is not evidence that FollowTheMoney itself is defective.

`HYPOTHESIS`: a composition using an explicit statement↔Evidence mapping can retain FTM semantic lineage together with SearchLeads raw capture/reprocessing responsibilities.

`DECISION`: no active `COMPOSE`, `ADOPT`, `RETAIN`, or `REJECT` decision is authorized by this document. Any historical engineering preference remains separate from the empirical claim state.

The broader candidate shape remains:

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

The current structured observations remain `NOT_EVALUATED` until the probes execute on a functioning runner and their artifacts are available to the canonical report. A passing functional probe would support only its bounded behavior claim; it would not by itself establish production suitability or comparative superiority.
