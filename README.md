# searchleads

B2B lead discovery and enrichment project.

Current clean work-unit stack:

- `LEADS_SCIENTIFIC_FOUNDATION_AND_DOMAIN_V1`
- `LEADS_PERSISTENCE_AND_EVIDENCE_V1`
- `LEADS_FIRST_REAL_SOURCE_V1`

## Included

- Scientific foundation and bounded architecture principles.
- Company, Person, ContactPoint, and Lead domain entities.
- Source, Evidence, fact-level Provenance, CandidateFact, CanonicalFact, and Conflict.
- SQLite persistence with typed lossless round-trip for supported values.
- Raw textual evidence preservation with storage-integrity checks and deterministic replay.
- One narrow real-source adapter: BrasilAPI CNPJ v1 point lookup for a known CNPJ.
- BrasilAPI HTTP bodies are persisted before response interpretation or source-field extraction.
- Executable invariants/tests.

## Deliberately not included yet

- crawling or full scans;
- broad company discovery;
- company normalization/entity-resolution algorithms;
- contact/person extraction from BrasilAPI;
- contact validation;
- ICP or qualification policy.

## Run tests

```bash
python -m pytest
```

B2B remains provisional and no ICP is defined yet.
