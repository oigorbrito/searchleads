# Searchleads readiness — executed portability evidence

## Classification

```text
SOURCE_REUSE = IMPLEMENTED / TWO_RECORDED_TARGET_ADAPTATIONS
TARGET_CLASSIFIER_AND_ASSOCIATION_MATRIX = EXECUTED_PASS / SYNTHETIC
TARGET_APPLICATION_CI = EXECUTED_SUCCESS / EXPLICIT_SKIPS_AND_XPASS_RETAINED
NATIVE_AUTOMATIC_HEAD_ASSOCIATION = EXECUTED_PASS
NATIVE_PENDING_EXCLUSION = EXECUTED_PASS
NATIVE_PENDING_TO_CLEAN_CANDIDATE = EXECUTED_PASS / SAME_RECORDED_HEAD
READINESS_SELF_INTERFERENCE_EXCLUSION = EXECUTED_PASS
PORTABILITY_ACCEPTANCE = ACCEPTED / AUTOMATIC_READ_REPORT_RECORDED_SCOPE
PROJECT4_INTEGRATION = RETIRED / NOT_EXECUTED_AFTER_RETIREMENT
PROJECT_OR_RELEASE_ACCEPTANCE = NOT_CLAIMED
```

Installation, successful checkout, merge, skipped tests and historical NDV/RJ claims did not establish this acceptance. Exact executed observations and inspected checks did.

## Frozen provenance and adaptations

Target initial main `007f13f471c2389bcd2122d10a4ff45c303a4e8f`; source NDV profile `ed1698905f04f87c6792baf570544fe714bc059e`, manifest v1 at NDV `3cd4c6bfa0a660e160d11ca9e16496d12692a878`.

Original protocol freeze `c2b57fc29e002bb5b8ff213fdd89f0bc978e2288` preceded byte-identical initial head `53a77324701ae72b1ddbb33e02e7a916c96a2e5c`. Initial classifier execution and application merge-ref/tree-equivalence evidence remain in the additive lint document and PR #155 history.

- Lint freeze `62be3b5e927721f6087a57ea69ca21b2f999c583`: rename three discarded local bindings in the response helper, preserving extraction order and decision semantics. Adapted v2 classifier blob `b1139508a580b17f0cda18fbbb64291357aaa8de`. Original Codacy warning and native annotation retrieval run `37525129570` / job `112480075957` are preserved. Temporary diagnostic workflow removed.
- Owner-delegated retirement freeze `e84911b43fe71bc1fcf5c43e46f354a345a6b7a0`: remove unrelated Project4 auto-sync instead of requiring a PAT for this installation. Original workflow remains in Git history; board/items/secrets/branches untouched. Earlier missing-token failures remain FAILURE, not PASS.
- Bounded-reread transport v1 freeze: preceding protocol commit in PR #157, before implementation `38e054854cc33b8ed842572b1664e7b86fa1764c`. Retry only automatic v2 NOT_READY_CHECKS/PENDING; initial query plus at most six additional native queries, fixed ten-second waits, source-head recheck every time. No budget tuning.

Five of the seven installed source files remain byte-identical. The v2 helper local names and observer transport are the two recorded target adaptations. Neither the native field ensemble nor classifier decision protocol changed. No policy engine, LLM inference or external service was added.

## Installation and activation

PR #155 final head `c4f246415865a634eff14f7f65d72c09d5b945f2` passed all five applicable checks before operator merge `c61a121cdae7dffd08c05d6614e0ed9a641202a9`.

Classifier run `37526618538`, job `112485127900`, recorded literal TESTED_HEAD and CLASSIFIER_MATRIX=PASS, CLASSIFIER_V2_MATRIX=PASS, RUN_ASSOCIATION_MATRIX=PASS. Application run `37526618595`, Python3.11/3.12/3.13 jobs `112485128579`/`112485127963`/`112485128223`, actually executed with each full suite 944 passed,24 skipped,1 xpassed. App checkout was merge ref `1959aa1fe08b4ce4aa48cb1adc00c0dba68154cd`, not literal application-head checkout. Codacy check `112485358707` succeeded. Application CI file was unchanged; retired Project4 workflow/check was absent, recorded as retirement rather than success.

PR #157 exact head `38e054854cc33b8ed842572b1664e7b86fa1764c` passed five applicable checks before operator activation `b425caba891bc11b21f3736f2ee221f08a183cb7`. Classifier run `37527196090`, job `112487077001`, recorded that TESTED_HEAD and all three matrices PASS. App run `37527196135`, jobs `112487076707`/`112487076886`/`112487076919`, each recorded 944 passed,24 skipped,1 xpassed. Codacy check `112487504869` succeeded. Existing classifier bytes were unchanged by this transport edit.

