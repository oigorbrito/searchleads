# SearchLeads Scientific Foundation v1

## Work unit

`LEADS_SCIENTIFIC_FOUNDATION_AND_DOMAIN_V1`

This document records the scientific baseline supplied in the project handoff. It intentionally does not perform new horizontal research and does not extrapolate the cited works beyond the conclusions recorded in that handoff.

## Evidence-backed logical direction

The project treats B2B lead discovery and enrichment as a multi-stage data acquisition/integration problem:

`DISCOVERY → ACQUISITION → EVIDENCE → STRUCTURED EXTRACTION → NORMALIZATION → ENTITY RESOLUTION → ENRICHMENT/FUSION → QUALIFICATION → EXPORT`

`PROVENANCE`, `VALIDATION`, `CONFIDENCE`, and selective `REVIEW` are cross-cutting concerns.

### Baseline references and bounded conclusions

| Reference | Baseline use in SearchLeads | Classification |
| --- | --- | --- |
| SODIUM, arXiv:2603.18447 | Open-web acquisition to structured/queryable data is multi-stage; structure/reuse can improve acquisition. | EVIDENCE_BACKED |
| WebLists, arXiv:2504.12682 | Prefer discovering an extraction procedure once and reusing it over reinterpreting equivalent pages forever. | EVIDENCE_BACKED direction |
| WideSearch, arXiv:2508.07999 | Discovery success is not discovery coverage; recall/coverage must eventually be measured. | EVIDENCE_BACKED |
| WANDR, arXiv:2608.14747 | Wide discovery + deep investigation + evidence-backed records maps naturally to lead enrichment. | EVIDENCE_BACKED direction |
| WebDS, arXiv:2508.01222 | Browser navigation success is not sufficient; data acquisition quality is the criterion. | EVIDENCE_BACKED direction |
| MaDI-Bench, arXiv:2606.30371 | Data integration decomposes into schema matching, normalization, blocking, entity matching, fusion, and conflict resolution. | EVIDENCE_BACKED |
| Automatic End-to-End Data Integration using LLMs, arXiv:2603.10547 | LLMs may assist mappings/configuration/ambiguity while traditional components execute repeatable stages. | EVIDENCE_BACKED direction |
| Fast Record Linkage for Company Entities, arXiv:1907.08667 | Company entity resolution is a distinct measurable problem; company name alone is insufficient identity. | EVIDENCE_BACKED |
| CompanyName2Vec, arXiv:2201.04687 | Company-name variation is an entity-matching problem relevant to enrichment/sales/marketing. | EVIDENCE_BACKED direction |
| ComEM, COLING 2025 | Candidate-set/context-aware matching may help company ER. | HYPOTHESIS until locally validated |
| ALER, PVLDB 2026 | Selective review should prioritize ambiguous/high-impact ER cases rather than review everything. | EVIDENCE_BACKED direction |
| PARSE, EMNLP 2025 Industry | Extraction should be schema-constrained and validated rather than arbitrary JSON. | EVIDENCE_BACKED direction |
| W3C PROV / PROV-O | Facts should preserve derivation/origin/process metadata. | EVIDENCE_BACKED standard basis |

## Non-negotiable invariants

- `COMPANY ≠ LEAD`
- `FOUND ≠ VALID`
- `NAME MATCH ≠ ENTITY MATCH`
- `CONTACT FOUND ≠ CONTACT VALID`
- `VALUE WITHOUT EVIDENCE ≠ VERIFIED FACT`
- `DISCOVERY SUCCESS ≠ DISCOVERY COVERAGE`

## Domain hypothesis

`B2B` is provisional and classified as `HYPOTHESIS`. No final ICP, target industry, geography, company size, role, or channel is defined in this work unit.

## What this foundation does not decide

It does not choose a crawler, database, company-matching weights, contact-validation method, qualification score, ICP, or universal extraction framework. Those remain future work and must be classified according to evidence/local validation when introduced.
