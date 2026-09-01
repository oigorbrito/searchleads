# Empirical Harness Blocker Register

Status: `ACTIVE_REGISTER`

This register records blockers that affect one block of an empirical-harness closing wave without terminating the remaining independent work. A blocker is not evidence for or against a challenger and is never reclassified as PASS.

| Blocker ID | Block | State | Evidence | Impact | Independent work that remains allowed | Unblock condition |
|---|---|---|---|---|---|---|
| `HARNESS-CI-001` | GitHub-hosted verification of current head | `EXTERNAL_INFRASTRUCTURE_BLOCKER` | CI run `33519805714` and bake-off run `33519805777` on head `4d2e96ce33d2e5ccc09d7b0db040dbeed36ad92c` completed as failure with every matrix job exposing `steps: null`; no checkout/setup/test step was materialized. This reproduces the same pre-step hosted-runner failure observed on preceding heads, including runs `33518974697`/`33518974633`. | These runs cannot verify or falsify the implementation. Any newer harness-only commit remains `NOT_EVALUATED` until a runner actually executes steps. | Code review, deterministic repair from earlier actionable runs, observation-contract completion, report/claim contract work, documentation, and blocker analysis. | A current-head GitHub Actions run must expose executable steps/logs and complete the relevant jobs. |
| `HARNESS-DEP-001` | Windows installation of the FTM/Nomenklatura/Yente dependency family | `CONDITIONAL_EXTERNAL_BLOCKER` | Local dependency-enabled execution on Python 3.12 failed while building `pyicu` for `followthemoney==4.10.2`, `nomenklatura==4.14.0`, and `yente==5.5.0`. The failure was the same `RuntimeError: Please install pkg-config on your system or set the ICU_VERSION environment variable to the version of ICU you have installed.` emitted by the `pyicu` build backend, with `icu-config` / `pkg-config` unavailable on this host. | Probes that require the FTM/Nomenklatura stack or the isolated Yente environment remain `NOT_EVALUATED` on this host. Crawlee-dependent probes can still execute independently. | Crawlee adapter probes, report construction from materialized observations, regression tests, documentation, canonical report generation, claim admission for already-executed probes. | A Windows-capable environment must provide a compatible ICU/pkg-config toolchain or prebuilt wheels for `pyicu` so the pinned dependency set can install successfully. |
| `HARNESS-RUNTIME-001` | Crawlee adapter retry metadata | `FIXED_PENDING_VERIFICATION` | Earlier actionable bake-off run `33515293119` showed adapter probes reading retry metadata through unstable/internal representation: processed requests exposed `max_retries=None`, and persisted user data no longer supported direct `__crawlee` indexing. The repaired probes construct requests with `Request.from_url(max_retries=...)` and read request-specific retry configuration through `Request.crawlee_data.max_retries`. | Core runtime-adapter probes previously failed and prevented those observations from being accepted. | All non-dependent harness/report/documentation blocks. | Execute current adapter probes on Python 3.11 and 3.12 and obtain successful JUnit plus structured observations. |
| `HARNESS-EXTERNAL-DATA-001` | Pinned external canonical dataset checkout | `CONDITIONAL_EXTERNAL_BLOCKER` | Workflow checkout is pinned to `dedupeio/dedupe@3f61e79102910bd355e920a2df7e44c14c9cb247` and is collected as an explicit step outcome. | If checkout fails, experiments requiring those files are not evaluated; independent regression/probes may still execute. | SearchLeads regression and experimental blocks that do not consume that dataset, report construction from available artifacts, documentation. | Successful checkout at the pinned commit with expected sparse files available. |

## Register rules

1. Add a blocker only when a concrete block cannot be completed with currently available prerequisites.
2. Record the smallest affected block; do not label an entire wave blocked when independent blocks can continue.
3. Preserve the evidence that established the blocker: run ID, job/step, log, missing dependency, credential requirement, or unavailable service.
4. A blocker may be `FIXED_PENDING_VERIFICATION` after a local correction, but it is not `CLOSED` until the relevant verification executes.
5. External runner state, credentials, network access, or optional runtimes never authorize an architecture conclusion.
6. When a blocker closes, retain the row for auditability and change its state to `CLOSED`, adding the verification evidence.
7. Repeated pre-step runner failures with `steps: null` are one continuing infrastructure blocker, not new independent implementation failures.
8. Do not create no-op or documentation-only commits solely to provoke another runner attempt; retry only after an objective indication that the external condition changed.

## Current critical path

The current critical path for the empirical-harness reporting wave is:

`current-head executable runner -> regression/non-experimental PASS -> runtime adapter probes PASS -> structured observation bundle -> canonical study report -> bounded claims`

FTM evidence-bridge observations can be prepared independently because their research question and deterministic probe already exist, but they remain `NOT_EVALUATED` until executed in the pinned environment.

Yente application probes are not on the critical path for repairing the Crawlee adapter contract and must not prevent that repair from proceeding.
