# SearchLeads

Evidence-preserving lead discovery, enrichment, entity-resolution and qualification pipeline.

## Current status

The generic technical pipeline is implemented as a stacked draft-PR series. The first real commercial ICP is defined for dental facial-surgery education.

```text
ARCHITECTURAL_DIRECTION = ALIGNED
TECHNICAL_END_TO_END_ACCEPTANCE = PASS
PERSON_ENTITY_RESOLUTION = IMPLEMENTED_V1
WU14_EXECUTION_REASSESSMENT = IMPLEMENTED_V1
WU3_LIVE_HTTP = PENDING_EXTERNAL_SMOKE

ICP_DEFINED = YES
ICP_ID = dental-facial-surgery-education-br-v1
PRIMARY_COMMERCIAL_ENTITY = PERSON
DENTAL_PERSON_QUALIFICATION = IMPLEMENTED_MVP
REPEATABLE_DENTAL_DISCOVERY = IMPLEMENTED_MVP
OUTREACH_READINESS_GATE = IMPLEMENTED_MVP
PREPARATION_VS_SEND_GATE = IMPLEMENTED_MVP
REAL_DENTAL_DISCOVERY_BATCH = 20
CFO_VERIFIED_ACTIVE = 0/20
PREPARATION_READY = 0/20
CAMPAIGN_LEGAL_STATUS = PENDING_REVIEW
SEND_READY = 0/20

MAIN_INTEGRATION = NOT_DONE
```

See:

- `ICP-DENTAL-FACIAL-SURGERY-V1.md` — business definition;
- `MVP-DENTAL-COHORT-V1.md` — first 10-profile cross-region smoke;
- `MVP-DENTAL-BATCH-20.md` — bounded 20-candidate real discovery batch;
- `DENTAL-CFO-VERIFICATION-BATCH-20.csv` — manual official-verification worksheet;
- `DENTAL-CFO-VERIFICATION-WORKFLOW.md` — operational CFO review flow;
- `HANDOFF-AUDIT-CLOSURE.md` — earlier strict technical audit.

## ICP V1

Target market:

- Brazil-wide, with optional region/state filters;
- general dentists are eligible;
- Bucomaxilofacial and HOF profiles are eligible and typically higher FIT when evidence-backed;
- campaigns may filter by title/specialty;
- offer format combines in-person, immersion, mentoring, longer-form training and online/hybrid education;
- core procedure relevance includes Blefaroplastia, Lip Lift, Lifting facial, Frontoplastia and evidence-backed adjacent facial procedures.

Commercial qualification is Person-centered. Clinic/company remains context and evidence source.

### FIT vs INTENT

```text
FIT = HIGH / MEDIUM / LOW / UNKNOWN
INTENT = HIGH / MEDIUM / LOW / UNKNOWN
```

SearchLeads never converts absence of learning-intent evidence into `LOW` intent. Missing intent stays `UNKNOWN`.

Priority:

```text
P1 = HIGH FIT + HIGH INTENT
P2 = strong fit with weaker/unknown intent, or medium fit with high intent
P3 = eligible lower-priority combinations
REVIEW = insufficient evidence for an active filter
EXCLUDE = explicit filter mismatch
```

## Dental MVP flow

```text
public web discovery
→ candidate with explicit public evidence
→ conservative exact CRO / exact URL dedupe
→ CFO/CRO official verification
→ Person-centered FIT / INTENT
→ offer-track regulatory gate
→ public professional contact
→ PREPARATION_READY / REVIEW / EXCLUDE
→ campaign legal/compliance gate
→ SEND_READY / REVIEW / EXCLUDE
```

Public discovery claims never become official credential facts automatically. Name-only matching never auto-merges people.

## Regulatory context

The current MVP distinguishes the 2026 CEOF framework from the separate HOF litigation.

CFO-SEC-285/2026 amended the prior facial-surgery prohibition framework. CFO-SEC-286/2026 recognizes Cirurgia Estética Orofacial (CEOF), lists CEOF procedures and establishes formation requirements. CFO Technical Note 001/2026 emphasizes specialty-specific competence boundaries rather than extension by analogy.

Separately, on 2026-08-19 the TRF1 8th Panel concluded judgment in case `1003948-83.2019.4.01.3400`, concerning CFO Resolution 198/2019 (Harmonização Orofacial). SearchLeads does not treat that event by itself as a direct suspension finding for CFO-SEC-285/286.

