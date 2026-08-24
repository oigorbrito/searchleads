# SearchLeads

Evidence-preserving lead discovery, enrichment, entity-resolution and qualification pipeline.

## Current status

The generic technical pipeline is implemented as a stacked draft-PR series. The first real commercial ICP is defined for dental facial-surgery education, and an external-API provider layer is being added without changing the evidence/provenance model.

```text
ARCHITECTURAL_DIRECTION = ALIGNED
TECHNICAL_END_TO_END_ACCEPTANCE = PASS
PERSON_ENTITY_RESOLUTION = IMPLEMENTED_V1
WU14_EXECUTION_REASSESSMENT = IMPLEMENTED_V1
WU3_LIVE_HTTP = PASS

ICP_DEFINED = YES
ICP_ID = dental-facial-surgery-education-br-v1
PRIMARY_COMMERCIAL_ENTITY = PERSON
DENTAL_PERSON_QUALIFICATION = IMPLEMENTED_MVP
REPEATABLE_DENTAL_DISCOVERY = IMPLEMENTED_MVP
OUTREACH_READINESS_GATE = IMPLEMENTED_MVP
PREPARATION_VS_SEND_GATE = IMPLEMENTED_MVP
REAL_DENTAL_DISCOVERY_BATCH = 50
CFO_VERIFIED_ACTIVE = 0/50
PREPARATION_READY = 0/50
CAMPAIGN_LEGAL_STATUS = PENDING_REVIEW
SEND_READY = 0/50

EXTERNAL_API_PROVIDER_LAYER = IMPLEMENTED_V1_ON_PR37
APIFY_GOOGLE_SEARCH_PROVIDER = IMPLEMENTED_V1_ON_PR37
MAIN_INTEGRATION = NOT_DONE
```

## Validation

The current stacked branch before the external-API extension completed a literal full regression in GitHub Actions:

```text
FULL_CURRENT_TEST_COUNT = 234 / 234 PASS
DETERMINISTIC_E2E = PASS
E2E_EXPORT_SHA256 = 81af24599d7b0bc6ca012a397c243b4049d2e70f0e31a50e0c5eb1d747d0139d
DENTAL_BATCH_50_SMOKE = PASS
WU3_LIVE_HTTP = PASS
```

The live BrasilAPI smoke ingested SERPRO CNPJ `33683111000280` over HTTP and persisted 10 candidate facts.

See `FULL-REGRESSION-REPORT-2026-08-22.md` and `WORK-UNIT-03-REPORT.md`.

The external-API extension must pass the same full-regression workflow before it is considered validated.

## Core architecture

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

Cross-cutting requirements remain:

```text
PROVENANCE / VALIDATION / CONFIDENCE / REVIEW
```

Core rules:

- `Company != Lead`;
- `Found != Valid`;
- `Name Match != Entity Match`;
- `Contact Found != Contact Valid`;
- `Value without evidence != verified fact`;
- provider/API output is evidence from that provider, not automatic truth;
- public CRO/title claims do not become official credentials without CFO/CRO verification;
- FIT and INTENT remain separate;
- missing evidence becomes `UNKNOWN`.

## Dental ICP V1

Target market:

- Brazil-wide, with optional region/state filters;
- general dentists are eligible;
- Bucomaxilofacial and HOF profiles are eligible and typically higher FIT when evidence-backed;
- campaigns may filter by title/specialty;
- offer format combines in-person, immersion, mentoring, longer-form training and online/hybrid education;
- core procedure relevance includes Blefaroplastia, Lip Lift, Lifting facial, Frontoplastia and evidence-backed adjacent facial procedures.

Commercial qualification is Person-centered. Clinic/company remains context and evidence source.

```text
FIT = HIGH / MEDIUM / LOW / UNKNOWN
INTENT = HIGH / MEDIUM / LOW / UNKNOWN
```

Absence of learning-intent evidence remains `UNKNOWN`.

## Dental MVP flow

```text
public discovery
→ raw evidence
→ candidate
→ conservative exact CRO / exact URL dedupe
→ CFO/CRO official verification
→ Person-centered FIT / INTENT
→ offer-track regulatory gate
→ professional contact
→ PREPARATION_READY / REVIEW / EXCLUDE
→ campaign legal/compliance gate
→ SEND_READY / REVIEW / EXCLUDE
```

## External API provider layer

External APIs plug into acquisition/discovery without replacing downstream scientific controls:

```text
explicit ICP / deterministic request
→ external API adapter
→ RAW PROVIDER RESPONSE AS EVIDENCE
→ provider-neutral structured observation
→ existing normalization / dedupe / verification / qualification
```

### Apify

The first provider implementation uses Apify's REST Actor API with the maintained Google Search Results Scraper by default.

```text
Actor = apify/google-search-scraper
Credential = APIFY_API_TOKEN environment variable
Token storage in Git = NO
Raw dataset evidence persistence = YES
CFO verification bypass = NO
Intent inference = NO
```

Dry query-plan smoke:

```bash
PYTHONPATH=. python scripts/run_apify_dental_discovery.py --dry-run --max-queries 4
```

Live bounded run:

```bash
APIFY_API_TOKEN=... PYTHONPATH=. python scripts/run_apify_dental_discovery.py \
  --max-queries 4 \
  --db searchleads-apify.db \
  --output apify-dental-candidates.json
```

See `EXTERNAL-API-PROVIDERS-V1.md`.

### Researched provider shortlist

Recommended order after Apify:

1. Brave Search API — fallback structured web discovery;
2. Google Places API — clinic/location/phone/website context;
3. Hunter API — email discovery and deliverability validation;
4. SerpAPI — optional Google-SERP redundancy.

Each provider is added only when it closes a concrete gap. No provider is allowed to silently become an authoritative credential source.

## Active dental batch

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

The evaluator safely keeps all unverified rows under review:

```text
ROWS=50 PREP_READY=0 SEND_READY=0 REVIEW=50 EXCLUDE=0
```

## Regulatory context

The application keeps professional/offer eligibility separate from campaign-send compliance. CFO-SEC-285/286 (2026 CEOF framework), the separate HOF litigation, and PDL 177/2026 are not collapsed into one automatic legal conclusion.

Actual sending defaults to:

```text
CampaignLegalStatus.PENDING_REVIEW
```

## Commands

Full regression:

```bash
python -m unittest discover -s tests -v
PYTHONPATH=. python scripts/run_end_to_end_acceptance.py
PYTHONPATH=. python scripts/evaluate_dental_verification_batch.py \
  DENTAL-CFO-VERIFICATION-BATCH-50.csv \
  --output /tmp/dental-batch-evaluated.csv
PYTHONPATH=. python scripts/run_live_brasilapi_smoke.py
```

External API provider tests are included in normal unittest discovery.

## Key documents

- `ICP-DENTAL-FACIAL-SURGERY-V1.md`
- `EXTERNAL-API-PROVIDERS-V1.md`
- `MVP-DENTAL-BATCH-50.md`
- `DENTAL-CFO-VERIFICATION-BATCH-50.csv`
- `DENTAL-CFO-VERIFICATION-WORKFLOW.md`
- `FULL-REGRESSION-REPORT-2026-08-22.md`
- `HANDOFF-AUDIT-CLOSURE.md`
