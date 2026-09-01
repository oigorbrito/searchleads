# Empirical Harness Blocker Register

Status: `ACTIVE_REGISTER`

This register records blockers that affect one block of an empirical-harness closing wave without terminating the remaining independent work. A blocker is not evidence for or against a challenger and is never reclassified as PASS.

| Blocker ID | Block | State | Evidence | Impact | Independent work that remains allowed | Unblock condition |
|---|---|---|---|---|---|---|
| `HARNESS-CI-001` | GitHub-hosted verification of current head | `EXTERNAL_INFRASTRUCTURE_BLOCKER` | The pre-step hosted-runner failure continues on current head `6f4af641153ad9355fccd9349eb21e2d3731bbf4`: CI `#595` / run `33524932311` and Bake-Off `#311` / run `33524932341` completed as failure with every matrix job exposing `steps: null`. The same condition was previously observed on CI `#592` / `33523136213`, Bake-Off `#308` / `33523136133`, and preceding heads. | These hosted runs cannot verify or falsify the implementation because no checkout/setup/test step materialized. | Local dependency-capable execution, structured observation validation, canonical report generation, bounded claim analysis, documentation, and blocker analysis. | A current-head GitHub Actions run must expose executable steps/logs and complete the relevant jobs. |
| `HARNESS-DEP-001` | Windows installation of the FTM/Nomenklatura/Yente dependency family | `CONDITIONAL_EXTERNAL_BLOCKER` | Local dependency-enabled execution on Python 3.12 failed while building `pyicu` for `followthemoney==4.10.2`, `nomenklatura==4.14.0`, and `yente==5.5.0`. The failure was `RuntimeError: Please install pkg-config on your system or set the ICU_VERSION environment variable to the version of ICU you have installed.`, with `icu-config` / `pkg-config` unavailable on this host. | Probes requiring the FTM/Nomenklatura stack or isolated Yente environment remain `NOT_EVALUATED` on this host. Crawlee-dependent probes executed independently. | Crawlee functional probes and bounded claims, report construction from materialized observations, regression tests, documentation, and canonical report generation. | A compatible environment must provide ICU/pkg-config metadata or a compatible prebuilt `pyicu` wheel so the pinned dependency set can install and the affected probes can execute. |
| `HARNESS-RUNTIME-001` | Crawlee adapter retry metadata | `FIXED_PENDING_CROSS_VERSION_VERIFICATION` | Earlier bake-off run `33515293119` exposed the unstable retry-metadata access. The repaired probes use `Request.from_url(max_retries=...)` and `Request.crawlee_data.max_retries`. On local Python `3.12.10` with `crawlee==1.9.3`, the focused adapter suite completed `3 passed, 0 failed, 0 errors, 0 skipped` and materialized `runtime-adapter-roundtrip-v1`, `runtime-adapter-boundary-v1`, and `runtime-adapter-persistence-v1`. The corresponding narrow roundtrip and filesystem-persistence claims are now traceable and `SUPPORTED` with `decision_state: DEFER`. Python 3.11 was unavailable on that host. | The previous functional failure is closed for the exercised Python 3.12 environment, but the workflow's intended 3.11/3.12 cross-version verification remains incomplete. | Canonical report generation, bounded Crawlee claims, non-dependent experiments, documentation, and blocker analysis. | Execute the repaired adapter probes successfully on Python 3.11 with structured observations; retain the already-successful Python 3.12 evidence. |
| `HARNESS-EXTERNAL-DATA-001` | Pinned external canonical dataset checkout | `CONDITIONAL_EXTERNAL_BLOCKER` | Workflow checkout is pinned to `dedupeio/dedupe@3f61e79102910bd355e920a2df7e44c14c9cb247` and is collected as an explicit step outcome. | If checkout fails, experiments requiring those files are not evaluated; independent regression/probes may still execute. | SearchLeads regression and experimental blocks that do not consume that dataset, report construction from available artifacts, documentation. | Successful checkout at the pinned commit with expected sparse files available. |
| `HARNESS-PR-001` | PR branch/metadata synchronization | `CLOSED` | GitHub branch metadata and PR #116 now both report head `6f4af641153ad9355fccd9349eb21e2d3731bbf4`. | No remaining synchronization impact. | All work allowed subject to the other blockers. | Closed; reopen only if the branch ref and PR head diverge again. |

## Register rules

1. Add a blocker only when a concrete block cannot be completed with currently available prerequisites.
2. Record the smallest affected block; do not label an entire wave blocked when independent blocks can continue.
3. Preserve the evidence that established the blocker: run ID, job/step, log, missing dependency, credential requirement, or unavailable service.
4. A blocker may be pending verification after a local correction, but it is not fully closed until its declared verification scope executes.
5. External runner state, credentials, network access, or optional runtimes never authorize an architecture conclusion.
6. When a blocker closes, retain the row for auditability and change its state to `CLOSED`, adding the verification evidence.
7. Repeated pre-step runner failures with `steps: null` are one continuing infrastructure blocker, not new independent implementation failures.
8. Do not create no-op or documentation-only commits solely to provoke another runner attempt; retry only after an objective indication that the external condition changed.

## Current critical path

The critical path has narrowed after successful local Crawlee execution:

`Python 3.11 adapter execution -> cross-version adapter verification closure`

and independently:

`ICU/pkg-config-capable environment -> FTM/Nomenklatura/Yente execution -> structured observation bundle -> bounded claim admission`

GitHub-hosted execution remains a separate external infrastructure blocker and does not invalidate the locally materialized Python 3.12 Crawlee observations or their bounded claims. No architecture, production, or superiority decision follows from those claims.
