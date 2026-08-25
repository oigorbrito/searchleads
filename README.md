# searchleads

B2B lead discovery and enrichment project.

Current clean work-unit stack:

- `LEADS_SCIENTIFIC_FOUNDATION_AND_DOMAIN_V1`
- `LEADS_PERSISTENCE_AND_EVIDENCE_V1`
- `LEADS_FIRST_REAL_SOURCE_V1`
- `COMPANY_NORMALIZATION_V1`
- `COMPANY_ENTITY_RESOLUTION_V1`
- `COMPANY_FIELD_FUSION_AND_TRUTH_DISCOVERY_V1`

## Included

- Scientific foundation and bounded architecture principles.
- Company, Person, ContactPoint, and Lead domain entities.
- Source, Evidence, fact-level Provenance, CandidateFact, CanonicalFact, and Conflict.
- SQLite persistence with typed lossless round-trip for supported values.
- Raw textual evidence preservation with storage-integrity checks and deterministic replay.
- One narrow real-source adapter: BrasilAPI CNPJ v1 point lookup for a known CNPJ.
- Deterministic, non-destructive company-field normalization.
- Measured company entity resolution with conservative operational triage.
- Conservative company-field fusion: unanimous effective values may produce a CanonicalFact; disagreement remains an explicit open Conflict.
- Derived canonical facts receive a new fusion Provenance that unions evidence and records all parent candidate fact IDs.
- Majority/support ratios are diagnostics only and have no truth-selection authority in V1.
- Executable invariants/tests.

## Deliberately not included yet

- crawling or full scans;
- broad company discovery;
- automatic fuzzy company merges or persisted merge execution;
- source-authority weights or learned truth discovery;
- contact/person extraction from BrasilAPI;
- contact validation;
- ICP or qualification policy.

## Run tests

```bash
python -m pytest
```

B2B remains provisional and no ICP is defined yet.
