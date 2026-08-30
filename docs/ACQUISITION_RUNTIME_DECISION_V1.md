# ACQUISITION_RUNTIME_DECISION_V1

Status: `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT`; GitHub Actions is still infrastructure-blocked, so the runtime comparison is not yet executed as an end-to-end benchmark.

## Scope

This decision covers planner-to-network acquisition runtime only.

It does not cover business qualification, entity identity, or evidence truth promotion. SearchLeads planner policy remains the authority over what may be attempted.

## Baseline and challenger

- Baseline: `searchleads.gap_automation.execution`
- Challenger: `crawlee==1.9.3`

The goal is not to replace product policy with a crawler. The goal is to use the best runtime boundary for request queueing, retry, reclaim, session handling, concurrency, and persistence.

## Static evidence from the harness

The current probes already show the relevant semantic split:

- SearchLeads retry budget is bounded by business action metadata.
- SearchLeads `GapRuntimeState` is process-local and loses state on restart.
- Crawlee request queues dedupe by unique key.
- Crawlee request queues support reclaim and handled terminal state.
- Crawlee filesystem storage survives storage-client reinstantiation.
- Crawlee `BasicCrawler` retries handler failures.
- Crawlee session rotation is distinct from ordinary retry.
- Crawlee throttling is domain-scoped, while SearchLeads min-interval is per action/cache key.

That is enough to decide the architecture boundary, even though it is not enough to claim a performance winner.

## Decision matrix

| Capability | Current SearchLeads | Crawlee | Decision |
|---|---|---|---|
| Business action authority | planner owns it | not native | `KEEP` |
| Per-action retry metadata | native | can carry metadata | `KEEP` |
| Request dedupe | absent | native unique-key queue | `REPLACE` |
| Failed-request reclaim | absent | native | `REPLACE` |
| Durable local request queue | absent | filesystem backend | `REPLACE` |
| Session rotation / blocked-session handling | absent | native | `REPLACE` |
| Adaptive concurrency / stats / telemetry | thin or absent | native | `REPLACE` |
| Min-interval by action/cache key | native | not native and not domain-equivalent | `KEEP` |
| Evidence truth boundary | native | must stay outside runtime | `KEEP` |

## Boundary decision

The correct architecture is composition:

```text
SearchLeads planner
  -> SearchLeads action metadata
  -> acquisition adapter
  -> Crawlee Request / RequestQueue / crawler runtime
  -> acquired response
  -> SearchLeads Evidence
  -> downstream normalization / ER / qualification
```

Why this wins structurally:

- SearchLeads must keep ownership of policy, Evidence, and qualification.
- Crawlee is better at runtime mechanics that are not domain logic.
- SearchLeads min-interval and Crawlee crawl-delay are not semantically identical, so they should not be collapsed into one abstraction.
- A fresh process must not lose queue state if recovery matters.

This is a `COMPOSE` decision.

## What the adapter must do

The adapter boundary should:

- translate SearchLeads action identity into Crawlee request metadata;
- preserve SearchLeads cache keys as request unique keys where appropriate;
- keep min-interval and business policy in SearchLeads metadata, not in Crawlee domain logic;
- map retry counts carefully because SearchLeads counts total attempts while Crawlee counts retries after the first attempt;
- keep Evidence capture outside the crawler's success semantics.

## What the adapter must not do

- It must not let crawler success become entity truth.
- It must not let request dedupe erase distinct business actions.
- It must not move qualification into the crawler.
- It must not collapse domain throttling into domain-level crawl delay.

## Claims table

| Claim | Evidence available | Execution required? | Decision possible now? | Confidence |
|---|---|---|---|---|
| SearchLeads runtime loses state on restart | static code/probe inspection | no | yes | high |
| Crawlee is a better request/runtime boundary | static capability inspection + probe design | no | yes | medium |
| Crawlee beats SearchLeads on throughput/recovery cost | benchmark only | yes | no | low |
| Crawlee should replace SearchLeads planner | no evidence | yes | no | low |

## Current decision

`Acquisition runtime` = `COMPOSE`

## Implication for implementation

The eventual implementation should not rewrite SearchLeads business semantics inside the crawler.

Instead, it should add a thin runtime adapter and let Crawlee own the operational request machinery. The product policy remains SearchLeads-owned.
