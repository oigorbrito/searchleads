# Bounded Gap Execution and Reassessment V1

## Work unit

`BOUNDED_GAP_EXECUTION_AND_REASSESSMENT_V1`

This work unit closes issue #73 by porting the already-tested bounded execution lifecycle from legacy PRs #23 and #30 onto the current clean stack after `DENTAL_COMMERCIAL_QUALIFICATION_V1`.

It does not change gap detection or action selection. The current planner remains the authority for which known capability is `READY` versus `BLOCKED`.

## Lifecycle

When at least one planned action succeeds, one cycle is:

```text
detect / plan
→ execute already-selected action handler
→ resolve
→ validate
→ reassess
```

The executor never creates an `ActionKind`, chooses a source, chooses an ICP, or upgrades a prerequisite acquisition into truth.

`resolve` and `validate` are explicit caller-supplied SearchLeads hooks. They run only when at least one action in the cycle returns `SUCCEEDED`. A cycle containing only blocked, missing-handler, failed, cache-hit, or scheduled work does not pretend that a new resolution/validation pass occurred.

## Execution states

Each planned action produces exactly one explicit execution record:

- `BLOCKED` — planner blocked it, required execution metadata is malformed, or no explicit handler was supplied;
- `CACHE_HIT` — the same deterministic successful cache key already completed in this runtime;
- `SCHEDULED` — the planner's minimum network interval has not elapsed;
- `SUCCEEDED` — an explicit handler completed within its bounded attempts;
- `FAILED` — the handler exhausted exactly the planner-authorized finite retry count.

No exception from a known action handler can create an unbounded retry loop.

## Current clean-stack action coverage

The executor is generic only over the finite `ActionKind` enum already owned by the clean planner. The current set is:

- `BRASILAPI_POINT_LOOKUP`
- `OFFICIAL_COMPANY_LOCATION_INGEST`
- `COMPANY_CONTACT_PAGE_INGEST`
- `PERSON_ROLE_PAGE_INGEST`
- `CONTACT_PUBLICATION_VALIDATION`
- `DENTAL_QUALIFICATION_EVALUATION`

Having an enum member does not make an action executable by itself. The caller must supply a handler for that exact action kind, and the planner must already have emitted a `READY` action.

## Retry, cache and rate-limit semantics

The executor consumes execution metadata already attached by planning:

```text
retry_max_attempts
cache_key
min_interval_seconds
```

Successful cache keys are runtime state only; they do not alter Evidence or domain truth. `last_attempt_at` is also runtime metadata and requires timezone-aware datetimes.

For network actions, the current planner provides finite retry and minimum-interval values. Local direct actions such as publication validation and dental qualification retain their planner-defined single-attempt / zero-interval behavior.

## Bounded run-until-stable

`run_gap_automation_until_stable(...)` is synchronous and finite. It stops with one of:

- `NO_GAPS`
- `GAPS_RESOLVED`
- `NO_PROGRESS_OR_SCHEDULED`
- `MAX_CYCLES_REACHED`

There is no daemon, background worker, cron scheduler, queue consumer, arbitrary DAG engine, or dynamic provider discovery.

## Qualification boundary

`DENTAL_QUALIFICATION_EVALUATION` can execute only when the clean planner already emitted it. The planner requires an explicit Person ID plus the approved dental policy ID. This executor does not select or infer either value and does not equate a qualified Lead with CFO-active, compliance-approved, deliverable, or `SEND_READY`.

## Verification

Focused deterministic executor suite:

```text
TESTS = 18/18 PASS
LINE_COVERAGE = 100%
BRANCH_COVERAGE = 100%
STATEMENTS = 111
BRANCHES = 30
```

Covered cases include:

- timezone-aware clock enforcement;
- blocked actions;
- malformed READY metadata defense;
- bounded retry success and failure;
- successful-result cache reuse;
- minimum-interval scheduling and elapsed-interval execution;
- missing explicit handler;
- lifecycle hook ordering and skip behavior;
- all current clean `ActionKind` values through explicit handlers;
- all four finite run stop reasons.

These are execution-contract tests, not live network-source success rates or production throughput measurements.

## Gates

```text
PLANNER_REMAINS_ACTION_AUTHORITY = YES
DYNAMIC_SOURCE_SELECTION = NO
FINITE_RETRY = PASS
SUCCESS_CACHE = PASS
MIN_INTERVAL_SCHEDULING = PASS
EXPLICIT_HANDLER_REQUIRED = YES
DETECT_ENRICH_RESOLVE_VALIDATE_REASSESS = PASS
HOOKS_WITHOUT_SUCCESS = NO
RUN_UNTIL_STABLE_BOUNDED = YES
BACKGROUND_SCHEDULER = NO
GENERIC_WORKFLOW_ENGINE = NO
LIVE_HTTP_CERTIFIED = NO
CFO_STATUS_MUTATED = NO
COMPLIANCE_STATUS_MUTATED = NO
SEND_READY_MUTATED = NO
```

## Documentation/test basis

- current `docs/GAP-DETECTION-AND-AUTOMATION.md`
- legacy PR #23 bounded executor
- legacy PR #30 lifecycle correction
- issue #73