## Native fixture and initial timing limitation

Fixture #156 initial head `049bb9d3f86a0de11e4da368d6e7c0ab734e5067`, implementation `c61a121cdae7dffd08c05d6614e0ed9a641202a9`. Observer run `37526873952` / job `112486003917` followed CI source `37526823824`; observer run `37526849808` / job `112485932184` followed classifier source `37526823812`.

Both actual observations were OPEN/non-draft/UNSTABLE/MERGEABLE/NONE/PENDING -> NOT_READY_CHECKS v2. Later successful Codacy check `112486358121` did not provide another workflow_run source. This established the target-specific timing limitation; initial automatic positive readiness remains NOT_PROVEN on that exact head.

## One prospective fixture refresh — native pending to candidate

After transport activation, the existing documentation fixture was refreshed once, producing exact head `8091a0a19c6f0d51708c662e04b83723335a1e44`. No observer command was posted. The comment list contained one bot comment and zero readiness commands.

Classifier source run `37527458397`, job `112487974907`, recorded literal fixture TESTED_HEAD and all three matrices PASS. CI source run `37527458484`, jobs `112487975674` (3.11), `112487976270` (3.12), `112487975411` (3.13), each executed 944 passed,24 skipped,1 xpassed. Actual app checkout was merge ref `2f8a8c2` merging the fixture with activated main; do not call it literal head checkout. Native Codacy check `112488262222` later completed SUCCESS.

Both observers checked out implementation `b425caba891bc11b21f3736f2ee221f08a183cb7` from the default branch and executed checkout, native association, repeated query and report-only assertion.

| Source | Observer run | Job | Native attempts |
| --- | --- | --- | --- |
| classifier37527458397 | 37527481317 | 112488054628 | 0–2 PENDING/NOT_READY_CHECKS; 3 SUCCESS/READY_FOR_MERGE_CANDIDATE |
| CI37527458484 | 37527505845 | 112488141811 | 0–1 PENDING/NOT_READY_CHECKS; 2 SUCCESS/READY_FOR_MERGE_CANDIDATE |

Actual final native lines:

```text
ASSOCIATION source_run=37527458397 source_head=8091a0a19c6f0d51708c662e04b83723335a1e44 pr=156
OBSERVATION state=OPEN draft=false mergeStateStatus=CLEAN mergeable=MERGEABLE reviewDecision=NONE checks=SUCCESS base=main head=readiness-fixture/automatic-searchleads head_sha=8091a0a19c6f0d51708c662e04b83723335a1e44 decision=READY_FOR_MERGE_CANDIDATE protocol=v2 attempt=3
ASSOCIATION source_run=37527458484 source_head=8091a0a19c6f0d51708c662e04b83723335a1e44 pr=156
OBSERVATION state=OPEN draft=false mergeStateStatus=CLEAN mergeable=MERGEABLE reviewDecision=NONE checks=SUCCESS base=main head=readiness-fixture/automatic-searchleads head_sha=8091a0a19c6f0d51708c662e04b83723335a1e44 decision=READY_FOR_MERGE_CANDIDATE protocol=v2 attempt=2
```

The preceding attempt lines preserve actual UNSTABLE/MERGEABLE/NONE/PENDING fields on this same head. The measured transport stopped once native checks settled within its frozen budget. These two source events made seven readiness queries and two association queries, with fifty seconds aggregate configured sleep plus API/job execution time; cost is not zero.

Five fixture-head checks completed SUCCESS: classifier, three application jobs and Codacy. Readiness observer jobs `112488054628` and `112488141811` were absent from that head's check rollup. No stale or different head supplied this positive candidate.

## Cleanup and acceptance boundary

Fixture #156 was closed without merge at `2026-10-06T20:35:55Z`; current and historical fixture heads and branch retained. No second refresh, observer command, check rerun, artificial check, review, rule mutation, provider call or branch deletion occurred. No issue was closed.

The prospective gates passed for installation, exact-head synthetic execution, applicable CI, automatic native current-head association, pending exclusion, same-head settled positive ensemble, no self-interference and cleanup. Accept observer portability and bounded transport only within these executed automatic READ/REPORT scopes.

Native budget exhaustion, head changes during reread, API errors, draft, conflict and optional policy/review states were not induced on this target; they retain inspected implementation and existing separately attributed synthetic/source coverage, not new native PASS. A transient UNKNOWN stops fail-closed and does not trigger additional budget. Checks completing after the fixed budget are not guaranteed a new automatic settled observation; there is no unbounded watcher.

No project/release quality acceptance or ability to merge is delegated to the observer. Historical source outcomes remain historical; the retired integration is not qualified.
