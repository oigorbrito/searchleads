# Work Unit 6 Report — COMPANY_ENRICHMENT_V1

This report closes the original handoff Work Unit 6, which requires a second source for an already-identified company.

## Real company exercised

Regional Brasília / SERPRO:

- company key: `company:cnpj:33683111000280`
- registry ID: `33.683.111/0002-80`

Source 1: BrasilAPI CNPJ adapter.

Source 2: official Serpro institutional/transparency location page.

The official page was independently verified on 2026-08-21 as publishing the Brasília regional CNPJ, address, city/state, CEP and activity-start information.

## Pipeline exercised

```text
BrasilAPI evidence
+
official Serpro HTML evidence
→ same Company
→ CandidateFact sets
→ normalization where defined
→ per-field fusion / explicit conflict
```

## Observed behavior

Overlapping fields:

- `business_registry_id`: two-source agreement → canonicalizable
- `state`: two-source agreement (`DF`) → canonicalizable
- `city`: `BRASILIA` vs `Brasília` → remains explicit conflict under the conservative V1 location normalizer

New enrichment fields from the second source:

- `street_address`
- `postal_code`
- `activity_start_date`

The city spelling difference is intentionally not hidden by new normalization semantics in this work unit.

## Validation

`python -m unittest discover -s tests -v`

- `TESTS_DISCOVERED = 126`
- `TESTS_EXECUTED = 126`
- `TESTS_PASSED = 126`

## Gates

- `SECOND_REAL_SOURCE = YES`
- `SAME_COMPANY_MULTI_SOURCE = YES`
- `RAW_EVIDENCE_PER_SOURCE = PASS`
- `MULTI_SOURCE_PROVENANCE = PASS`
- `ENRICHMENT_NEW_FIELDS = PASS`
- `CONFLICT_PRESERVATION = PASS`
- `MULTI_SOURCE = YES`
- `ICP_DEFINED = NO`
- `B2B_ASSUMPTION = PROVISIONAL`

## Decision classification

- Official-page adapter and regex extraction: `ENGINEERING_CHOICE`.
- Treating the official page as independent evidence from BrasilAPI: `LOCALLY_VERIFIED` source distinction.
- Not resolving `BRASILIA` vs `Brasília` automatically: `ENGINEERING_CHOICE` consistent with existing normalization boundaries.
- No source-authority ranking: `UNKNOWN` / deliberately not invented.
