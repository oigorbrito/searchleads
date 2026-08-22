# SearchLeads — Dental MVP Handoff

**Date:** 2026-08-22
**Repository:** `tihotm/searchleads`
**Active PR:** #36 — `feat: define dental facial-surgery education ICP MVP`
**Branch:** `feat/dental-facial-surgery-icp-v1`
**Base:** `docs/handoff-audit-closure-v1` (PR #24)
**PR state:** DRAFT / OPEN / UNMERGED / MERGEABLE

## User working preference

- Continue autonomously when the user says `go` / `continue`.
- Keep MVP scope narrow.
- Do not expand tests for cosmetic coverage.
- For test work: run the complete relevant regression, fix and rerun until green when possible, and report only the final summary (`PASS`, `FAIL`, or external blocker) so the flow is not interrupted by intermediate test chatter.
- Do **not** merge, retarget, mark ready, enable auto-merge, or write to `main` without explicit authorization.

## Source-of-truth architecture

Pipeline remains:

`DISCOVERY → ACQUISITION → EVIDENCE → STRUCTURED EXTRACTION → NORMALIZATION → ENTITY RESOLUTION → ENRICHMENT/FUSION → QUALIFICATION → EXPORT`

Cross-cutting:

`PROVENANCE / VALIDATION / CONFIDENCE / REVIEW`

Non-negotiables:

- `COMPANY ≠ LEAD`
- `FOUND ≠ VALID`
- `NAME MATCH ≠ ENTITY MATCH`
- `CONTACT FOUND ≠ CONTACT VALID`
- `VALUE WITHOUT EVIDENCE ≠ VERIFIED FACT`
- `DISCOVERY SUCCESS ≠ DISCOVERY COVERAGE`

The dental commercial object is `Person`; clinic/company is context/evidence.

## Confirmed ICP V1

Target market: dentistry professionals in Brazil who may fit education/training in facial surgery.

Target professionals:

- general dentist
- dentist with specialty/title
- oral and maxillofacial surgeon / Bucomaxilofacial
- professionals with evidence of HOF / facial aesthetics / facial surgery activity

Core procedure relevance:

- Blepharoplasty
- Lip Lift
- Facelift / Lifting facial
- Frontoplasty / forehead lift
- related facial procedures

Geography is configurable:

- Brazil-wide
- macroregion: North, Northeast, Central-West, Southeast, South
- state

Title/specialty filters are configurable.

Offer formats may include specialization/training, in-person, immersion, mentorship, online/hybrid.

`FIT` and `INTENT` are separate:

- `PROFILE_FIT = HIGH / MEDIUM / LOW / UNKNOWN`
- `LEARNING_INTENT = HIGH / MEDIUM / LOW / UNKNOWN`
- profession/profile evidence alone never implies learning intent
- absence of intent evidence remains `UNKNOWN`

Company size is not a person-level gate.

## Regulatory/offer tracks

Implemented tracks:

1. `CEOF_SPECIALIZATION`
   - general dentists can remain prospects for the formation/specialization route
   - subject to official professional/admission verification

2. `COMPLEMENTARY_EXCLUSIVE_CEOF`
   - complementary training for CEOF-exclusive procedures
   - official CEOF specialty evidence is required

The MVP distinguishes the 2026 CEOF framework (CFO-SEC-285/286) from litigation concerning the older HOF Resolution 198/2019.

Pending legal/legislative context does not automatically erase lead-preparation work. Sending remains an explicit compliance decision.

Two readiness layers:

```text
PREPARATION_READY
= active official CFO registration
+ eligible ICP / offer track
+ public professional contact

SEND_READY
= PREPARATION_READY
+ explicit current campaign legal/compliance confirmation
```

## Implemented dental MVP modules

Key files include:

- `searchleads/dental_facial_surgery_icp.py`
- `searchleads/dental_regulatory.py`
- `searchleads/dental_person_lead.py`
- `searchleads/dental_repeatable_discovery.py`
- `searchleads/dental_outreach.py`
- `scripts/evaluate_dental_verification_batch.py`

Focused dental tests:

- `tests/test_dental_facial_surgery_icp.py`
- `tests/test_dental_repeatable_discovery.py`
- `tests/test_dental_outreach.py`

## Real discovery / operational data

Active real batch:

```text
CANDIDATES = 50
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
- `MVP-CFO-VERIFICATION-WAVE1-RESULT.md`
- `MVP-REGULATORY-CHECKPOINT-2026-08-21.md`

Priority verification state:

```text
PRIORITY_CFO_QUEUE = 15
WAVE1 = 5
OFFICIAL_HISTORICAL_IDENTITY_MATCH = 5/5
OFFICIAL_CURRENT_SPECIALTY_EVIDENCE = 1/5
CFO_VERIFIED_ACTIVE = 0/50
```

Current official specialty evidence:

- Claudia Salete Judachesci — CRO-PR 22606 appears on the current CRO-PR HOF specialist page.
- This supports current specialty evidence, **not** explicit active-registration status.

No candidate is promoted to `VERIFIED_ACTIVE` from a private directory, historical document, specialty list alone, or absence of a cancellation record.

## Official verification boundary

The CFO professional-search portal exposes fields for CRO/UF, registration number, specialty, habilitation and name, but no reusable documented result endpoint was exposed through the accessible interface.

Therefore current active status remains a manual/external boundary:

```text
public discovery
→ indexed official identity/specialty evidence when available
→ current individual CFO/CRO lookup
→ VERIFIED_ACTIVE / INACTIVE / NOT_FOUND
```

Do not scrape/reverse-engineer the CFO portal for the MVP unless explicitly authorized and technically justified.

## Test state — COMPLETE CURRENT REGRESSION

A full GitHub Actions regression was added to `.github/workflows/dental-mvp.yml` and executed on the remote PR branch.

**Workflow run:** `dental-mvp` run #48 / run id `32544027242`
**Job:** `full-regression`
**Conclusion:** `SUCCESS`

### Full unittest discover

```text
python -m unittest discover -s tests -v
Ran 234 tests in 7.616s
OK
```

Result:

```text
FULL_CURRENT_TEST_SUITE = 234/234 PASS
```

This supersedes the earlier state where only baseline + change-impact subsets were available.

### Deterministic end-to-end acceptance

Remote run passed:

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
```

Deterministic export remains:

```text
EXPORT_SHA256=81af24599d7b0bc6ca012a397c243b4049d2e70f0e31a50e0c5eb1d747d0139d
```

The legacy generic/company E2E script still prints:

```text
ICP_DEFINED=NO
REAL_QUALIFICATION=NOT_EVALUABLE
BUSINESS_QUALIFICATION=UNKNOWN
```

Important: this is now a **legacy integration mismatch**, not absence of the dental ICP. The dental ICP exists in PR #36, but the old generic E2E acceptance script has not yet been rewired to consume the new person-centric dental policy. Do not interpret this line as “dental ICP undefined.”

### Batch smoke

```text
ROWS=50
PREP_READY=0
SEND_READY=0
REVIEW=50
EXCLUDE=0
```

This is expected because current active CFO verification is still pending for the batch.

### Live BrasilAPI smoke — WU3 strict gate resolved

The remote GitHub Actions runner has outbound connectivity and the live adapter smoke passed:

```text
WU3_LIVE_HTTP=PASS
COMPANY_ID=company:cnpj:33683111000280
CANDIDATE_FACTS=10
```

Therefore the previous environment-only WU3 blocker is resolved on the remote runner:

```text
WU3_LIVE_HTTP = PASS
```

## Current status

```text
ARCHITECTURAL_DIRECTION = ALIGNED
NON_NEGOTIABLE_PRINCIPLES = ALIGNED

FULL_CURRENT_TEST_SUITE = 234/234 PASS
DETERMINISTIC_E2E = PASS
E2E_EXPORT_SHA = 81af24599d7b0bc6ca012a397c243b4049d2e70f0e31a50e0c5eb1d747d0139d
WU3_LIVE_HTTP = PASS
DENTAL_MVP_FOCUSED_TESTS = PASS
BATCH_50_SMOKE = PASS

ICP_DENTAL_V1 = DEFINED
DENTAL_PERSON_QUALIFICATION = IMPLEMENTED_MVP
REPEATABLE_DENTAL_DISCOVERY = IMPLEMENTED_MVP
PREPARATION_VS_SEND_GATE = IMPLEMENTED_MVP
REAL_DENTAL_DISCOVERY_BATCH = 50

CFO_VERIFIED_ACTIVE = 0/50
PREPARATION_READY = 0/50
CAMPAIGN_LEGAL_STATUS = PENDING_REVIEW
SEND_READY = 0/50

LEGACY_GENERIC_E2E_DENTAL_ICP_BRIDGE = NOT_DONE
MAIN_INTEGRATION = NOT_DONE
```

## Recommended next work

Highest-value sequence:

1. **Do not add more broad tests unless new behavior is introduced.** The complete current suite is green.
2. Decide whether to wire the new dental person-centric ICP into the legacy generic E2E acceptance so `ICP_DEFINED=YES` is represented in the commercial vertical acceptance path without breaking old company acceptance semantics.
3. Continue the first manual/current CFO verification wave for the five highest-confidence identities.
4. As soon as one current active registration is confirmed, populate the batch CSV and rerun the evaluator to obtain the first `PREPARATION_READY` candidate.
5. Keep `SEND_READY` separate until current legal/compliance input explicitly permits the campaign.
6. Do not merge PR #36 or the stacked PR chain without explicit user authorization.

## PR / branch governance

- `main` historically remained bootstrap-only while the implementation is stacked in draft PRs.
- PR #36 is based on PR #24.
- Keep PR #36 draft/open/unmerged unless the user explicitly authorizes integration.
- No merge, retarget, ready-for-review, or auto-merge action has been authorized.

## Next-chat startup instruction

When continuing in a new chat, treat this file as the latest handoff source of truth for the dental MVP, together with the original project handoff.

Start by reading this file from branch `feat/dental-facial-surgery-icp-v1`, then inspect PR #36 and the latest GitHub Actions run before making code changes.

For tests, follow the user's requested workflow: run relevant/full regression, fix failures and rerun to green where possible, then report only the final pass/fail/blocker summary.