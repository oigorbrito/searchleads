# SearchLeads — Current Handoff

**Updated:** 2026-08-24

This file is the continuity checkpoint for future work on this repository. A new chat/session should read this file before making architecture, business, test-status, or roadmap claims.

## Repository / project references

- Repository: `tihotm/searchleads`
- GitHub Project: https://github.com/users/tihotm/projects/4/views/1
- Current active branch: `feat/external-api-providers-v1`
- Current active PR: `#37 — feat: add external API provider layer with Apify`
- Parent branch: `feat/dental-facial-surgery-icp-v1`
- Parent PR: `#36 — feat: define dental facial-surgery education ICP MVP`
- PRs are draft/open/unmerged unless explicitly changed by the user.
- Do **not** merge, retarget, mark ready, enable auto-merge, or push to `main` without explicit user authorization.

## Core architecture — do not reinterpret

```text
DISCOVERY
→ ACQUISITION
→ EVIDENCE
→ STRUCTURED EXTRACTION
→ NORMALIZATION
→ ENTITY RESOLUTION
→ ENRICHMENT / FUSION
→ QUALIFICATION
→ EXPORT
```

Cross-cutting:

```text
PROVENANCE / VALIDATION / CONFIDENCE / REVIEW
```

Non-negotiable rules:

```text
COMPANY != LEAD
FOUND != VALID
NAME MATCH != ENTITY MATCH
CONTACT FOUND != CONTACT VALID
VALUE WITHOUT EVIDENCE != VERIFIED FACT
DISCOVERY SUCCESS != DISCOVERY COVERAGE
THIRD_PARTY_API_RESULT != VERIFIED FACT
PUBLIC_CRO_CLAIM != CFO_VERIFIED_CREDENTIAL
FIT != INTENT
MISSING EVIDENCE = UNKNOWN
```

## Commercial ICP V1 — authoritative business direction

Commercial object: `Person`.

Target:

- Brazil, with configurable whole-country / macro-region / state filters;
- general dentists are eligible for the formation/specialization prospect path;
- dentists with specialty/title can be filtered explicitly;
- Bucomaxilofacial / HOF / facial-surgery profiles generally have stronger FIT when supported by evidence;
- core offer relevance includes Blefaroplastia, Lip Lift, Lifting facial, Frontoplastia and related facial procedures;
- professional themself is the purchase decision-maker;
- company/clinic is context/evidence, not the lead object;
- company size is not a person-level exclusion gate;
- public professional contact is useful, but contact validity remains separate from FIT/INTENT.

Offer tracks:

```text
CEOF_SPECIALIZATION
COMPLEMENTARY_EXCLUSIVE_CEOF
```

Important semantics:

```text
PROFILE_FIT = HIGH / MEDIUM / LOW / UNKNOWN
LEARNING_INTENT = HIGH / MEDIUM / LOW / UNKNOWN
```

Profession/profile fit alone must **not** create learning intent. Absence of explicit intent evidence remains `UNKNOWN` and does not automatically disqualify a strong-fit lead.

## Regulatory model

Keep separate:

1. CFO-SEC-285/286 (2026 CEOF framework);
2. the separate TRF1 litigation concerning CFO Resolution 198/2019 (HOF);
3. PDL 177/2026 challenging CFO acts 283-286;
4. individual professional eligibility/credential verification;
5. campaign send-compliance approval.

Do not collapse a pending legislative/judicial challenge into an automatic conclusion that CEOF is suspended or invalid.

Readiness is deliberately split:

```text
PREPARATION_READY
= active official CFO registration
+ eligible ICP / offer track
+ public professional contact

SEND_READY
= PREPARATION_READY
+ explicit current campaign legal/compliance confirmation
```

## Active dental data state

Balanced real discovery batch:

```text
CANDIDATES = 50
MACRO_REGIONS = 5/5
CANDIDATES_PER_MACRO_REGION = 10
PUBLIC_CRO_CLAIM = 50/50
PUBLIC_PROFESSIONAL_OR_BOOKING_CHANNEL = 50/50
CFO_VERIFIED_ACTIVE = 0/50
PREPARATION_READY = 0/50
SEND_READY = 0/50
```

Priority official-verification queue:

