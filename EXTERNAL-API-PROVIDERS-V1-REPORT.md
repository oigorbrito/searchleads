# External API Providers V1 — Validation Report

## Scope

This work keeps the existing SearchLeads architecture and adds an interchangeable external-API acquisition boundary.

Implemented provider in V1:

```text
Apify REST API
→ apify/google-search-scraper
→ raw dataset item persisted as Evidence
→ provider-neutral WebSearchHit
→ existing dental repeatable discovery
→ CFO_VERIFICATION=PENDING
```

No third-party API output bypasses provenance, person/company entity resolution, contact validation, CFO/CRO verification, FIT/INTENT separation, or campaign compliance.

## Current Apify contract

Verified against current official Apify API/Actor documentation on 2026-08-24:

```text
API_BASE = https://api.apify.com/v2
ACTOR = apify~google-search-scraper
SYNC_ENDPOINT = /actors/{actorId}/run-sync-get-dataset-items
AUTH = Authorization: Bearer <token>
COUNTRY = br
INTERFACE_LANGUAGE = pt-BR
MAX_PAGES_PER_QUERY = bounded, default 1
```

The adapter deliberately omits undocumented Actor input fields and accepts dataset pages with no `organicResults` as valid empty-result evidence.

## Changed-logic validation

A credential-free local engineering reconstruction exercised the external-provider layer with injected Apify transport:

```text
EXTERNAL_PROVIDER_TESTS = 6/6 PASS
```

Covered behaviors:

1. API token is sent in the Authorization header and never in the persisted/request URL;
2. raw Apify dataset output is persisted before projected search hits;
3. identical provider payloads are idempotent;
4. bounded dataset item count is enforced;
5. public CRO claims discovered through the provider remain CFO verification `PENDING`;
6. an Apify dataset page without `organicResults` remains valid empty evidence.

The current module set also passes Python bytecode compilation in the local engineering reconstruction.

## Inherited current-base regression

Immediately before this external-provider branch, the parent dental branch completed the literal current repository regression in GitHub Actions:

```text
BASE_FULL_SUITE = 234/234 PASS
DETERMINISTIC_E2E = PASS
E2E_EXPORT_SHA256 = 81af24599d7b0bc6ca012a397c243b4049d2e70f0e31a50e0c5eb1d747d0139d
DENTAL_BATCH_50_SMOKE = PASS
WU3_LIVE_HTTP = PASS
```

See `FULL-REGRESSION-REPORT-2026-08-22.md`.

## Current-branch full CI status

GitHub Actions pull-request runs for PR #37 have repeatedly terminated before any job step started. The API reports the `full-regression` job with `steps = null`, and no job log blob is available. Re-running the job and changing the runner label did not cause a runner step to start.

Therefore this is recorded conservatively as:

```text
PR37_FULL_CURRENT_DISCOVER = NOT_EXECUTED_BY_GITHUB_RUNNER
PR37_CODE_TEST_FAILURE = NOT_OBSERVED
PR37_EXTERNAL_PROVIDER_CHANGED_LOGIC = 6/6 PASS
```

The no-step Actions runs are not relabeled as test failures because no checkout, Python setup, unittest, E2E, batch, or live-source command actually executed.

## Validation gate

```text
PROVIDER_ARCHITECTURE = PASS
APIFY_CONTRACT_ALIGNMENT = PASS
RAW_EVIDENCE_PERSISTENCE = PASS
TOKEN_HANDLING = PASS
CFO_VERIFICATION_BYPASS = NO
INTENT_INFERENCE_FROM_PROVIDER = NO
CHANGED_LOGIC_TESTS = PASS
INHERITED_BASE_FULL_REGRESSION = PASS
CURRENT_BRANCH_GITHUB_FULL_REGRESSION = BLOCKED_BEFORE_RUNNER_STEPS
```

PR #37 remains draft/open/unmerged until a complete current-branch regression can execute in a runner environment.
