# SEARCHLEADS_CHASSIS_SCORECARD_V1

Status: `HISTORICAL_DECISION_RECORD`.

This document preserves architecture decisions recorded during the original chassis bake-off. It is not the canonical empirical evidence report for the current harness.

The canonical methodology is `EMPIRICAL-HARNESS-METHODOLOGY.md`. New empirical claims must be represented through the machine-readable claim contract and the canonical study report.

## Reading rule

The legacy labels `KEEP`, `REPLACE`, `COMPOSE`, and `PROVISIONAL_COMPOSE` are historical engineering decision labels. They are not evidence states and they do not establish comparative superiority.

For this historical record:

- `KEEP` means the project chose to retain the current boundary at that point in time;
- `REPLACE` means the project chose to displace that boundary at that point in time;
- `COMPOSE` means the project chose a composed boundary;
- `PROVISIONAL_COMPOSE` means the project chose a composed boundary while explicitly retaining an unresolved evaluation dependency.

Under the current methodology, these map to `decision_state=HISTORICAL_DECISION` plus the recorded legacy label. They must not be interpreted as `evidence_state=SUPPORTED` unless a current claim bundle independently establishes that state.

The previous scorecard also used qualitative columns such as `strong +`, `medium +`, and confidence labels. Those values were engineering assessments, not reproducible empirical measurements. They are therefore removed from the canonical reading of this document.

## Historical component decisions

| Component | SearchLeads boundary at the time | Challenger or alternative considered | Historical decision | Current empirical interpretation |
|---|---|---|---|---|
| Entity model | `Person` embeds `company_id`; `Company.person_ids` snapshot | FTM person plus first-class relationship entities | `REPLACE` | structural/product reasoning recorded; comparative superiority must be re-established through explicit claims if needed |
| Relationship model | person/company coupling inside identity | explicit relationship entities | `COMPOSE` | structural/product reasoning recorded; not a benchmark result |
| Professional registration | mixed with person/role evidence | person-scoped registration entity | `REPLACE` | structural/product reasoning recorded; not a benchmark result |
| Evidence store | SearchLeads raw Evidence with digest/integrity | external statement/evidence approaches | `KEEP` | retention decision; integrity behavior is separately testable |
| Facts/statements | Candidate/Canonical/Conflict model | FTM statements plus Evidence bridge | `COMPOSE` | composition decision; requires claim-level evidence for any comparative benefit assertion |
| Provenance | SearchLeads lineage objects | statement metadata plus SearchLeads Evidence identity | `COMPOSE` | composition decision; not a universal superiority claim |
| Conflict handling | persisted conflict records | derive by default and persist adjudication/cache state | `COMPOSE` | engineering design choice; empirical effect remains workload-dependent |
| Company ER | SearchLeads company matcher/field fusion | Nomenklatura and normalization challengers | `PROVISIONAL_COMPOSE` | historical local evaluation existed, but current canonical support requires preserved raw artifacts and claim traceability |
| Person ER | SearchLeads person resolution | Nomenklatura/Splink/Dedupe challengers | `PROVISIONAL_COMPOSE` | historical review-first decision; no general auto-match authority follows from this record |
| Normalization | SearchLeads normalization | Rigour and `python-stdnum` boundaries | `COMPOSE` | boundary decision; specific normalization effects require controlled evidence |
| Identifier validation | shape-only CNPJ handling in some paths | formal CNPJ validation | `REPLACE` | correctness distinction between canonicalization and validation is separate from library superiority |
| Acquisition runtime | `gap_automation.execution` | Crawlee request/runtime machinery | `COMPOSE` | historical composition decision; throughput/recovery benefit remains an empirical question |
| Planner | SearchLeads business planner | no equivalent challenger selected | `KEEP` | product authority retained; not a benchmark win |
| API/app chassis | SearchLeads app shell | thin FastAPI shell; Yente as optional separate service | `COMPOSE` | historical application decision; comparative operational benefit not established by this label |
| Persistence | generic immutable domain/evidence records | retained shape with additional checks/codecs | `KEEP` | retention decision; correctness and recovery are tested independently |
| Contact discovery | person/company-owned contact discovery | relationship-scoped contact links | `COMPOSE` | structural decision; production-quality benefit requires separate evidence |
| Contact validation | person/company-scoped validation | relationship-scoped validation gate | `COMPOSE` | structural decision; production-quality benefit requires separate evidence |
| Qualification | SearchLeads commercial policy | relationship-scoped inputs | `KEEP` | product-policy authority retained; not an empirical challenger result |
| Selective review | SearchLeads review workflow | derived conflict/evidence queue composition | `COMPOSE` | workflow decision; human-review outcome quality is a separate study question |
| Observability | SearchLeads telemetry | Crawlee request stats plus SearchLeads business telemetry | `COMPOSE` | capability composition; operational benefit requires empirical evaluation |
| Telemetry | domain telemetry mixed with acquisition concerns | explicit adapter boundary | `COMPOSE` | structural decision; not a performance result |
| Deployment | lightweight SearchLeads deployment | thin FastAPI plus optional isolated search service | `COMPOSE` | historical engineering decision; deployment cost remains context-dependent |

## Historical architecture interpretation

The bake-off produced the following historical design direction:

```text
SearchLeads commercial policy
    |
    v
PersonIdentity + PersonCompanyRelationship + ProfessionalRegistration
    |
    v
semantic statements / explicit evidence linkage
    |
    v
SearchLeads raw Evidence + integrity + replay
    |
    v
thin application chassis
    |
    v
acquisition runtime adapter
```

This diagram records a chosen architecture direction. It does not constitute evidence that each selected component is empirically superior to every alternative.

## Claims that require current traceable evidence before reuse

The following legacy statements must not be reused as current empirical conclusions unless represented by a canonical claim bundle with preserved inputs:

- one ER implementation is more accurate than another;
- one normalization boundary improves entity resolution generally;
- Crawlee improves throughput, recovery cost, or production reliability;
- a thin FastAPI shell has lower operational cost than Yente or another service chassis;
- derived conflict handling improves quality or cost;
- any qualitative `strong +` or `medium +` assessment represents a measured effect.

When the required evidence is absent, the appropriate current state is `NOT_EVALUATED` or `INSUFFICIENT_EVIDENCE`, not an inferred winner.

## Current authority

Use this file for historical decision provenance only.

Use the following for current empirical authority:

1. `EMPIRICAL-HARNESS-METHODOLOGY.md` for method and vocabulary;
2. raw manifests/JUnit/observation artifacts for execution evidence;
3. `EMPIRICAL_CLAIM_CONTRACT_V1.json` for claim structure;
4. `scripts/chassis_bakeoff_report.py` output for deterministic claim/evidence aggregation.
