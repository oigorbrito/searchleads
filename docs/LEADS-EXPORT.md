# Leads Export v1

## Work unit

`LEADS_EXPORT_V1`

This work unit adds an output boundary independent from discovery, acquisition, entity resolution, validation, review routing, and qualification. Export consumes an already-assembled coherent record and refuses to serialize a bundle whose ownership/evidence/provenance graph is internally inconsistent.

## Clean-stack export model

The legacy stack modeled role and qualification in separate helper records. The clean stack does not. WU12 therefore exports the actual current domain shape:

- one `Company`;
- optional `Lead`;
- zero or more `Person` observations;
- zero or more `ContactPoint` observations;
- `CandidateFact` records, including person role/title facts;
- `CanonicalFact` records;
- `Conflict` records;
- standalone `Provenance` records;
- `Source` records;
- `Evidence` records;
- optional WU11 `ReviewItem` records.

Qualification state and reasons live inside `Lead`. A Company remains exportable with `lead = null`, preserving `COMPANY != LEAD` while ICP is undefined.

## Integrity graph

Before any serialization, the exporter validates the following graph.

```text
Company
├─ optional Lead → same Company
├─ People → same Company
│  └─ relationship Evidence → exported Evidence
├─ Contacts → Company or exported Person
│  ├─ discovery Evidence → exported Evidence
│  └─ validation Evidence → exported Evidence
├─ CandidateFacts → Company or exported Person
│  ├─ Evidence → exported Evidence
│  └─ Provenance → same subject/field + exported Evidence
├─ CanonicalFacts → Company or exported Person
│  ├─ candidate IDs → exported CandidateFacts
│  └─ Provenance → same subject/field
├─ Conflicts → Company or exported Person
│  └─ candidate IDs → same subject/field CandidateFacts
├─ Provenances
│  ├─ Evidence → exported Evidence
│  └─ derived_from_fact_ids → exported CandidateFacts
├─ Evidence → exported Source
└─ ReviewItems → referenced Evidence exported
```

Duplicate IDs inside any exported record category are rejected rather than silently collapsed.

Company/Person aggregate child-ID snapshots are deliberately not treated as strict export foreign keys because the clean persistence model intentionally permits immutable aggregate snapshots while child records are appended separately.

## Deterministic JSON

`export_json()` emits compact UTF-8 JSON with:

- `schema_version = leads_export_v1`;
- explicit enum values;
- timezone-aware datetimes as ISO-8601 strings;
- bytes as `{ "encoding": "hex", "value": ... }`;
- record collections sorted by their stable IDs;
- mapping keys sorted;
- sets/frozensets deterministically ordered.

Non-string mapping keys, unsupported object values, naive datetimes, and non-finite floats are rejected rather than serialized ambiguously.

Changing the input tuple order does not change the JSON output.

## CSV

`export_csv()` emits one company/lead row. Scalar routing columns are exposed directly:

- schema version;
- company ID;
- optional lead ID;
- optional lead stage;
- optional qualification status.

Audit-heavy sections remain JSON cells instead of being destructively flattened:

- Company;
- People;
- Contacts;
- candidate/canonical facts and conflicts;
- Provenances;
- Sources;
- Evidence;
- ReviewItems.

This keeps CSV interoperable while retaining the evidence graph required for audit/replay.

## Curated integrity benchmark

A deterministic 15-scenario benchmark exercises both accepted and rejected bundles.

```text
SCENARIOS = 15
COHERENT_ACCEPTED = 3
FALSE_ACCEPT = 0
INCOHERENT_REJECTED = 12
FALSE_REJECT = 0
INTEGRITY_ACCEPT_PRECISION = 100.0%
INTEGRITY_REJECT_SPECIFICITY = 100.0%
```

Accepted scenarios cover a full coherent bundle, Company-without-Lead, and input-order changes. Rejected scenarios include cross-company ownership, missing Evidence/Source/Provenance links, fact/provenance mismatch, missing canonical candidates, conflict mismatch, missing review Evidence, and duplicate IDs.

These are curated contract metrics, not production data-quality prevalence estimates.

## Verification

```text
WU12_FOCUSED_TESTS = 29/29 PASS
WU12_MODULE_LINE_COVERAGE = 100%
WU12_MEASURED_STATEMENTS = 153
LEADS_EXPORT_INTEGRITY_BENCHMARK = PASS
PYTHON_MODULE_COMPILE = PASS
```

The implementation imports only contracts confirmed on the clean PR #52 head: `Company`, `Person`, `ContactPoint`, `Lead`, facts, `Provenance`, `Source`, `Evidence`, and WU11 `ReviewItem`. No domain or persistence schema change is required.

## Gates

```text
JSON_EXPORT = PASS
CSV_EXPORT = PASS
DETERMINISTIC_EXPORT = PASS
COMPANY_EXPORTABLE_WITHOUT_LEAD = YES
PERSON_ROLE_FACTS_EXPORT = PASS
CONTACT_EXPORT = PASS
FACTS_AND_CONFLICTS_EXPORT = PASS
PROVENANCE_EXPORT = PASS
EVIDENCE_EXPORT = PASS
REVIEW_ITEMS_EXPORT = PASS
EXPORT_GRAPH_INTEGRITY = PASS
DUPLICATE_IDS_REJECTED = YES
NONFINITE_FLOAT_EXPORT = REJECTED
NAIVE_DATETIME_EXPORT = REJECTED
UNSUPPORTED_VALUE_EXPORT = REJECTED
FOCUSED_TESTS = 29/29 PASS
LINE_COVERAGE_NEW_MODULE = 100%
ICP_DEFINED = NO
B2B_ASSUMPTION = PROVISIONAL
```

## Next work unit

Per the original handoff sequence after export: audit `GAP_DETECTION_AND_AUTOMATION_V1` before implementation.
