# Searchleads readiness observer — prospective portability protocol

Frozen before implementation. Source is the qualified NDV profile at `ed1698905f04f87c6792baf570544fe714bc059e`, identified by NDV's reuse manifest v1 at `3cd4c6bfa0a660e160d11ca9e16496d12692a878`. Target initial main: `007f13f471c2389bcd2122d10a4ff45c303a4e8f`.

## Scope and decision

REUSE the five common scripts plus the NDV profile's observer and classifier-test workflows byte-for-byte. Repository context is native and requires no target-specific classifier. The target has CI and Project 4 operational memory workflows; the NDV completed-workflow profile observes pull_request/dynamic source events through native current-head association. Unrelated project workflows and application code remain unchanged.

Authority is READ/REPORT only. Candidate reporting grants no merge, review, rerun, issue closure, release, rule change or branch deletion authority. Operator merges of the reviewed installation/evidence PRs are separately authorized. Do not activate the repository's project-closure template.

## Frozen acceptance gates

1. Record the source manifest and all seven Git blob identities; inspect the target instructions, native CI, permissions and selected profile. Missing or unreadable policy evidence is not policy PASS.
2. On the literal installation head, inspect the executed shell syntax and v1/v2/association matrix markers. Inspect all current-head application/project checks independently. Installation or workflow presence alone is not PASS.
3. Merge for activation only after the installation's applicable checks pass. If a substantive runner, credential or application gate prevents this, leave the PR pending and report the actual boundary. Do not rerun checks, disable existing checks, request paid calls or mutate repository rules to obtain PASS.
4. After activation, open a minimal documentation-only fixture without an observer comment. Record exact fixture head, implementation commit, native source run, observer run/job and actual ASSOCIATION/OBSERVATION output. Verify no readiness observer job appears in that PR's head rollup.
5. Accept only the observations actually executed. Native pending/failure/unknown stays fail-closed; a candidate requires the frozen v2 positive fields. Existing NDV/RJ results are source evidence, not target PASS. Optional uninduced review/policy states remain NOT_PROVEN.
6. Close the fixture without merge, retain its branch, and add attributable evidence. No project/release acceptance is inferred.

## Initial evidence boundary

Recent target runs had failed jobs with steps=null. This is historical infrastructure evidence, not a current run or source-code failure diagnosis. A fresh installation PR will establish the current executable gate. No secret or provider credential is required by this observer, but pre-existing workflows may have their own external prerequisites.

```text
PROTOCOL = FROZEN
IMPLEMENTATION = NOT_IMPLEMENTED at freeze
TARGET_HOSTED_MATRIX = NOT_EXECUTED
TARGET_NATIVE_AUTOMATION = NOT_PROVEN
TARGET_ACCEPTANCE = PENDING_EXECUTION
```
