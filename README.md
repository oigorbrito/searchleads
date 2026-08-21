# SearchLeads

Evidence-preserving lead discovery, enrichment, entity-resolution and qualification pipeline.

## Current status

The generic technical pipeline is implemented as a stacked draft-PR series. The first real commercial ICP is now explicitly defined for dental facial-surgery education.

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
REAL_DENTAL_COHORT_QUALIFICATION = PENDING
COMMERCIAL_END_TO_END_ACCEPTANCE = PENDING_REAL_DENTAL_COHORT

MAIN_INTEGRATION = NOT_DONE
```

See `ICP-DENTAL-FACIAL-SURGERY-V1.md` for the business definition and `HANDOFF-AUDIT-CLOSURE.md` for the earlier strict technical audit.

## ICP V1

Target market:

- Brazil-wide, with optional region/state filters;
- general dentists are eligible;
- Bucomaxilofacial and HOF profiles are eligible and typically higher FIT;
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

## Original roadmap capabilities

1. scientific/domain foundation
2. persistence/evidence
3. first structured company source
4. normalization
5. company entity resolution
6. company enrichment/fusion
7. contact discovery
8. person/role discovery
9. contact validation
10. repeatable web discovery
11. qualification engine and now explicit dental ICP MVP
12. selective review
13. export
14. bounded gap execution/reassessment
15. deterministic technical E2E acceptance

Additional capabilities include controlled expansion, Person Entity Resolution, qualification evidence bridges and registry-size evidence.

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

For MVP speed, the dental vertical intentionally uses a small focused suite covering only high-cost qualification errors rather than exhaustive edge cases.

## Commands

Focused dental MVP qualification:

```bash
python -m unittest tests.test_dental_facial_surgery_icp -v
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
- disagreement remains an explicit conflict;
- contact validation does not claim deliverability;
- FIT and INTENT remain explainable and separate;
- missing evidence becomes `UNKNOWN`, not an invented conclusion;
- gap execution remains bounded and uses known capabilities only.
