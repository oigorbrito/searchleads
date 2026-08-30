# Chassis Bake-Off — Application V1

## Question

This experiment tests the user's stronger chassis hypothesis: not merely whether an external matcher improves one SearchLeads subsystem, but whether a mature application chassis can absorb the best SearchLeads ideas with less custom infrastructure and less upstream modification.

SearchLeads remains a baseline, not a protected architecture. Yente is a challenger, not an assumed winner.

## Challenger

Pinned stable application release:

```text
yente == 5.5.0
```

The Yente job is intentionally isolated from the core chassis job.

Yente 5.5.0 pins:

```text
followthemoney == 4.9.2
nomenklatura == 4.10.0
rigour == 2.1.2
```

The current core bake-off independently pins newer releases:

```text
followthemoney == 4.10.2
nomenklatura == 4.14.0
rigour == 2.3.1
python-stdnum == 2.2
```

Installing both generations into one environment would force dependency resolution to choose one generation and would contaminate the comparison. Separate jobs make the trade-off explicit.

## Engineering evidence in Yente 5.5.0

Yente is a genuine application chassis, not only a matching library. Its stable release provides:

- FastAPI application assembly;
- `/match/{dataset}` query-by-example matching;
- `/search/{dataset}` entity search;
- OpenRefine reconciliation API;
- entity/data access endpoints;
- `/healthz` liveness;
- `/readyz` index readiness;
- `/catalog` data/index metadata;
- `/algorithms` matcher discovery;
- background catalog refresh/reindex lifecycle;
- Elasticsearch/OpenSearch provider abstraction;
- request logging and trace-context middleware;
- CORS and gzip middleware;
- maximum URL length enforcement;
- bounded batch, result and match-candidate settings;
- downloaded entity-data checksum verification;
- OpenTelemetry instrumentation/freshness metrics in the stable release;
- container signing/SBOM release hardening.

These capabilities are relevant because building them ourselves would add non-domain code and maintenance burden.

## Important constraints

### External search service

Yente 5.5.0 requires an external Elasticsearch 9.x or supported OpenSearch service for its normal search/match operation. SearchLeads' current development persistence is much lighter-weight. Therefore Yente can reduce application code while increasing infrastructure footprint and operating cost.

That trade-off must be measured rather than assumed to be favorable.

### Authentication

The Yente service contract explicitly states that the API does not provide general authentication or access control. The administrative reindex endpoint has a dedicated update token, but this is not a general application authorization system.

If SearchLeads becomes multi-user or internet-facing, authentication remains SearchLeads work or another infrastructure responsibility.

### Product domain

Yente's native product domain is entity search/screening/matching. It does not natively implement SearchLeads concepts such as:

- lead qualification policy;
- contact discovery/validation lifecycle;
- commercial intent;
- campaign readiness;
- legal/compliance gates for outreach;
- source-specific acquisition planning;
- SearchLeads Evidence/truth promotion policy.

Those concepts are replaceable if better alternatives are found, but Yente 5.5.0 does not itself supply direct replacements for them.

## Executable probes

`test_chassis_bakeoff_yente_application.py` runs in a clean Yente 5.5.0 environment and tests:

1. exact dependency generation;
2. application construction without starting external services;
3. presence of match/search/health/readiness/catalog/algorithm routes;
4. native bounds for batch, matches, candidates, page and URL length;
5. default checksum-verification setting;
6. ability to add a SearchLeads FastAPI router without modifying Yente source;
7. explicit reporting of external-index and domain/auth constraints.

The additive-router probe is intentionally narrow. It proves that Yente can host additional SearchLeads HTTP surfaces without an upstream patch. It does **not** prove that SearchLeads persistence, Evidence, qualification or acquisition semantics fit cleanly inside Yente.

## Current architectural hypothesis

Three architectures remain live candidates:

### A — SearchLeads chassis

Keep current SearchLeads application/core and adopt only external algorithms/libraries that win their subsystem benchmarks.

### B — Hybrid specialized chassis

```text
SearchLeads domain/policy
    + FollowTheMoney/Nomenklatura/Rigour where they win
    + Crawlee acquisition runtime where it wins
    + a thin SearchLeads API/application layer
```

### C — Yente application chassis

```text
Yente FastAPI/search/index/operational chassis
    + newer core components if compatibility work is justified
    + SearchLeads commercial/acquisition extensions
```

A fourth possibility is also valid: use Yente as a separately deployed search/match service rather than forking it or making it the repository root. This can retain upstream upgradeability while SearchLeads owns commercial workflow and acquisition.

## Decision metrics

A full-chassis decision must include more than matching accuracy:

- code owned by SearchLeads;
- upstream code modified/forked;
- number and complexity of adapters;
- dependency divergence from upstream;
- ER precision/recall/F0.5/false-merge rate;
- request throughput and latency;
- index/storage footprint;
- recovery behavior;
- observability coverage;
- deployment components required;
- estimated infrastructure cost;
- time to add a source;
- time to add/modify a qualification policy;
- ability to preserve raw Evidence/provenance/integrity;
- ability to upgrade upstream without repeated conflict resolution.

## Adoption rule

A mature repository does not win merely because it contains more code.

Yente becomes the preferred application chassis only if the experiment shows that its ready-made operational capabilities reduce total SearchLeads-owned complexity and maintenance enough to justify its external-index footprint, older stable dependency generation, and extension work.

Conversely, SearchLeads does not win because its current domain model is ours. If Yente or another chassis can express the required product behavior more simply and more robustly, the existing design is replaceable.

## Current execution gate

GitHub-hosted jobs in this repository still terminate before the first checkout/setup step. Therefore this document distinguishes inspected upstream engineering evidence from local executed evidence. No Yente probe PASS/FAIL or cost/latency result is claimed yet.
