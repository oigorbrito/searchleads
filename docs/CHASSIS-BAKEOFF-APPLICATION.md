# Chassis Bake-Off — Application V1

Status: `EXPERIMENTAL_PROTOCOL / NOT PRODUCTION AUTHORIZED`.

This study evaluates application-chassis alternatives without treating SearchLeads or an external repository as a protected or preferred architecture.

The canonical methodology is `EMPIRICAL-HARNESS-METHODOLOGY.md`.

## Research questions

1. Which application capabilities are present in the pinned chassis candidates?
2. Can a candidate host the required SearchLeads HTTP/application boundary without upstream source modification under the declared probe?
3. What additional infrastructure or adapters are required by each candidate?
4. Under a future controlled study, how do candidates compare on explicitly defined operational or maintenance constructs?

Capability presence, code volume, or repository maturity is not comparative production evidence.

## Isolated challenger environment

The Yente application probe pins:

```text
yente == 5.5.0
```

The Yente job remains isolated from the core bake-off because its stable dependency generation differs from the separately pinned core challenger environment. Isolation prevents dependency resolution from contaminating the comparison.

## Static capability observations

Inspection of the pinned Yente release identifies application/search capabilities such as FastAPI assembly, search/match routes, health/readiness endpoints, catalog/algorithm surfaces, index lifecycle, middleware, bounds, and observability/integrity features.

These are `STATIC_INSPECTION` observations. They establish capability presence in the inspected version only. They do not establish lower SearchLeads maintenance cost, better reliability, lower latency, or lower total infrastructure cost.

## Constraints requiring explicit treatment

### External search/index service

Normal Yente search/match operation uses an external Elasticsearch/OpenSearch service. SearchLeads' current lightweight persistence path has a different infrastructure footprint.

Any claim about total operational cost or burden must measure a declared deployment context. It must not be inferred from component count alone.

### Authentication/access control

If a candidate does not provide the SearchLeads-required authentication/access-control boundary, that remains an explicit integration requirement. Feature absence is a product-fit observation, not automatically a benchmark loss.

### Product-specific semantics

The application chassis must not silently replace or bypass SearchLeads requirements around Evidence, qualification, contact lifecycle, campaign readiness, compliance, and source/acquisition policy unless an explicit evaluated alternative replaces those requirements.

## Executable probe boundary

`test_chassis_bakeoff_yente_application.py` is a bounded functional probe. It may establish, under the declared environment, properties such as:

- dependency generation;
- application construction without starting external services;
- route presence;
- configured bounds;
- checksum-verification defaults;
- ability to mount an additive SearchLeads router without modifying upstream source;
- explicit external-index/domain/auth constraints.

The additive-router probe demonstrates only the exercised integration property. It does not establish that SearchLeads persistence, Evidence, qualification, acquisition, or compliance semantics fit cleanly inside the candidate chassis.

## Architecture hypotheses

The study may evaluate alternatives such as:

- retaining the current SearchLeads application shell;
- a thin SearchLeads-owned FastAPI shell composing selected domain/runtime components;
- Yente as a root application/search chassis;
- Yente as a separate search/match service behind a SearchLeads-owned product boundary.

These are alternatives to evaluate, not a ranking.

## Measurement discipline for future comparative claims

Different claims require different operational definitions.

Examples:

- latency/throughput: controlled comparable request workload and repeated observations;
- resource footprint: defined deployment topology plus CPU/memory/storage observations;
- recovery: fault model, recovery procedure, and observable outcome;
- infrastructure cost: declared deployment assumptions and measured/quoted resource inputs;
- change effort: predeclared comparable engineering tasks and a defensible effort measure;
- upstream divergence: explicit diff/patch/adaptation observations;
- product-fit correctness: functional acceptance cases for required SearchLeads behavior.

Do not combine these dimensions into an opaque weighted winner score.

Counts such as owned LOC, adapter count, or deployment-component count are descriptive observations. They are not maintainability or cost metrics unless the study defines and justifies that construct.

## Decision semantics

An application chassis may receive an engineering decision for product reasons, but that decision remains separate from empirical support.

Historical decisions are preserved in `APPLICATION_CHASSIS_DECISION_V1.md`. Current comparative claims require machine-readable claim files and a canonical study report referencing the preserved artifacts.

Missing required evidence becomes `INSUFFICIENT_EVIDENCE`. Unexecuted or skipped probes remain `NOT_EVALUATED` for the behaviors they did not exercise.
