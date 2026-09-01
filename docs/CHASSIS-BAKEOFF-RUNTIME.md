# Chassis Bake-Off Runtime V1

Status: `EXPERIMENTAL_PROTOCOL / NOT PRODUCTION AUTHORIZED`.

This document defines runtime/acquisition questions for the chassis bake-off. It does not make the experimental harness production authority.

Baseline: SearchLeads `gap_automation.execution`.

Challenger: `crawlee==1.9.3`.

## Research questions

The runtime probes examine bounded questions including:

1. finite retry under deterministic injected failure;
2. minimum-interval behavior after exhausted SearchLeads retries;
3. what runtime state survives a fresh SearchLeads state object;
4. request unique-key deduplication;
5. failed-request reclaim;
6. handled terminal state;
7. local request persistence across storage-client re-instantiation;
8. retry/recovery without requiring live navigation;
9. scheduling behavior under a declared synthetic workload;
10. request-level observability such as completion, retry, and duration observations;
11. separation of ordinary request retry from blocked/session recovery;
12. presence of session, proxy, timeout, statistics, robots-policy, and concurrency controls.

Each question must be interpreted according to its method. Capability inspection is not a benchmark. A functional probe is not production reliability evidence. A synthetic scheduling workload is not a production throughput claim.

## Static observations

SearchLeads currently provides product/domain runtime semantics such as:

- planner authority over allowed business actions;
- finite per-action retry metadata;
- explicit minimum interval from business planning;
- resolve/validate/reassess lifecycle hooks;
- bounded run-until-stable behavior;
- separation between acquisition success and Evidence/truth;
- action identity/disposition/attempt/reason records.

The current in-memory `GapRuntimeState` contains process-local collections for successful cache keys and last-attempt timestamps. That is a static implementation observation; a restart-persistence claim should additionally point to an executed functional probe.

Crawlee exposes request/runtime capabilities including request queues, retry/reclaim lifecycle, session management, concurrency controls, statistics, proxy configuration, timeouts, and storage backends.

Capability presence does not establish that those capabilities improve SearchLeads production outcomes.

## Candidate composition hypothesis

A historically considered architecture is:

```text
SearchLeads planner / evidence policy / lifecycle authority
                    |
                    v
          acquisition runtime adapter
                    |
                    v
request queue / retry / recovery / sessions / concurrency / stats
                    |
                    v
SearchLeads raw Evidence -> normalize -> resolve -> validate -> reassess
```

This is a design hypothesis/decision history, not a winner result.

The telemetry boundary follows the same separation conceptually:

```text
request telemetry
  -> attempts / duration / retry / status / session observations
SearchLeads business telemetry
  -> action / source / gap / Evidence / lead / cost / outcome
```

The adapter must correlate the layers without allowing request success to become domain truth.

## Evidence required by claim type

### Capability-presence claim

`STATIC_INSPECTION` may establish that an API or implementation feature exists in the inspected version.

It does not establish operational benefit.

### Functional behavior claim

A `FUNCTIONAL_PROBE` must preserve its environment and execution artifacts and may support only the tested behavior under the declared conditions.

Examples include request persistence/re-instantiation or retry/session-state behavior.

### Throughput/latency claim

A `CONTROLLED_BENCHMARK` must declare the workload, environment, repetitions or justification, raw observations, analysis, and validity limits. One synthetic timing observation must not be generalized to production.

### Production reliability/recovery claim

Requires evidence appropriate to external validity, potentially combining controlled fault injection with bounded live operational evidence. Static capability presence is insufficient.

## Invariants any challenger must preserve

- planner remains the authority for allowed actions;
- request success is not Evidence truth;
- runtime machinery cannot directly promote CandidateFact, ContactPoint, Person, Lead, qualification, or compliance state;
- retry accounting remains explicit;
- business-action throttling is not silently replaced by a non-equivalent crawler delay;
- distinct business actions are not accidentally collapsed by request deduplication.

## Decision state

No active production runtime decision is authorized by this document alone.

Historical composition decisions may be retained in `ACQUISITION_RUNTIME_DECISION_V1.md`, but current empirical support must come from a machine-readable claim bundle and canonical study report.

Missing required artifacts yield `INSUFFICIENT_EVIDENCE`; skipped or unexecuted probes yield `NOT_EVALUATED` for the behavior they did not exercise.
