# SearchLeads — Current Dental MVP Handoff

**Repository:** `tihotm/searchleads`  
**Working branch:** `feat/dental-facial-surgery-icp-v1`  
**Draft PR:** #36 — `feat: define dental facial-surgery education ICP MVP`  
**PR base:** `docs/handoff-audit-closure-v1`  
**Project board reference:** https://github.com/users/tihotm/projects/4/views/1  
**Handoff refreshed:** 2026-08-24  

> This file is the continuity source for the current project state. A future chat/session should read this file before proposing changes. Do not infer missing business requirements, do not reinterpret historical test output without the distinctions below, and do not merge/retarget/mark-ready/auto-merge PRs without explicit authorization.

## 1. Product direction now confirmed

Commercial object is **Person**, not company.

Target audience:

- dentists across Brazil;
- general dentists are eligible for the formation/specialization prospect path;
- title/specialty filters are configurable;
- Bucomaxilofacial, HOF and facial-surgery/facial-aesthetics evidence generally raise FIT when evidence-backed;
- target procedures include Blepharoplasty, Lip Lift, Facelift/Lifting facial, Frontoplasty and related facial procedures;
- offer formats may include in-person, immersion, mentorship, longer formation/specialization, online or hybrid;
- the professional themself is the purchase decision-maker.

Geography is configurable for:

- all Brazil;
- macroregion: North, Northeast, Central-West, Southeast, South;
- state.

Company/clinic is evidence/context. **Company size is not a person-level ICP gate.**

## 2. Qualification semantics

Keep these independent:

```text
FIT = HIGH / MEDIUM / LOW / UNKNOWN
INTENT = HIGH / MEDIUM / LOW / UNKNOWN
```

Rules:

- profession/profile fit does not imply learning intent;
- missing intent evidence stays `UNKNOWN`;
- `HIGH FIT + UNKNOWN INTENT` remains a valid prospect for the specialization/formation path;
- public contactability is separate from FIT and INTENT;
- public CRO/title claims are discovery evidence, not official verification;
- name alone is never sufficient identity evidence;
- clinic/company alone never makes a person a lead.

## 3. Offer-track/regulatory separation

Implemented tracks:

```text
CEOF_SPECIALIZATION
COMPLEMENTARY_EXCLUSIVE_CEOF
```

For complementary courses involving CEOF-exclusive procedures, official CEOF specialty evidence is required by the current policy gate.

Do not infer CEOF competence from HOF or CTBMF by analogy.

Regulatory model intentionally separates:

- CFO-SEC-285/286 (2026 CEOF framework);
- litigation concerning CFO Resolution 198/2019 (HOF);
- PDL 177/2026 challenging CFO acts 283–286.

Current campaign sending still requires explicit current legal/compliance confirmation. A pending challenge is not automatically treated as suspension.

## 4. Readiness layers

```text
PREPARATION_READY
= active official CFO registration
+ eligible ICP / offer track
+ public professional contact

SEND_READY
= PREPARATION_READY
+ explicit current campaign legal/compliance confirmation
```

This is intentional: lead preparation work may continue while campaign-level legal/compliance remains under review.

## 5. Current discovery batch

Active MVP batch:

```text
REAL_DENTAL_DISCOVERY_BATCH = 50
MACRO_REGIONS = 5/5
CANDIDATES_PER_MACRO_REGION = 10
PUBLIC_CRO_CLAIM = 50/50
PUBLIC_PROFESSIONAL_OR_BOOKING_CHANNEL = 50/50
```

Operational files:

- `MVP-DENTAL-BATCH-50.md`
- `DENTAL-CFO-VERIFICATION-BATCH-50.csv`
- `DENTAL-CFO-VERIFICATION-PRIORITY-15.csv`
- `DENTAL-CFO-PRIORITY15-IDENTITY-EVIDENCE.csv`
- `DENTAL-CFO-VERIFICATION-WAVE1-5.csv`
- `DENTAL-CFO-CURRENT-OFFICIAL-EVIDENCE.csv`
- `DENTAL-CROPR-CURRENT-HOF-CROSSCHECK.csv`
- `DENTAL-CFO-VERIFICATION-WORKFLOW.md`
- `scripts/evaluate_dental_verification_batch.py`

Current verification state:

```text
PRIORITY_CFO_REVIEW_QUEUE = 15
OFFICIAL_HISTORICAL_IDENTITY_MATCH = 5/15
CURRENT_OFFICIAL_SPECIALTY_EVIDENCE = 1/15
CFO_VERIFIED_ACTIVE = 0/50
PREPARATION_READY = 0/50
SEND_READY = 0/50
```

Current official specialty evidence includes CRO-PR 22606 / Claudia Salete Judachesci on the current CRO-PR HOF specialist roster. This corroborates specialty/name/CRO but is **not** promoted to active-registration status because the page does not explicitly state current cadastral activity.

## 6. Official CFO boundary

The public CFO search is the current official/manual boundary for individual active registration status.

Do not:

- replace CFO/CRO verification with Doctoralia or a professional website;
- infer `VERIFIED_ACTIVE` from historical council documents;
- infer active status from the absence of indexed cancellation/transfer/low-registration acts;
- reverse-engineer or scrape the portal with a brittle/unapproved mechanism merely to force automation.

Indexed official historical/current specialty evidence can be stored separately and used to prioritize manual review.

## 7. Test truth — latest full regression

A full GitHub Actions regression was added to `.github/workflows/dental-mvp.yml` and executed on the PR branch.

