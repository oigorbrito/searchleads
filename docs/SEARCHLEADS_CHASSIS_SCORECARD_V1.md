# SEARCHLEADS_CHASSIS_SCORECARD_V1

Status: `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT`.

Live authority as of 2026-08-30:

- PR #113 is open on `work/chassis-bakeoff-v1` against `work/persistence-load-identity-invariants-v1`.
- The latest GitHub Actions runs for the PR complete with `failure`, but job payloads expose `steps: []` and no logs, so there is still no executable benchmark evidence to interpret.
- Therefore all scorecard decisions below are architecture decisions, not PASS claims.

## Reading rule

`KEEP` means the current SearchLeads implementation already fits the product requirement well enough that replacement is not justified by the current evidence.

`REPLACE` means the current implementation/model is structurally wrong or too costly and should be displaced by the challenger.

`COMPOSE` means the right answer is a composition of SearchLeads and external components.

`DEFER` means the claim is still benchmark-dependent or the runner has not yet produced usable evidence.

## Scorecard

| Component | Current SearchLeads | Best challenger | Decision | Evidence class | Quality delta | False-positive/merge delta | Operational delta | Custom-code delta | Migration cost | Upstream divergence | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Entity model | `Person` embeds `company_id`; `Company.person_ids` is a snapshot | FTM `Person` + first-class relationship entities | `REPLACE` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` | strong + | strong + | + | - | medium | low | high |
| Relationship model | person/company coupling inside identity | `PersonCompanyRelationship` / FTM `Directorship` / `Employment` | `COMPOSE` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` | strong + | strong + | + | - | medium | low | high |
| Professional registration | mixed with person/role evidence | person-scoped registration entity | `REPLACE` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` | strong + | + | + | - | medium | low | high |
| Evidence store | SearchLeads raw Evidence with digest/integrity | no better challenger found yet | `KEEP` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` | strong + | strong + | + | 0 | low | 0 | high |
| Facts/statements | `CandidateFact`/`CanonicalFact`/`Conflict` overlap semantics | FTM `Statement` + explicit Evidence bridge | `COMPOSE` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` | medium + | strong + | + | - | medium | low | medium |
| Provenance | parallel SearchLeads lineage objects | FTM statement metadata + SearchLeads Evidence identity | `COMPOSE` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` | medium + | strong + | + | - | medium | low | medium |
| Conflict handling | persisted conflict records and derived workflow state | derive by default; persist only adjudication or irreducible cache state | `COMPOSE` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` | medium + | medium + | + | - | low | low | medium |
| Company ER | current company matcher / field fusion | Nomenklatura `LogicV2` / `RegressionV1` / `EntityResolveRegression` + Rigour normalization | `PROVISIONAL_COMPOSE` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` + `LOCAL_BENCHMARK` | strong + | medium + | review-first | medium | low | low | medium |
| Person ER | current person resolution | Nomenklatura / Splink / Dedupe challengers | `PROVISIONAL_COMPOSE` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` + `LOCAL_BENCHMARK` | strong + | strong + | review-first | medium | low | low | medium |
| Normalization | duplicated SearchLeads name normalization | Rigour + `python-stdnum` + official CNPJ oracle | `COMPOSE` | `OFFICIAL_SPEC` + `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` | medium + | medium risk | + | - | medium | low | medium |
| Identifier validation | shape-only CNPJ canonicalization in parts of the stack | `python-stdnum` / official Receita-Serpro CNPJ contract | `REPLACE` | `OFFICIAL_SPEC` + `ENGINEERING_EVIDENCE` | strong + | strong + | + | - | low | low | high |
| Acquisition runtime | `gap_automation.execution` | Crawlee request queue / retry / sessions / stats | `COMPOSE` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` | medium + | neutral | strong + | - | medium | low | medium |
| Planner | SearchLeads business planner and qualification policy | no challenger yet | `KEEP` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` | 0 | 0 | + | 0 | low | 0 | high |
| API/app chassis | thin SearchLeads app layer with growing custom ops code | thin FastAPI chassis; Yente only as separate service if needed | `COMPOSE` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` | medium + | neutral | strong + | - | medium | medium | medium |
| Persistence | generic immutable `domain_records` + `evidence_records` + v3 integrity | keep storage shape; extend codecs and semantic checks | `KEEP` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` | + | + | + | 0 | low | 0 | high |
| Contact discovery | person-owned corporate contact discovery | relationship-scoped contact links | `COMPOSE` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` | strong + | strong + | + | - | medium | low | high |
| Contact validation | person/company-scoped validation state | relationship-scoped validation gate | `COMPOSE` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` | strong + | strong + | + | - | medium | low | high |
| Qualification | SearchLeads commercial policy | keep policy; feed it relationship-scoped inputs | `KEEP` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` | 0 | 0 | + | 0 | low | 0 | high |
| Selective review | SearchLeads review workflow | derived conflict + evidence queue composition | `COMPOSE` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` | medium + | medium + | + | - | medium | low | medium |
| Observability | current SearchLeads telemetry / measurement | Crawlee stats + SearchLeads business telemetry | `COMPOSE` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` | medium + | 0 | strong + | - | low | low | medium |
| Telemetry | domain telemetry split from acquisition telemetry | explicit adapter boundary | `COMPOSE` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` | medium + | 0 | strong + | - | low | low | medium |
| Deployment | current lightweight SearchLeads deployment path | thin FastAPI app + optional external search/service split | `COMPOSE` | `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT` | medium + | neutral | strong + | - | medium | medium | medium |

## Consolidated architecture

The leading shape after the current bake-off is:

```text
SearchLeads commercial policy
    |
    v
PersonIdentity + PersonCompanyRelationship + ProfessionalRegistration
    |
    v
FTM semantic statements
    |
    v
explicit StatementEvidenceLink many-to-many bridge
    |
    v
SearchLeads raw Evidence + integrity + replay
    |
    v
thin FastAPI chassis
    |
    v
Crawlee acquisition runtime adapter
```

The current SearchLeads person model does not survive unchanged. The raw Evidence store does.

The strongest provisional decisions are:

- `Person.company_id` must not remain part of canonical identity.
- relationship scope must own company-dependent role/contact facts.
- raw Evidence identity must remain distinct from statement identity.
- commercial qualification must stay separate from entity identity.
- Crawlee is a strong acquisition-runtime challenger, but only as an adapter.
- Yente is useful as a separate search/match service candidate, not as the root chassis.
- conflict handling should derive by default and persist only adjudication or irreducible cache state.

## Residual gaps

- Company ER and Person ER now have executed local benchmark policies, but external challenger breadth remains partially blocked.
- execution of the benchmark harness is still blocked for some challengers by Windows build/runtime dependencies.
- deployment cost, throughput and recovery are still benchmark-dependent.

Until runners produce real step logs, those gaps remain `DEFER` and must not be narrated as PASS.
