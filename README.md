# searchleads

B2B lead discovery and enrichment project.

Current clean work-unit stack:

- `LEADS_SCIENTIFIC_FOUNDATION_AND_DOMAIN_V1`
- `LEADS_PERSISTENCE_AND_EVIDENCE_V1`
- `LEADS_FIRST_REAL_SOURCE_V1`
- `COMPANY_NORMALIZATION_V1`
- `COMPANY_ENTITY_RESOLUTION_V1`
- `COMPANY_FIELD_FUSION_AND_TRUTH_DISCOVERY_V1`
- `CONTACT_DISCOVERY_V1`
- `PERSON_AND_ROLE_DISCOVERY_V1`
- `CONTACT_VALIDATION_V1`
- `REPEATABLE_WEB_DISCOVERY_V1`
- `SELECTIVE_REVIEW_V1`
- `LEADS_EXPORT_V1`

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
- Evidence-preserving company contact discovery for e-mail, phone, WhatsApp, contact forms, LinkedIn company profiles, and Instagram profiles; all remain `DISCOVERED`.
- Evidence-backed Person observations linked to a known Company, with name/title CandidateFacts and locally associated professional contacts; same-name observations are never merged at discovery time.
- Conservative contact validation by independent persisted page-observation corroboration; validated publication association remains distinct from deliverability or reachability.
- One versioned known-source web-discovery recipe for the official SERPRO office directory; raw discovery Evidence and discovered CNPJ seeds are preserved for deterministic replay and downstream structured acquisition.
- Selective review routing for already-explicit ambiguity/conflict states; obvious/terminal cases are excluded, human-readable reasons are required, duplicate review work is consolidated, and no opaque review score is introduced.
- Deterministic JSON and one-row CSV export of a coherent company/lead audit bundle, with explicit cross-record integrity checks and provenance/evidence preservation.
- Executable invariants/tests.

## Deliberately not included yet

- generic crawling or full scans;
- broad/unbounded company discovery;
- automatic fuzzy company merges or persisted merge execution;
- source-authority weights or learned truth discovery;
- cross-observation Person entity resolution or automatic person merges;
- mailbox deliverability, phone reachability, or social-account-control validation;
- ICP or qualification policy.

## Run tests

```bash
python -m pytest
```

B2B remains provisional and no ICP is defined yet.
