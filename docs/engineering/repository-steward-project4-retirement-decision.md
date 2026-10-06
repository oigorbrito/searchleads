# Searchleads — retirement of legacy Project4 integration

## Owner-delegated operational decision

After the owner was offered credential setup or changing the existing Project4 integration, the owner delegated the easier option on 2026-10-06. Retire the unrelated automatic Project4 sync workflow rather than introduce a PAT requirement into the readiness installation.

This is an additive operational decision frozen before removal. It supersedes the original portability gate's requirement to keep that specific unrelated project integration active and passing. It does not change application CI, Codacy, the classifier, repository rules or the READ/REPORT authority boundary.

## Scope

Remove only `.github/workflows/project4-auto-add.yml` from active workflows. Its original Git blob `36a9fb8ff02f986b81216e65e325019ce16910db` remains recoverable at commit `ac96c05b87c925d2e362cf5877e97162ceb07a68` and earlier history. Do not delete the Project4 board, items, secrets or branches. Do not substitute another token/account or create a new project integration.

Issue/PR events will no longer automatically add or change Project4 items after this retirement reaches the default branch. Readiness reporting remains automatic and does not depend on Project4 credentials. This is not a Project4 integration PASS; future reactivation requires a separate explicit scope and credential/access verification.

## Prospective acceptance gate

1. Verify the removal is the only active workflow change beyond the already identified readiness installation and lint adaptation.
2. On the final literal installation head, inspect executed classifier/association matrices, unchanged application CI on Python3.11–3.13, Codacy and all applicable current-head checks.
3. Verify the retired integration is absent from active workflows and native current-head checks; record it as RETIRED / NOT_EXECUTED, never SUCCESS.
4. After those checks pass, operator merge may activate the observer. Then execute the previously frozen automatic native documentation-fixture gate, record exact run/job/head and clean up without merge.
5. Keep historical Project4 failures and unavailable credentials attributable to their original runs. No previous FAIL is reclassified.

## Preserved preceding evidence

On head `ac96c05b87c925d2e362cf5877e97162ceb07a68`:
- Classifier run37525328661/job112480751273: literal TESTED_HEAD and all three matrix markers PASS.
- Application run37525328623: jobs112480752351/112480752115/112480752598 passed; each full suite944 passed/24 skipped/1 xpassed, focused91/31 passed. Merge-ref1d2a12f16c6ae7fca68bc37201c353fc16679ae1 tree8aeec090d52e2960d715686fa030b855c82d4bbb equals literal-head tree.
- Codacy check112481726952: completed/success.
- Project4 run37525328645/job112480751454: missing GH_TOKEN diagnostic and exit4; remains FAILURE.
- Temporary annotation diagnostic workflow was removed; source semantics were preserved by the documented local-name lint adaptation.

These historical successful checks do not establish execution on the retirement head. No target native observer PASS is claimed before activation and fixture execution.
