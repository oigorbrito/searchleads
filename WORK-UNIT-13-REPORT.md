# Work Unit 13 Report — LEADS_EXPORT_V1

## Scope

Adds an output boundary independent from discovery/acquisition. Export consumes already-assembled domain records and refuses internally inconsistent bundles.

## Exportable record

`LeadExportBundle` represents:

- Company
- optional Lead status
- People
- ProfessionalRole links
- Contacts
- CandidateFact records
- CanonicalFact records
- Conflicts
- Sources
- Evidence
- Qualification result

## Formats

### JSON

Deterministic, UTF-8-safe JSON with sorted keys. Dates become ISO-8601 strings and enums become their explicit values.

### CSV

One independent company/lead row. Nested audit structures (people, roles, contacts, facts/conflicts, sources, evidence, qualification) are JSON-encoded within named cells so provenance is not discarded by flattening.

## Integrity checks before export

The exporter rejects:

- Lead or Qualification belonging to another Company;
- roles pointing outside the exported company/person set;
- contacts owned by another company or a non-exported person;
- facts/conflicts belonging to another entity;
- Evidence whose Source is omitted;
- provenance references whose Evidence is omitted.

A Company may be exported with `lead = null` and `qualification = null`; this is required while the real ICP is undefined and preserves `Company != Lead`.

## Validation

`python -m unittest discover -s tests -v`

- `TESTS_DISCOVERED = 147`
- `TESTS_EXECUTED = 147`
- `TESTS_PASSED = 147`

## Gates

- `JSON_EXPORT = PASS`
- `CSV_EXPORT = PASS`
- `COMPANY_EXPORTABLE_WITHOUT_LEAD = YES`
- `PEOPLE_EXPORT = PASS`
- `CONTACT_EXPORT = PASS`
- `FACTS_AND_CONFLICTS_EXPORT = PASS`
- `EVIDENCE_EXPORT = PASS`
- `PROVENANCE_EXPORT = PASS`
- `QUALIFICATION_EXPORT = PASS`
- `EXPORT_INTEGRITY_VALIDATION = PASS`
- `EXPORT = PASS`

## Classification

JSON/CSV shapes and bundle-integrity checks are `ENGINEERING_CHOICE`. The inclusion of evidence/provenance and separation of Company from Lead follow the `EVIDENCE_BACKED` architecture in the supplied handoff.