**Workflow run:** `dental-mvp` run #48  
**Run ID:** `32544027242`  
**Result:** `SUCCESS`

### Full unittest discovery

```text
python -m unittest discover -s tests -v
Ran 234 tests in 7.616s
OK
```

Therefore:

```text
FULL_CURRENT_PRIVATE_BRANCH_TEST_DISCOVER = 234/234 PASS
```

This supersedes earlier handoff caveats that a fresh complete private-branch unittest discovery had not been run.

### Deterministic end-to-end acceptance

`PYTHONPATH=. python scripts/run_end_to_end_acceptance.py`

Result:

```text
REAL_COMPANIES=YES
MULTI_SOURCE=YES
DEDUPLICATION=PASS
COMPANY_ER=PASS
PROVENANCE=PASS
CONTACT_DISCOVERY=PASS
CONTACT_VALIDATION=PASS
PERSON_ROLE=PASS
QUALIFICATION_ENGINE=PASS
EXPORT=PASS
REPRODUCIBLE=PASS
EXPORT_SHA256=81af24599d7b0bc6ca012a397c243b4049d2e70f0e31a50e0c5eb1d747d0139d
```

Important compatibility note: this legacy end-to-end acceptance script still prints:

```text
ICP_DEFINED=NO
REAL_QUALIFICATION=NOT_EVALUABLE
BUSINESS_QUALIFICATION=UNKNOWN
```

That output refers to the **legacy generic/company qualification path**, which intentionally has no default business ICP. It must **not** be interpreted as saying the new dentistry person-centric ICP is undefined.

Current dentistry state is:

```text
DENTAL_ICP_DEFINED = YES
DENTAL_PERSON_QUALIFICATION = IMPLEMENTED_MVP
```

### Dental batch smoke

```text
ROWS=50
PREP_READY=0
SEND_READY=0
REVIEW=50
EXCLUDE=0
```

This is currently expected because official active CFO verification and send-compliance confirmation remain pending.

### Live BrasilAPI smoke

`PYTHONPATH=. python scripts/run_live_brasilapi_smoke.py`

Result:

```text
WU3_LIVE_HTTP=PASS
COMPANY_ID=company:cnpj:33683111000280
CANDIDATE_FACTS=10
```

This closes the earlier environment-only WU3 live HTTP blocker for the GitHub Actions execution environment.

## 8. Current technical/commercial status

```text
ARCHITECTURAL_DIRECTION = ALIGNED
NON_NEGOTIABLE_PRINCIPLES = ALIGNED

FULL_CURRENT_PRIVATE_BRANCH_TEST_DISCOVER = 234/234 PASS
DETERMINISTIC_E2E = PASS
WU3_LIVE_HTTP = PASS
DENTAL_MVP_CI = PASS

DENTAL_ICP_DEFINED = YES
DENTAL_PERSON_QUALIFICATION = IMPLEMENTED_MVP
REPEATABLE_DENTAL_DISCOVERY = IMPLEMENTED_MVP
PREPARATION_VS_SEND_GATE = IMPLEMENTED_MVP
REAL_DENTAL_DISCOVERY_BATCH = 50

CFO_VERIFIED_ACTIVE = 0/50
PREPARATION_READY = 0/50
CAMPAIGN_LEGAL_STATUS = PENDING_REVIEW
SEND_READY = 0/50

PR_36 = DRAFT / OPEN / UNMERGED
MAIN_INTEGRATION = NOT_DONE
```

## 9. Non-negotiable architecture principles

Preserve:

```text
COMPANY ≠ LEAD
FOUND ≠ VALID
NAME MATCH ≠ ENTITY MATCH
CONTACT FOUND ≠ CONTACT VALID
VALUE WITHOUT EVIDENCE ≠ VERIFIED FACT
DISCOVERY SUCCESS ≠ DISCOVERY COVERAGE
```

Also preserve:

- provenance is mandatory;
- validation is separate from discovery;
- person entity resolution is separate and conservative;
- qualification is a business layer, not data acquisition;
- UNKNOWN must remain representable;
- do not use opaque scoring to hide unsupported assumptions;
- do not invent sources or business requirements.

## 10. Testing policy requested by user

For MVP work, prioritize tests that prevent expensive business errors rather than expanding edge-case coverage unnecessarily.

However, before declaring a branch stable, use the full regression workflow. If a test fails:

```text
run → inspect → fix → rerun
```

Do not provide an intermediate “done” summary while known tests are failing. Final status should clearly state only the final passed/failed state and any external blocker that cannot be repaired in code.

## 11. Next recommended execution order

Do not add more framework/infrastructure unless real usage proves it necessary.

Next highest-value work:

1. manually verify current CFO active status for the first Wave 1 candidates;
2. write verified active status and official source into the batch CSV;
3. rerun `scripts/evaluate_dental_verification_batch.py`;
4. obtain first `PREPARATION_READY` leads;
5. separately confirm current legal/compliance status for campaign sending;
6. only then create first `SEND_READY` subset;
7. measure funnel quality before scaling beyond the current batch.

## 12. Git/PR safety

Current implementation lives in stacked draft PRs; `main` is not the integration source of truth yet.

For PR #36 specifically:

- keep draft/open unless explicitly told otherwise;
- do not merge;
- do not retarget;
- do not mark ready;
- do not enable auto-merge;
- do not push directly to `main`.

A future session should begin by reading this handoff plus the current PR metadata/workflow status before making project assertions.
