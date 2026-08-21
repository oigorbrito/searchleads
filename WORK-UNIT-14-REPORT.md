# Work Unit 14 Report — GAP_DETECTION_AND_AUTOMATION_V1

## Scope

Implements the handoff's bounded loop over already-known SearchLeads capabilities:

```text
company
→ detect missing information
→ select known source/capability
→ execute enrichment/action
→ resolve/validate in the source-specific handler
→ reassess gaps
```

Requirements remain explicit caller inputs. The system does not silently decide that a business field is required and does not create a generic crawler, daemon, or universal workflow engine.

## Known action mapping

Missing canonical registry fields already covered by the structured CNPJ adapter map to `BRASILAPI_LOOKUP`.

Missing `street_address`, `postal_code`, or `activity_start_date` map to the known official-location enrichment capability.

Missing validated company contact maps to the known official contact discovery/corroboration capability.

Missing person/company role maps to the known official people-page capability.

Missing qualification maps to qualification evaluation only when an explicit policy ID exists.

An unknown requested field remains `BLOCKED`; no new source is invented.

## Planning semantics

Ready network actions carry:

- finite `retry_max_attempts`;
- deterministic cache key;
- minimum interval metadata.

Blocked actions carry no network action and do not retry blindly.

## Execution semantics

`gap_execution.py` adds a synchronous bounded executor for actions that have already been selected by `gap_automation.py`.

Per action it supports:

- explicit handler lookup by existing `ActionKind`;
- finite retry only up to `retry_max_attempts`;
- successful-result cache key reuse;
- rate-limit enforcement from `min_interval_seconds`;
- `SCHEDULED` disposition with explicit `next_eligible_at` when the minimum interval has not elapsed;
- final `FAILED` record with the next eligible time after bounded retries;
- `BLOCKED` when no explicit handler exists.

The executor does not dynamically discover arbitrary functions or sources.

## Reassessment loop

`run_gap_automation_until_stable()` performs a bounded synchronous loop:

```text
plan gaps
→ execute ready known actions
→ source handlers persist/enrich through existing capabilities
→ rebuild plan from resulting state
→ stop when gaps resolve, progress stops/scheduling is required, or max_cycles is reached
```

This closes the original handoff requirements `run enrichment`, `retry`, `cache`, `rate limit`, `schedule`, and `reassess` without introducing a background scheduler.

## Validation

Original planning implementation baseline:

```text
TESTS_DISCOVERED = 156
TESTS_EXECUTED = 156
TESTS_PASSED = 156
```

Audit-correction isolated execution suite:

```text
GAP_EXECUTION_TESTS = 9/9 PASS
```

The isolated suite covers success/cache reuse, bounded retries, explicit schedule time under rate limiting, blocked actions, missing handlers, post-handler reassessment, run-until-stable resolution, no-progress termination, and timezone-aware scheduling.

A new whole-repository regression on the final stacked audit-correction head is still required before declaring regression validation complete; the execution environment cannot clone the private GitHub repository because outbound DNS is unavailable.

## Gates

```text
GAP_DETECTION = PASS
EXPLICIT_REQUIREMENTS = PASS
KNOWN_SOURCE_SELECTION = PASS
UNKNOWN_SOURCE_NOT_INVENTED = PASS
RUN_ENRICHMENT = PASS (bounded explicit handlers)
BOUNDED_RETRY = PASS
CACHE = PASS
RATE_LIMIT = PASS
SCHEDULE = PASS (explicit next_eligible_at; no daemon)
REASSESS = PASS
QUALIFICATION_WITHOUT_ICP = BLOCKED
GENERIC_SCHEDULER = NO
UNIVERSAL_FRAMEWORK = NO
FULL_REGRESSION_ON_FINAL_HEAD = PENDING
```

## Classification

### EVIDENCE_BACKED

- unknown gaps do not imply invented data sources;
- qualification remains blocked without policy/ICP.

### ENGINEERING_CHOICE

- synchronous bounded execution instead of a background scheduler;
- explicit handler map keyed only by known `ActionKind`;
- cached successful action keys;
- finite `max_cycles` stop boundary;
- `next_eligible_at` as scheduling representation.

### LOCALLY_VERIFIED

- original WU14 planning tests passed 156/156 on its branch;
- audit-correction execution contract passes 9/9 isolated tests.

### UNKNOWN

- production retry timing/backoff policy;
- production scheduler/storage technology;
- production source quotas and rate limits;
- full regression status of the latest stacked head until the complete suite can run there.
