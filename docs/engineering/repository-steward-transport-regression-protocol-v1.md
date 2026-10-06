# Bounded observer transport — controlled regression protocol v1

Frozen before implementation; target source main: 450243c4de7223db5d2e0b10de737de403520d3d.

Claim: the actual observer query step enforces its fixed budget and head check, stops on invalid/API failures and does not apply automatic-v2 retry to manual/v1 invocation. This is synthetic transport coverage, not new native GitHub policy evidence.

Execute the existing workflow query run block unchanged in Bash, with real target classifiers and jq. Replace only gh responses and sleep with deterministic local stubs in a temporary directory; permit no network and no repository writes. Require a unique named workflow step and literal run-block indentation; unsupported structure fails extraction. No copied transport algorithm or test-only classifier.

Freeze eight cases:
1. Pending then success: two queries, one ten-second requested sleep, candidate only at attempt 1.
2. Persistent pending: exactly seven queries, six ten-second requested sleeps, final NOT_READY_CHECKS at attempt 6.
3. Head changed after pending: two queries, one sleep, final READINESS_UNKNOWN; no candidate.
4. API error after pending: two calls, one sleep, nonzero process; no successful decision output or candidate.
5. Missing requested field: one query, no sleep, READINESS_UNKNOWN.
6. Draft with pending checks: one query, no sleep, NOT_READY_DRAFT.
7. Manual v2 pending: one query, no sleep, NOT_READY_CHECKS.
8. Automatic v1 pending: one query, no sleep, NOT_READY_CHECKS.

Each case checks process exit, exact API-call count, sleep arguments, actual observation count/attempt and final decision or absence of output. A finite supplied response sequence fails on extra queries. Harness timeout is ten seconds; sleeps are recorded rather than elapsed, so this does not measure real runner latency.

Integrate with the existing literal-head classifier CI, keeping READ-only permissions and existing matrices. Record head/run/job and all applicable checks. Observer, classifier, association and application files remain unchanged. Native budget exhaustion/head change/API failure remain NOT_PROVEN unless separately induced and executed. Preserve prior evidence.

Status at freeze: DOCUMENTED; IMPLEMENTATION/EXECUTION/ACCEPTANCE pending.
