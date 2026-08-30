# FACT_LINEAGE_CHASSIS_DECISION_V1

Status: `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT`; external execution remains `INFRASTRUCTURE_BLOCKED` while Actions jobs terminate without usable step logs.

## Question

Which SearchLeads fact/provenance concepts should survive if FollowTheMoney becomes the semantic entity/statement layer?

The decision separates semantic truth representation from raw-observation preservation. Those responsibilities need not live in one record type.

## Decision matrix

| Current concept | Candidate disposition | Decision |
|---|---|---|
| `Evidence` raw observation | retain as independent captured-input identity/store | `KEEP` |
| Evidence digest/envelope integrity | retain | `KEEP` |
| FTM `Statement` semantics | use for semantic entity/property/value representation where compatible | `COMPOSE` |
| statement↔Evidence association | explicit many-to-many bridge | `COMPOSE` |
| `CandidateFact` | transitional compatibility/input projection; do not assume permanent core primitive | `DEFER` |
| `CanonicalFact` | candidate projection/aggregation over statements; permanence not yet justified | `DEFER` |
| persisted `Conflict` | derive by default; persist only adjudication or irreducible cache state | `COMPOSE` |
| SearchLeads `Provenance` | retain only responsibilities not represented by FTM statement metadata + explicit Evidence links | `COMPOSE` |

## Identity rule

`statement_id` and `evidence_id` are different namespaces and must remain different.

A statement identifies a semantic assertion. Evidence identifies a captured observation/raw input. Therefore both cardinalities are required:

```text
one Evidence -> many statements
one statement -> many Evidence records
```

Any implementation that stores `evidence_id` as the FTM statement identifier is rejected because distinct semantic assertions from the same captured document would collide.

## Proposed responsibility split

### Semantic statement layer

Prefer FollowTheMoney statements for:

- entity/property/value semantics;
- statement identity;
- dataset/origin metadata;
- observed temporal metadata supported by FTM;
- canonical-entity linkage;
- generic graph semantics.

### Raw Evidence layer

Keep SearchLeads Evidence for:

- stable captured-observation identity;
- raw payload retention;
- source capture metadata not reducible to a semantic statement;
- replay/reprocessing input;
- digest/integrity verification;
- mandatory evidence requirements for commercially consequential facts and relationships.

### Bridge layer

Use an explicit link such as:

```text
StatementEvidenceLink
    statement_id
    evidence_ids[]
```

A normalized physical representation may instead store one row per `(statement_id, evidence_id)` pair. The logical requirement is many-to-many cardinality, not this exact storage shape.

## CandidateFact / CanonicalFact

No deletion is authorized yet.

`CandidateFact` currently packages raw value, normalized value, evidence references, provenance, confidence, decision class and observation time. Some of those responsibilities overlap FTM statements; others are SearchLeads-specific workflow concerns.

The correct experiment is therefore not "can FTM instantiate a statement?" but whether the same downstream behavior can be expressed with fewer owned concepts while preserving:

- raw Evidence requirements;
- normalization traceability;
- qualification behavior;
- conflict visibility;
- reprocessing;
- deterministic persistence/reconstruction.

Until that comparison executes, `CandidateFact` is `DEFER`, not `KEEP` and not `REPLACE`.

`CanonicalFact` is similarly treated as a possible projection/aggregation rather than assumed durable storage. If canonical values can be reproduced deterministically from statements + judgements + policy, persisting a second truth record may be unnecessary. That must be tested for complexity, latency, reproducibility and auditability.

## Conflict representation

Default candidate: derive conflicts from multiple materially incompatible statements for the same semantic subject/property under the active policy.

Persist a dedicated Conflict record only if experiments demonstrate a concrete advantage such as:

- substantially cheaper repeated reads;
- required stable workflow identity for human review;
- preservation of historical adjudication state that cannot be reconstructed from statements/judgements;
- materially simpler audit semantics.

Conflict handling is therefore no longer a structural blocker. The best architecture is:

- derive conflict state from statements and Evidence by default;
- persist only the irreducible human adjudication event or a provable cache;
- never let a persisted Conflict record become the only source of truth for reconstructable lineage.

## Provenance composition

FTM `dataset`, `origin`, temporal metadata and statement identity cover part of current SearchLeads provenance. They do not by themselves guarantee raw payload identity, integrity, or exact replay input.

The target is to measure whether SearchLeads `Provenance` can shrink to only the non-overlapping responsibilities rather than keeping two parallel lineage systems.

Success criterion:

```text
minimum owned lineage model
+ no evidence loss
+ deterministic reconstruction
+ no semantic identifier collision
```

## Required executable gates

The combined fact-lineage bake-off must demonstrate:

1. one raw Evidence supporting multiple distinct semantic statements;
2. one semantic statement corroborated by multiple independent Evidence records;
3. conflicting values retained without destructive overwrite;
4. dataset/origin/time metadata retained independently from raw Evidence identity;
5. replay from Evidence can rebuild the same semantic inputs;
6. corruption/missing Evidence is detectable;
7. qualification-relevant facts cannot become evidence-free through conversion;
8. relationship-scoped facts remain scoped after statement conversion;
9. no silent collapse of two origins solely because normalized semantic values match;
10. explicit handling of adjudication/judgements separate from observation identity.

Existing PR #113 probes cover several of these individually; `test_chassis_bakeoff_domain_chassis_integrated.py` adds cross-cutting cardinality and scoping gates.

## Complexity benchmark to collect when runners work

For SearchLeads baseline versus FTM+Evidence bridge, record:

- number of owned record types;
- owned implementation LOC excluding tests/docs;
- adapter LOC;
- semantic-reference rules;
- persistence codec rules;
- write amplification per observation;
- read operations required to reconstruct a qualified decision;
- round-trip/replay correctness;
- corruption-detection coverage;
- latency and memory for representative fact sets.

No winner on those quantitative dimensions is claimed while the runner is blocked.

## Current decision

`COMPOSE` is the leading fact-lineage architecture:

```text
FollowTheMoney semantic statements
        ↕ explicit many-to-many links
SearchLeads raw Evidence + integrity
        ↕ derived conflict state / adjudication events
```

This is stronger than either extreme currently supported by evidence:

- FTM lineage alone does not replace raw Evidence/replay guarantees;
- retaining the entire SearchLeads fact/provenance stack unchanged would duplicate mature semantic statement machinery without proof that the duplication is valuable;
- persisting Conflict as a primary truth store is unnecessary unless repeated-read cost or audit semantics prove it is needed.

The exact fate of `CandidateFact`, `CanonicalFact`, and the residual `Provenance` schema remains intentionally deferred until executable complexity and reconstruction benchmarks run.

## Consolidated scorecard

See [`SEARCHLEADS_CHASSIS_SCORECARD_V1`](./SEARCHLEADS_CHASSIS_SCORECARD_V1.md) for the current cross-cutting decision table across domain, lineage, normalization, runtime, application chassis and persistence.
