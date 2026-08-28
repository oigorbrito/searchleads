# searchleads

B2B lead discovery and enrichment with fact-level provenance and explicit validation boundaries.

## Architecture

DISCOVERY → ACQUISITION → EVIDENCE → STRUCTURED EXTRACTION → NORMALIZATION → ENTITY RESOLUTION → ENRICHMENT/FUSION → QUALIFICATION → EXPORT

Cross-cutting concerns: PROVENANCE / VALIDATION / CONFIDENCE / REVIEW.

## Scientific invariants

- Company is not a Lead.
- Found is not Valid.
- Name match is not entity match.
- Contact found is not contact valid.
- A value without Evidence is not a verified fact.
- Discovery success is not coverage.
- Provenance is fact-level.
- ICP, score, geography, company size, job titles and qualification criteria must not be invented.

## Work units

Current branch establishes `LEADS_SCIENTIFIC_FOUNDATION_AND_DOMAIN_V1` with immutable domain values and unit tests for the core invariants.

Qualification remains blocked while ICP is undefined.
