# Chassis Bake-Off Runtime V1

## Scope

This document records the runtime/acquisition portion of PR #113. It is an experiment, not a production dependency decision.

The baseline is SearchLeads `gap_automation.execution`. The challenger is `crawlee==1.9.3`, the stable PyPI release published 2026-08-24.

No SearchLeads concept is protected merely because it already exists. A SearchLeads-specific business/evidence invariant may remain while its runtime implementation is replaced.

## Tested questions

The executable probes in `tests/experimental/test_chassis_bakeoff_runtime*.py` test:

1. finite retry under deterministic injected failure;
2. minimum-interval behavior after exhausted SearchLeads retries;
3. what SearchLeads runtime state survives a fresh `GapRuntimeState`;
4. Crawlee request `unique_key` deduplication;
5. Crawlee failed-request reclaim;
6. Crawlee handled terminal state;
7. Crawlee filesystem request persistence across storage-client re-instantiation;
8. Crawlee request retry/recovery without network navigation;
9. synthetic scheduling concurrency under identical 20 ms per-item work;
10. presence of session rotation, blocking retry, proxy, statistics, timeout, robots policy and concurrency controls.

## Current static findings

### SearchLeads strengths retained as hypotheses

- planner remains the authority for which business action is allowed;
- finite per-action retry metadata;
- explicit minimum interval from the business planner;
- explicit `resolve -> validate -> reassess` hooks;
- bounded run-until-stable semantics;
- evidence/truth boundaries remain separate from acquisition success.

These are product/domain semantics, not reasons to retain the current runtime implementation.

### SearchLeads runtime limitations exposed by code and probes

`GapRuntimeState` contains only:

- `successful_cache_keys`;
- `last_attempt_at`.

Both are in-memory Python collections. A fresh runtime therefore loses the successful-action cache and the previous attempt timestamp. There is no native request queue, reclaim state, session rotation, adaptive concurrency, crawler statistics, proxy runtime or durable local request lifecycle in this executor.

### Crawlee capabilities under test

Crawlee 1.9.3 provides a request queue with unique-key deduplication, explicit pending/in-progress/handled lifecycle and reclaim; `BasicCrawler` provides retries, session management/rotation, concurrency controls, statistics, proxy configuration, handler timeouts and blocked-request policy. Its filesystem storage client explicitly persists local storage between program runs, while warning that the filesystem backend is not multi-process safe.

## Decision boundary

The likely architecture, if the probes confirm the static findings, is **not** to replace SearchLeads with a generic crawler.

The candidate design is a hybrid:

```text
SearchLeads planner / evidence policy / lifecycle authority
                    |
                    v
          acquisition runtime adapter
                    |
                    v
Crawlee request queue / retry / recovery / sessions / concurrency / stats
                    |
                    v
SearchLeads raw Evidence -> normalize -> resolve -> validate -> reassess
```

This is only a candidate until tests execute.

## Required evidence before adoption

Do not adopt Crawlee as a production dependency until all of the following have executed successfully:

- full SearchLeads regression suite with the challenger installed only in the experimental workflow;
- runtime fault-injection probes;
- request persistence probe;
- concurrency probe;
- existing entity-resolution and statement/evidence chassis probes;
- at least one bounded live-source experiment after issue #60 is ready for live HTTP certification.

Any production adapter must preserve the rule that request success is not evidence truth and cannot directly promote a CandidateFact, ContactPoint, Person, Lead or qualification/compliance state.

## Current execution gate

As of 2026-08-30, GitHub-hosted jobs for this repository repeatedly terminate before checkout/setup with no job steps. This is recorded as a runner/provisioning gate. It is not reported as pytest failure or success.