```text
PRIORITY_CFO_REVIEW_QUEUE = 15
OFFICIAL_HISTORICAL_IDENTITY_MATCH = 5/15
CURRENT_ACTIVE_VERIFIED = 0/15
```

Wave 1 has five high-confidence identity candidates. Historical official identity evidence does **not** equal current active registration.

Current official specialty evidence exists for `Claudia Salete Judachesci / CRO-PR 22606` on the current CRO-PR HOF specialist list. This corroborates specialty evidence, not explicit active-registration state.

Files:

- `MVP-DENTAL-BATCH-50.md`
- `DENTAL-CFO-VERIFICATION-BATCH-50.csv`
- `DENTAL-CFO-VERIFICATION-PRIORITY-15.csv`
- `DENTAL-CFO-PRIORITY15-IDENTITY-EVIDENCE.csv`
- `DENTAL-CFO-VERIFICATION-WAVE1-5.csv`
- `DENTAL-CFO-CURRENT-OFFICIAL-EVIDENCE.csv`
- `DENTAL-CROPR-CURRENT-HOF-CROSSCHECK.csv`
- `DENTAL-CFO-VERIFICATION-WORKFLOW.md`

## External API provider layer — PR #37

Current implemented acquisition extension:

```text
ICP / explicit query plan
→ external API provider
→ raw provider response persisted as Evidence
→ provider-neutral WebSearchHit
→ existing dental deterministic discovery
→ CFO_VERIFICATION=PENDING
→ existing qualification / review flow
```

Implemented V1 provider:

```text
Provider = Apify
API base = https://api.apify.com/v2
Actor = apify~google-search-scraper
Auth = Authorization: Bearer <APIFY_API_TOKEN>
Country = br
Interface language = pt-BR
Default max pages/query = 1
```

Files added/changed on PR #37 include:

- `searchleads/external_api.py`
- `searchleads/apify_web_search.py`
- `searchleads/dental_external_discovery.py`
- `scripts/run_apify_dental_discovery.py`
- `tests/test_external_api_providers.py`
- `EXTERNAL-API-PROVIDERS-V1.md`
- `EXTERNAL-API-PROVIDERS-V1-REPORT.md`

Security/provenance rules:

- no API keys are committed;
- token comes from `APIFY_API_TOKEN` at runtime;
- token is sent in Authorization header, not persisted in URLs;
- raw provider output is persisted before projection;
- provider CRO/title claims remain `CFO_VERIFICATION=PENDING`;
- no learning-intent inference from provider data;
- no automatic person merge from names.

Provider roadmap recorded in the branch:

1. Apify Google Search — implemented;
2. Brave Search — recommended fallback web search;
3. Google Places — clinic/location context;
4. Hunter — later email discovery/deliverability;
5. SerpAPI — optional Google-SERP redundancy.

Do not integrate all providers at once; each provider must close a concrete gap.

## Test truth — critical continuity section

### Last fully executed remote full regression

GitHub Actions run `32544027242` on commit:

```text
6759dfd6701bc58c92296bc26177a002b4d7fb69
```

Result:

```text
FULL_UNITTEST_DISCOVER = PASS
TESTS_DISCOVERED = 234
TESTS_EXECUTED = 234
TESTS_PASSED = 234
TESTS_FAILED = 0
TESTS_ERRORS = 0
DETERMINISTIC_E2E = PASS
DENTAL_BATCH_50_SMOKE = PASS
WU3_LIVE_HTTP = PASS
```

Deterministic E2E export SHA:

```text
81af24599d7b0bc6ca012a397c243b4049d2e70f0e31a50e0c5eb1d747d0139d
```

Live BrasilAPI smoke in that successful run:

```text
WU3_LIVE_HTTP = PASS
COMPANY_ID = company:cnpj:33683111000280
CANDIDATE_FACTS = 10
```

See `FULL-REGRESSION-REPORT-2026-08-22.md`.

### Important E2E wording trap

`run_end_to_end_acceptance.py` still prints the historical generic company-level state:

```text
ICP_DEFINED=NO
REAL_QUALIFICATION=NOT_EVALUABLE
BUSINESS_QUALIFICATION=UNKNOWN
```

That script intentionally preserves the earlier generic acceptance contract. It does **not** override the separately implemented dental Person ICP:

```text
ICP_ID = dental-facial-surgery-education-br-v1
ICP_DEFINED = YES for the dental vertical
```

