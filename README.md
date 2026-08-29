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
- `GAP_DETECTION_AND_AUTOMATION_V1`
- `END_TO_END_ACCEPTANCE_V1`
- `MULTI_SOURCE_COMPANY_ENRICHMENT_V1`
- `GAP_CAPABILITY_RECONCILIATION_V1`
- `DISCOVERY_COVERAGE_MEASUREMENT_V1`
- `PERSON_ENTITY_RESOLUTION_V1`
- `DENTAL_ICP_POLICY_CONTRACT_V1`
- `DENTAL_COMMERCIAL_QUALIFICATION_V1`

Current persistence/domain hardening stack (draft, stacked after the clean work units above):

- `UNIFIED_MEASUREMENT_AND_TELEMETRY_V1`
- `SQLITE_SCHEMA_MIGRATIONS_V2`
- `QUALIFICATION_DECISION_INVARIANTS_V1`
- `FACT_PROVENANCE_REFERENCE_INVARIANTS_V1`
- `CONTACT_LEAD_STATE_INVARIANTS_V1`
- `PERSISTENCE_SEMANTIC_REFERENCE_INVARIANTS_V1`
- `MIGRATION_LEDGER_REPAIR_V2`
- `PERSISTENCE_IMPORT_BOUNDARY_V1`
- `PERSISTENCE_CONTRACT_DOCS_V2`

`docs/ARCHITECTURE-PRINCIPLES.md` records the architecture incrementally as work units were introduced. Its early `Deferred decisions` section is historical: later clean work units have already implemented schema migration, contact validation, export, and the first approved vertical ICP/qualification contract. Current capability status is defined by the complete stack and the most recent capability-specific documents, not by those historical deferrals in isolation.

## Included

- Scientific foundation and bounded architecture principles.
- Company, Person, ContactPoint, and Lead domain entities.
- Source, Evidence, fact-level Provenance, CandidateFact, CanonicalFact, and Conflict.
- SQLite persistence with typed lossless round-trip for supported values.
- Raw textual evidence preservation with storage-integrity checks and deterministic replay.
- Explicit SQLite schema v1-to-v2 migration, additive repair, migration ledger, and domain-record integrity hashing.
- Public persistence layering that combines base SQLite storage, semantic fact-reference validation, and current-version migration-ledger repair.
- A guarded runtime import boundary requiring persistence consumers to use `searchleads.persistence` rather than implementation modules directly.
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
- Bounded source-page discovery coverage measurement against an explicit 12-block CNPJ-labelled SERPRO reference population; missed, unexpected, and duplicate seed behavior is reported separately and no market-wide recall is claimed.
- Measured cross-observation Person ER triage over explicit evidence-linked name, role and person-contact signals; a profile+name auto-match candidate is diagnostic only because the adversarial benchmark shows non-zero false-merge risk.
- Selective review routing for already-explicit ambiguity/conflict states; obvious/terminal cases are excluded, human-readable reasons are required, duplicate review work is consolidated, and no opaque review score is introduced.
- Deterministic JSON and one-row CSV export of a coherent company/lead audit bundle, with explicit cross-record integrity checks and provenance/evidence preservation.
- Explicit-requirement gap detection with bounded plans that select only implemented clean-stack capabilities, including WU15 official-location enrichment for address/postal/activity-start gaps when an explicit CNPJ is available; missing inputs or unknown sources remain blocked.
- Deterministic end-to-end technical acceptance over the published clean-stack APIs, including Evidence replay and byte-identical export reproduction across fresh runs.
- A second narrow company source for already-identified SERPRO entities: the official transparency address page, preserving raw Evidence and adding address/postal/activity-start observations without source-authority ranking.
- A versioned first vertical ICP policy contract for the already-documented Brazil dental facial-surgery education target; the commercial target is `Person`, company size is not an applicable criterion, and missing/conflicting required evidence remains `UNKNOWN/REVIEW`.
- Evidence-backed Person-centered dental commercial qualification that consumes exactly the approved policy contract, keeps FIT and INTENT separate, preserves `UNKNOWN` under missing/conflicting required evidence, materializes deterministic company-linked Lead wrappers, and keeps CFO/compliance/live-network gates separate.
- Executable invariants/tests.

## Deliberately not included yet

- generic crawling or full scans;
- broad/unbounded company discovery;
- market-wide or web-wide discovery coverage claims;
- automatic fuzzy company merges or persisted merge execution;
- source-authority weights or learned truth discovery;
- automatic persisted Person merges/splits;
- mailbox deliverability, phone reachability, or social-account-control validation;
- a universal project-wide ICP applicable to every vertical;

## Run tests

```bash
python -m pytest
```

GitHub Actions is configured for Python 3.11, 3.12, and 3.13 with `compileall` and pytest. At the current repository/account state, Actions jobs are terminating before any workflow step is provisioned, so no current CI PASS is claimed until steps execute.

The generic core B2B assumption remains provisional. The first approved vertical ICP is the documented Brazil dental facial-surgery education policy; the clean-stack engine now evaluates that policy with evidence-linked Person-centered decisions. Qualification does not certify current CFO registration, campaign legal/compliance status, contact reachability, or live-network acquisition; those remain separate gates.
