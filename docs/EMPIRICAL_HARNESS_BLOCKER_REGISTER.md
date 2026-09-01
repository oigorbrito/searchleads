# Empirical Harness Blocker Register

Status: `ACTIVE_REGISTER`

This register records blockers that affect one block of an empirical-harness closing wave without terminating the remaining independent work. A blocker is not evidence for or against a challenger and is never reclassified as PASS.

| Blocker ID | Block | State | Evidence | Impact | Independent work that remains allowed | Unblock condition |
|---|---|---|---|---|---|---|
| `HARNESS-CI-001` | GitHub-hosted verification of current head | `EXTERNAL_INFRASTRUCTURE_BLOCKER` | On head `2cad405972bd6aace96280a0c54661313337cb8f`, CI run `33518528677` and bake-off run `33518528553` completed as failure with job payloads exposing `steps: null`, so no executable step-level failure is available from those runs. | Those runs cannot verify or falsify the current implementation. | Code review, deterministic test repair from earlier actionable runs, documentation, observation contracts, report contracts, and blocker analysis. | A current-head GitHub Actions run must expose executable steps/logs and complete the relevant jobs. |
| `HARNESS-RUNTIME-001` | Crawlee adapter retry metadata | `FIXED_PENDING_VERIFICATION` | Earlier actionable bake-off run `33515293119` showed adapter probes reading retry metadata through unstable/internal representation: processed requests exposed `max_retries=None`, and persisted user data no longer supported direct `__crawlee` indexing. Crawlee 1.9 public API exposes retry configuration through `Request.crawlee_data.max_retries`. | Core runtime-adapter probes previously failed and prevented those observations from being accepted. | All non-dependent harness/report/documentation blocks. | Execute current adapter probes on Python 3.11 and 3.12 and obtain successful JUnit plus structured observations. |
| `HARNESS-EXTERNAL-DATA-001` | Pinned external canonical dataset checkout | `CONDITIONAL_EXTERNAL_BLOCKER` | Workflow checkout is pinned to `dedupeio/dedupe@3f61e79102910bd355e920a2df7e44c14c9cb247` and is collected as an explicit step outcome. | If checkout fails, experiments requiring those files are not evaluated; independent regression/probes may still execute. | SearchLeads regression and experimental blocks that do not consume that dataset, report construction from available artifacts, documentation. | Successful checkout at the pinned commit with expected sparse files available. |

## Register rules

1. Add a blocker only when a concrete block cannot be completed with currently available prerequisites.
2. Record the smallest affected block; do not label an entire wave blocked when independent blocks can continue.
3. Preserve the evidence that established the blocker: run ID, job/step, log, missing dependency, credential requirement, or unavailable service.
4. A blocker may be `FIXED_PENDING_VERIFICATION` after a local correction, but it is not `CLOSED` until the relevant verification executes.
5. External runner state, credentials, network access, or optional runtimes never authorize an architecture conclusion.
6. When a blocker closes, retain the row for auditability and change its state to `CLOSED`, adding the verification evidence.

## Current critical path

The current critical path for the empirical-harness reporting wave is:

`current-head executable runner -> regression/non-experimental PASS -> runtime adapter probes PASS -> structured observation bundle -> canonical study report -> bounded claims`

Yente application probes are not on this critical path for repairing the Crawlee adapter contract and must not prevent that repair from proceeding.
