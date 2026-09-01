# FACT_LINEAGE_CHASSIS_DECISION_V1

Status: `HISTORICAL_DECISION_RECORD`.

This document preserves a prior engineering direction for semantic statements, raw Evidence, provenance, and conflict representation. It is not a canonical empirical result under the current harness methodology.

Historical decision label: `COMPOSE`.

## Research question

Which fact/provenance responsibilities can be represented by a semantic statement layer while preserving SearchLeads raw-observation identity, integrity, replay, qualification semantics, and auditability?

The relevant empirical question is not whether an external library can instantiate a statement. It is whether a candidate composition preserves the declared behavior and reduces a defined cost/complexity construct under a reproducible method.

## Historical responsibility split

| Current concept | Historical direction | Current methodological interpretation |
|---|---|---|
| SearchLeads raw `Evidence` | retain independent captured-input identity/store | integrity/replay behavior is independently testable; retention decision is not a benchmark win |
| Evidence digest/envelope integrity | retain | correctness/integrity requirement |
| semantic statements | compose where compatible | capability/semantic fit requires explicit compatibility probes |
| statement↔Evidence association | explicit many-to-many bridge | cardinality/integrity requirement to be exercised functionally |
| `CandidateFact` | defer permanent-core decision | comparative simplification requires reconstruction/complexity evidence |
| `CanonicalFact` | defer permanent-core decision | persistence-vs-projection trade-off requires measured reconstruction/operational evidence |
| persisted `Conflict` | prefer derivation plus persisted adjudication where needed | benefit/cost of derivation vs persistence requires a declared workload if claimed empirically |
| SearchLeads `Provenance` | retain only non-overlapping responsibilities | reduction claim requires evidence of no lineage loss and reproducible reconstruction |

These are historical engineering directions, not `SUPPORTED` empirical superiority claims by themselves.

## Identity invariant

`statement_id` and `evidence_id` are different namespaces.

A semantic statement identifies an assertion. Evidence identifies a captured observation/raw input. The model must support:

```text
one Evidence -> many semantic statements
one semantic statement -> many Evidence records
```

Collapsing those identities would create semantic collisions. This is a correctness/integrity constraint, not a performance result.

## Raw Evidence responsibilities

SearchLeads Evidence is intended to preserve:

- stable captured-observation identity;
- raw payload retention;
- source capture metadata not reducible to a semantic statement;
- replay/reprocessing input;
- digest/integrity verification;
- mandatory evidence requirements for consequential facts and relationships.

A semantic statement layer may overlap with some provenance semantics but does not automatically replace raw Evidence identity.

## Bridge hypothesis

A logical many-to-many bridge such as:

```text
StatementEvidenceLink
    statement_id
    evidence_ids[]
```

is one candidate representation. The exact physical storage shape is not fixed by this historical decision.

A functional probe should establish cardinality, referential integrity, reconstruction, and corruption/missing-Evidence behavior before the representation is considered compatible.

## CandidateFact / CanonicalFact claim boundary

No deletion or replacement claim is authorized merely because another framework offers semantic statements.

Any claim that SearchLeads can remove or shrink these concepts must preserve and evaluate, as applicable:

- raw Evidence requirements;
- normalization traceability;
- qualification behavior;
- conflict visibility;
- replay/reprocessing;
- deterministic persistence/reconstruction;
- decision/audit identity.

If the claim is lower complexity or lower operational cost, the study must define and measure that construct rather than infer it from record-type count alone.

## Conflict representation

A historical candidate direction was to derive reconstructable conflict state and persist only irreducible human adjudication or justified cache state.

This is a design hypothesis. The following are distinct claims requiring different evidence:

- conflict state can be reconstructed correctly: functional/reconstruction evidence;
- derivation is cheaper than persistence: controlled workload/cost evidence;
- derivation improves auditability: explicit auditability construct and evaluation;
- persisted workflow identity is necessary: functional/product requirement evidence.

No one of those claims implies the others.

## Required executable gates

A current fact-lineage claim bundle should preserve evidence for relevant gates such as:

1. one raw Evidence supporting multiple distinct semantic statements;
2. one semantic statement corroborated by multiple independent Evidence records;
3. conflicting values retained without destructive overwrite;
4. dataset/origin/time metadata retained independently from raw Evidence identity;
5. replay from Evidence rebuilding the declared semantic inputs;
6. corruption/missing Evidence detection;
7. qualification-relevant facts remaining evidence-backed;
8. relationship-scoped facts remaining scoped after conversion;
9. distinct origins not collapsing solely because normalized values match;
10. adjudication/judgement state remaining separate from observation identity.

JUnit execution status alone is not sufficient when a claim depends on measurements or reconstructed outputs not represented by JUnit. Those observations must be preserved as structured artifacts.

## Complexity/performance claims

Potential observations include:

- owned record types;
- owned implementation LOC excluding tests/docs;
- adapter LOC;
- semantic-reference rules;
- persistence codec rules;
- write amplification;
- read operations needed for reconstruction;
- round-trip/replay correctness;
- corruption-detection outcomes;
- latency/memory under a declared representative fact workload.

Counts such as LOC or record-type count are descriptive observations. They do not become maintainability or quality metrics without a method that justifies that construct.

## Decision semantics

The historical fact-lineage direction remains recorded as `COMPOSE`:

```text
semantic statements
        ↕ explicit evidence links
SearchLeads raw Evidence + integrity
        ↕ derived conflict state / adjudication events
```

Under the current vocabulary this is `decision_state=HISTORICAL_DECISION` with a legacy label of `COMPOSE`.

Current empirical support for any stronger claim must come from the canonical claim/evidence report. Missing required inputs result in `INSUFFICIENT_EVIDENCE`; absent execution results in `NOT_EVALUATED`.
