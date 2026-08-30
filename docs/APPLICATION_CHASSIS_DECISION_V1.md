# APPLICATION_CHASSIS_DECISION_V1

Status: `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT`; the repository still has no executable GitHub Actions steps, so this is a structural chassis decision, not a benchmark PASS.

## Scope

This decision covers the root application chassis, not the domain model or runtime adapter.

It asks which shell should host the product surface: the current SearchLeads app, a thin custom FastAPI chassis, or Yente 5.5.0.

## Candidates

### A. Current SearchLeads application evolved

Pros:

- preserves existing integration points;
- minimal near-term churn;
- already owns SearchLeads-specific policy.

Cons:

- tends to accumulate custom application plumbing;
- does not automatically solve search/index/operational surfaces;
- risks keeping more bespoke app code than necessary.

### B. Thin custom FastAPI chassis

Pros:

- keeps SearchLeads domain/policy explicit;
- can host the winning domain/runtime components without forcing their semantics into one upstream framework;
- can add exactly the API, health, readiness, auth, telemetry, and deployment behavior SearchLeads needs;
- avoids Elasticsearch/OpenSearch as a root requirement unless the product actually needs it.

Cons:

- requires some application code to be built and maintained;
- does not get a ready-made search platform for free.

### C. Yente 5.5.0

Pros:

- real application chassis;
- already includes FastAPI, search, match, health, readiness, catalog, algorithm discovery, and operational middleware;
- can host additive SearchLeads routes without an upstream patch.

Cons:

- stable Yente pins older core dependencies than the current bake-off stack;
- requires Elasticsearch/OpenSearch for normal search/match operation;
- does not natively provide SearchLeads qualification, contact discovery, or commercial policy;
- exposes no general authentication/access-control system as part of the service contract.

## Structural conclusion

Yente is a good separate service candidate for search/match, but it is not the best root chassis for SearchLeads product logic.

The reasons are structural, not popularity-based:

- SearchLeads needs product-specific qualification and contact semantics that Yente does not provide natively.
- Yente root adoption pulls in an external search-service burden that SearchLeads does not need to pay unless search becomes the dominant workload.
- SearchLeads would still need a substantial custom boundary for Evidence, qualification, acquisition policy, and compliance.

Therefore the best root chassis is a thin custom FastAPI shell that composes the winning domain/runtime components and leaves Yente as an optional separate service if search/match becomes worth isolating.

## Decision matrix

| Candidate | SearchLeads-owned code avoided | Adapter count | Upstream divergence | External service burden | Product fit | Decision |
|---|---|---|---|---|---|---|
| Current SearchLeads app evolved | low | low | none | low | medium | `DEFER` |
| Thin FastAPI chassis | medium | medium | low | low | high | `COMPOSE` |
| Yente root chassis | high on paper, but not on SearchLeads domain code | medium-high | medium-high | high | medium | `DEFER` |
| Yente as separate service | medium-high for search/match only | medium | low | high, isolated | high for search only | `COMPOSE` |

## Decision

`Application chassis` = `COMPOSE`

Concretely:

- root the product in a thin custom FastAPI chassis;
- compose the winning domain and runtime components there;
- do not make Yente the repository root chassis;
- allow Yente as a separately deployed service only if the search/match boundary later proves worth that operational cost.

## Claims table

| Claim | Evidence available | Execution required? | Decision possible now? | Confidence |
|---|---|---|---|---|
| Yente is a real chassis | static upstream inspection | no | yes | high |
| Yente is the best SearchLeads root chassis | no benchmark evidence | yes | no | low |
| Thin FastAPI can host the winning SearchLeads components | structural analysis | no | yes | medium |
| Yente should remain a separate service option | static architecture analysis | no | yes | medium |

## Implication for deployment

Because the root chassis is thin rather than Yente-root, deployment should stay lightweight and avoid introducing Elasticsearch/OpenSearch as a default product dependency.

That does not eliminate optional search infrastructure later. It only rejects making it the default chassis tax today.