PDL 177/2026 seeks to suspend CFO acts 283-286 and was still pending on 2026-08-21. A pending challenge is not silently converted into a legal conclusion by the application.

Because this is a changing, high-stakes context, actual campaign sending still defaults to:

```text
CampaignLegalStatus.PENDING_REVIEW
```

This is an operational risk-control gate, not a claim that CEOF rules are invalid or suspended.

## Two readiness layers

The MVP preserves useful lead work independently of campaign send approval.

```text
PREPARATION_READY
= active official CFO registration
+ eligible ICP / offer track
+ public professional contact

SEND_READY
= PREPARATION_READY
+ explicit current campaign legal/compliance confirmation
```

`PAUSED` explicitly blocks campaign sending. A record can therefore become preparation-ready while sending remains under review.

## Bounded real batch

Current dental discovery smoke:

```text
CANDIDATES = 20
MACRO_REGIONS = 5/5
PUBLIC_CRO_CLAIM = 20/20
PUBLIC_PROFESSIONAL_OR_BOOKING_CHANNEL = 20/20
FIT_HIGH = 19
FIT_MEDIUM = 1
INTENT_MEDIUM = 4
INTENT_UNKNOWN = 16
CFO_VERIFIED_ACTIVE = 0/20
PREPARATION_READY = 0/20
SEND_READY = 0/20
```

These are discovery-smoke metrics, not production precision/recall or conversion claims.

## MVP verification workflow

Fill only official CFO/CRO-supported fields in `DENTAL-CFO-VERIFICATION-BATCH-20.csv`, then run:

```bash
PYTHONPATH=. python scripts/evaluate_dental_verification_batch.py \
  DENTAL-CFO-VERIFICATION-BATCH-20.csv \
  --output DENTAL-CFO-VERIFICATION-BATCH-20-EVALUATED.csv
```

The evaluator keeps public claims separate from official verification and reports preparation readiness separately from send readiness.

The untouched sheet should produce:

```text
ROWS=20 PREP_READY=0 SEND_READY=0 REVIEW=20 EXCLUDE=0
```

## Validation state

Historical whole-repository technical baseline:

```text
162 / 162 PASS
```

Strict post-baseline audit validation:

```text
POST_BASELINE_ISOLATED_CONTRACT_TESTS = 53 / 53 PASS
CHANGE_IMPACT_REGRESSION = 33 / 33 PASS
UNIQUE_POST_BASELINE_TESTS_EXERCISED = 86 / 86 PASS
```

The affected-module E2E replay reproduced the accepted export SHA-256:

```text
81af24599d7b0bc6ca012a397c243b4049d2e70f0e31a50e0c5eb1d747d0139d
```

For MVP speed, the dental vertical intentionally uses a focused suite protecting only high-cost mistakes:

```text
DENTAL_FOCUSED_TESTS = 13
```

The CI also smoke-runs the manual 20-row CFO verification workflow. Exhaustive edge-case expansion is deferred until real lead flow.

## Commands

Focused dental MVP:

```bash
python -m unittest \
  tests.test_dental_facial_surgery_icp \
  tests.test_dental_repeatable_discovery \
  tests.test_dental_outreach -v
```

General deterministic validation:

```bash
python -m unittest discover -s tests -v
python scripts/run_end_to_end_acceptance.py
```

Literal WU3 live smoke from an environment with outbound DNS/HTTPS:

```bash
python scripts/run_live_brasilapi_smoke.py
```

## Core policies

- `Company != Lead`;
- the dental campaign's commercial target is `Person`;
- `Found != Valid`;
- `Name Match != Entity Match`;
- `Contact Found != Contact Valid`;
- evidence/provenance is preserved;
- same-name people do not auto-match;
- fuzzy company/person identity is not silently merged;
- public CRO/title claims do not become official facts without CFO/CRO verification;
- disagreement remains an explicit conflict;
- contact validation does not claim deliverability;
- FIT and INTENT remain explainable and separate;
- missing evidence becomes `UNKNOWN`, not an invented conclusion;
- professional preparation readiness is separate from campaign send approval;
- campaign legal/compliance state is separate from individual professional eligibility;
- gap execution remains bounded and uses known capabilities only.
