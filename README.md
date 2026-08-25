# searchleads

B2B lead discovery and enrichment project.

Current clean work-unit stack:

- `LEADS_SCIENTIFIC_FOUNDATION_AND_DOMAIN_V1`
- `LEADS_PERSISTENCE_AND_EVIDENCE_V1`
- `LEADS_FIRST_REAL_SOURCE_V1`
- `COMPANY_NORMALIZATION_V1`
- `COMPANY_ENTITY_RESOLUTION_V1`

## Included

- Scientific foundation and bounded architecture principles.
- Company, Person, ContactPoint, and Lead domain entities.
- Source, Evidence, fact-level Provenance, CandidateFact, CanonicalFact, and Conflict.
- SQLite persistence with typed lossless round-trip for supported values.
- Raw textual evidence preservation with storage-integrity checks and deterministic replay.
- One narrow real-source adapter: BrasilAPI CNPJ v1 point lookup for a known CNPJ.
- BrasilAPI HTTP bodies are persisted before response interpretation or source-field extraction.
- Deterministic, non-destructive company-field normalization with explicit versioned rule IDs.
- Normalization replay from immutable persisted candidate facts without rewriting raw source values.
- Measured company entity resolution with transparent blocking, pairwise signals, calibration metrics, and conservative triage.
- Operational ER auto-matches only exact supported namespaced registry IDs; multi-signal similarity routes to review rather than irreversible merge.
- Executable invariants/tests.

## Deliberately not included yet

- crawling or full scans;
- broad company discovery;
- automatic fuzzy company merges or persisted merge execution;
- contact/person extraction from BrasilAPI;
- contact validation;
- ICP or qualification policy.

## Run tests

```bash
python -m pytest
```

B2B remains provisional and no ICP is defined yet.
