# APPLICATION_CHASSIS_DECISION_V1

Status: `HISTORICAL_DECISION_RECORD`.

Historical decision label: `COMPOSE` around a thin custom FastAPI root chassis, with Yente retained only as an optional separate search/match service candidate.

Current empirical reading: comparative superiority of that application chassis is `NOT_EVALUATED` unless a current canonical claim bundle supplies reproducible comparative evidence.

## Scope

This record covers the root application chassis, not the domain model or acquisition runtime adapter.

The alternatives originally considered were:

- evolving the current SearchLeads application;
- a thin custom FastAPI chassis;
- Yente as the root chassis;
- Yente as a separately deployed service for search/match only.

## Structural observations

The original analysis identified product and dependency constraints:

- SearchLeads requires product-specific qualification, Evidence, contact, and compliance semantics.
- A thin FastAPI shell can host those SearchLeads-owned boundaries without requiring Elasticsearch/OpenSearch by default.
- Yente provides an application/search chassis with search and matching capabilities.
- Yente does not natively replace SearchLeads product-specific qualification, Evidence, acquisition policy, or compliance contracts.
- Root adoption of Yente introduces search-service infrastructure that may be unnecessary if search is not the dominant workload.

These statements are structural/capability observations. They do not establish lower latency, lower cost, greater reliability, or superior maintainability in production.

## Historical decision

The project recorded the following application direction:

```text
thin SearchLeads-owned application shell
    -> SearchLeads domain/policy components
    -> optional external runtime/search services behind explicit adapters
```

The historical action was to compose a thin custom FastAPI root and defer Yente-root adoption.

Under the current methodology this is preserved as `decision_state=HISTORICAL_DECISION`; the historical label `COMPOSE` is decision provenance, not evidence state.

## Current claim states

| Claim | Evidence class | Current evidence state | Allowed conclusion |
|---|---|---|---|
| Yente provides a real application/search chassis | `STATIC_INSPECTION` | `SUPPORTED` for capability presence | Yente exposes the inspected application/search capabilities |
| SearchLeads has product-specific policy not natively supplied by Yente | `STATIC_INSPECTION` / product contract | `SUPPORTED` for boundary presence | an adapter or SearchLeads-owned layer remains necessary |
| Thin FastAPI can host SearchLeads-owned components | `STATIC_INSPECTION` / bounded functional integration when executed | `PARTIALLY_SUPPORTED` until current artifacts are attached | structural feasibility only |
| Thin FastAPI has lower operational cost than Yente-root | comparative operational study required | `NOT_EVALUATED` | no cost conclusion |
| Thin FastAPI is more reliable or maintainable than Yente-root | controlled/longitudinal evidence required | `NOT_EVALUATED` | no comparative reliability/maintainability conclusion |
| Yente should never be used | no supporting evidence | `NOT_SUPPORTED` | Yente remains evaluable for a scoped search/match service role |

## Evidence required for a current active chassis recommendation

A current empirical recommendation would need a declared research question and reproducible artifacts appropriate to the claimed benefit. Depending on the claim, that may include:

- equivalent functional workloads across candidate shells;
- deployment/startup behavior;
- resource use;
- latency/throughput where relevant;
- failure/recovery behavior;
- operational dependency burden measured under a defined environment;
- maintenance-change tasks if maintainability is the research question.

Feature presence or dependency inspection is insufficient to establish comparative production benefit.

## Current authority

This document preserves why the historical engineering decision was made. It must not be cited as evidence that the selected chassis empirically outperforms alternatives.
