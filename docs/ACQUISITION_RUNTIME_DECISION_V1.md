# ACQUISITION_RUNTIME_DECISION_V1

Status: `HISTORICAL_DECISION_RECORD`.

Historical decision label: `COMPOSE`.

Current empirical reading: comparative runtime superiority is `NOT_EVALUATED` unless a current canonical claim bundle supplies the preserved artifacts required by `EMPIRICAL-HARNESS-METHODOLOGY.md`.

## Scope

This record covers planner-to-network acquisition runtime only. It does not cover business qualification, entity identity, or Evidence truth promotion. SearchLeads planner policy remains the authority over what may be attempted.

## Baseline and challenger

- Baseline: `searchleads.gap_automation.execution`
- Challenger: `crawlee==1.9.3`

## Observations available from inspection and bounded probes

The bake-off identified separable runtime capabilities:

- SearchLeads retry budget is bounded by business-action metadata.
- SearchLeads `GapRuntimeState` is process-local unless state is externalized.
- Crawlee exposes request queue deduplication, reclaim/handled lifecycle, retry/session machinery, concurrency controls, statistics, and storage backends.
- SearchLeads minimum-interval semantics are business-action scoped and are not automatically equivalent to crawler-level delay semantics.
- Acquisition success must remain separate from SearchLeads Evidence and downstream truth decisions.

These observations may support capability-presence or boundary hypotheses. Static inspection alone does not establish that Crawlee improves SearchLeads throughput, reliability, recovery cost, or production outcomes.

## Historical boundary decision

The recorded engineering design was composition:

```text
SearchLeads planner
  -> SearchLeads action metadata
  -> acquisition adapter
  -> request/runtime machinery
  -> acquired response
  -> SearchLeads Evidence
  -> downstream normalization / ER / qualification
```

Under the current methodology this is a `decision_state=HISTORICAL_DECISION` with historical label `COMPOSE`, not an empirical winner declaration.

## Adapter invariants retained

Any runtime adapter must preserve the following product/integrity requirements regardless of runtime implementation:

- planner remains the authority for allowed business actions;
- request success does not become Evidence truth;
- distinct business actions are not erased by request deduplication;
- qualification does not move into the crawler/runtime layer;
- SearchLeads business throttling semantics are not silently replaced by a non-equivalent crawler delay;
- retry accounting remains explicit when baseline and challenger count attempts differently.

These are design requirements, not benchmark outcomes.

## Current claim states

| Claim | Evidence class | Current evidence state | Allowed conclusion |
|---|---|---|---|
| SearchLeads process-local runtime state is lost when a fresh in-memory state object is used | `STATIC_INSPECTION` / bounded `FUNCTIONAL_PROBE` when executed | `PARTIALLY_SUPPORTED` until the current artifact bundle is attached | behavior may be described only under the inspected/probed conditions |
| Crawlee exposes persistent queue/storage capabilities | `STATIC_INSPECTION` | `SUPPORTED` for capability presence only | capability exists; production benefit is not implied |
| Crawlee improves throughput | `CONTROLLED_BENCHMARK` required | `NOT_EVALUATED` | no comparative throughput conclusion |
| Crawlee improves recovery cost or production reliability | controlled and operational evidence required | `NOT_EVALUATED` | no production-benefit conclusion |
| Crawlee should replace the SearchLeads planner | no supporting method/evidence | `NOT_SUPPORTED` | planner replacement is not authorized by this record |

## Evidence required for an active runtime recommendation

A current active recommendation must point to reproducible artifacts covering the relevant research question. Depending on the claim, this can include:

- fault-injection observations;
- request persistence/restart observations;
- repeated latency/throughput measurements under a declared workload;
- retry/session recovery observations;
- resource and failure measurements;
- bounded live operational evidence where external validity is claimed.

The raw inputs must be preserved and referenced by a machine-readable claim. If required inputs are absent, the effective evidence state is `INSUFFICIENT_EVIDENCE`.

## Current authority

This document preserves the historical architecture decision and invariant boundary. It does not authorize production adoption based on static capability inspection.
