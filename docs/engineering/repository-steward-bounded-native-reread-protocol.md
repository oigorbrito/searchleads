# Searchleads automatic readiness — bounded native reread v1

## Prospective transport gate

Freeze before implementation. Active observer/classifier implementation `c61a121cdae7dffd08c05d6614e0ed9a641202a9`. Frozen v2 decision semantics remain unchanged.

Fixture #156 head `049bb9d3f86a0de11e4da368d6e7c0ab734e5067` had successful app/classifier CI while Codacy was still pending. Automatic native source association executed twice:
- CI source37526823824 -> observer37526873952/job112486003917.
- Classifier source37526823812 -> observer37526849808/job112485932184.
Both recorded OPEN/non-draft/UNSTABLE/MERGEABLE/NONE/PENDING -> NOT_READY_CHECKS v2. Codacy check112486358121 subsequently succeeded without another workflow_run source event. These pending observations are PASS for fail-closed snapshots, not automatic positive readiness.

GitHub's documented check_run/check_suite recursion restrictions make those events unsuitable as an assumed guaranteed completion source for an Actions-associated head. Use the smallest ADAPT of the already qualified wrapper: bounded native rereads, no separate engine/service or policy reconstruction.

## Frozen stopping rule and cost

For automatic workflow_run v2 observation only: initial query plus at most six additional queries, ten seconds between retries (at most sixty seconds sleep, plus API/runner execution time). Retry only when the unchanged classifier returns NOT_READY_CHECKS and its native rollup is PENDING. The subsequent query must still match the exact source head.

Stop immediately on a different head, extraction/error/unknown, draft/closed, conflict/policy exclusion, or a settled rollup. Preserve every actual OBSERVATION with attempt index; report the last executed result. Exhausted pending remains NOT_READY_CHECKS, not PASS/ready. Manual and historical v1 behavior unchanged.

The fixed budget is frozen before execution and must not be increased to favor a positive outcome. Multiple source events may each run that bounded observation; runner/API cost is not zero. No paid API/model/service or credential is introduced.

## Acceptance gate

Inspect the diff for this stopping rule, default-branch checkout, unchanged classifier blobs, source-head recheck, unchanged permissions and no PR artifact/code execution. On the literal implementation head execute existing classifier/association matrices and unchanged application CI; inspect Codacy and all applicable checks before operator activation.

After activation, refresh the existing minimal fixture once to generate a new current-head CI event and inspect exact source/head/run/job plus attempt lines. No manual observer comment, rerun, artificial check, policy change or extra repetition is allowed. Accept only executed observations; positive readiness requires the original native v2 ensemble. Retain old-head pending evidence separately. Close fixture without merge, retain branch and append execution evidence.

Optional timing/state combinations remain NOT_PROVEN. This is transport v1, not a new classifier protocol or universal native-policy PASS.