A future chat must not infer that the dental ICP is undefined because of the legacy E2E output.

### PR #37 changed-logic validation

Recorded in `EXTERNAL-API-PROVIDERS-V1-REPORT.md`:

```text
EXTERNAL_PROVIDER_TESTS = 6/6 PASS
PYTHON_MODULE_COMPILE = PASS
APIFY_DENTAL_DRY_RUN = PASS
```

These are targeted changed-logic results, not a substitute for a literal full current-head remote regression.

### Current-head GitHub Actions blocker

Current PR #37 head at handoff creation:

```text
303906a02e5f55accb99c3710cb1b715ad14903d
```

GitHub Actions run `32755225623` concluded `failure`, but the job reports:

```text
steps = []
runner_id = 0
runner_name = ""
```

Therefore:

```text
PR37_FULL_CURRENT_DISCOVER = BLOCKED_BEFORE_RUNNER_STEPS
PR37_CODE_TEST_FAILURE = NOT_OBSERVED
```

The parent PR #36 head `81799f93b334bb566882338f80e41d960ef2799c` also had a later Actions run terminating before runner steps (`steps=[]`, `runner_id=0`).

**Do not claim current-head full regression PASS until the current head actually executes the full workflow.**

## User-required testing/reporting behavior

For future changes, the requested operating mode is:

```text
1. run all relevant tests;
2. if a real code/test failure occurs, fix it;
3. rerun until the executable test suite completes successfully;
4. do not interrupt the user with step-by-step test chatter;
5. final testing update should be only a concise summary: PASS / FAIL / BLOCKED and exact counts;
6. distinguish code failure from CI/runner infrastructure failure;
7. never reuse an older successful run as proof that a newer head passed.
```

If GitHub Actions fails before any runner step, record it as infrastructure-blocked and do not label it as a code-test failure.

## Useful commands

Full regression:

```bash
python -m unittest discover -s tests -v
PYTHONPATH=. python scripts/run_end_to_end_acceptance.py
PYTHONPATH=. python scripts/evaluate_dental_verification_batch.py \
  DENTAL-CFO-VERIFICATION-BATCH-50.csv \
  --output /tmp/dental-batch-evaluated.csv
PYTHONPATH=. python scripts/run_live_brasilapi_smoke.py
```

Apify dry run without credentials:

```bash
PYTHONPATH=. python scripts/run_apify_dental_discovery.py --dry-run --max-queries 4
```

Bounded live Apify run when a runtime token is available:

```bash
APIFY_API_TOKEN=... PYTHONPATH=. python scripts/run_apify_dental_discovery.py \
  --max-queries 4 \
  --db searchleads-apify.db \
  --output apify-dental-candidates.json
```

## Remaining real blockers / next work

Priority order for continuation:

1. get a runner to execute the literal full regression on the **current PR #37 head**;
2. if tests fail, fix and rerun until PASS; if runner never starts, preserve `BLOCKED_BEFORE_RUNNER_STEPS` rather than inventing a test result;
3. when full current-head regression passes, update this handoff with the exact test count and successful commit SHA;
4. run bounded live Apify discovery only when `APIFY_API_TOKEN` is available in runtime; do not commit credentials;
5. continue official individual CFO/CRO active-status verification for the priority queue;
6. keep `PREPARATION_READY` separate from `SEND_READY`;
7. keep campaign legal/compliance state explicit and current before actual sending;
8. do not build more generic infrastructure unless real lead flow shows a concrete gap.

## Integration state

```text
MAIN_INTEGRATION = NOT_DONE
PR36 = DRAFT / OPEN / UNMERGED
PR37 = DRAFT / OPEN / UNMERGED
```

Do not infer that `main` contains the stacked implementation.

## Source-of-truth order for the next session

When facts conflict, prefer in this order:

1. current branch code and current GitHub state;
2. this `HANDOFF-CURRENT.md` for continuation context;
3. specific validation reports (`FULL-REGRESSION-REPORT-2026-08-22.md`, `EXTERNAL-API-PROVIDERS-V1-REPORT.md`);
4. PR descriptions;
5. older handoff/audit documents;
6. conversation memory.

If a statement is not supported by these sources, leave it `UNKNOWN` or verify it instead of filling the gap by inference.
