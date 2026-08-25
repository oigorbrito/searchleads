# searchleads

B2B lead discovery and enrichment project.

Current completed work units:

- `LEADS_SCIENTIFIC_FOUNDATION_AND_DOMAIN_V1`
- `LEADS_PERSISTENCE_AND_EVIDENCE_V1`

## Included

- Scientific foundation and bounded architecture principles.
- Company, Person, ContactPoint, and Lead domain entities.
- Source, Evidence, and fact-level Provenance.
- CandidateFact, CanonicalFact, and Conflict representation.
- SQLite persistence with typed lossless round-trip for supported values.
- Raw textual evidence preservation with storage-integrity checks.
- Deterministic evidence replay inputs for reprocessing.
- Executable invariants/tests.

## Run tests

```bash
python -m pytest
```

B2B remains provisional and no ICP is defined yet.
