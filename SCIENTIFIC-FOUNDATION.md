# Scientific Foundation — Leads V1

## Scope

This document records the scientific baseline supplied by the project handoff for `LEADS_SCIENTIFIC_FOUNDATION_AND_DOMAIN_V1`. It does **not** independently re-verify or extend the papers. Claims below are intentionally limited to what the handoff states.

## Decision vocabulary

Every material design statement should be classified as one of:

- `EVIDENCE_BACKED`
- `HYPOTHESIS`
- `ENGINEERING_CHOICE`
- `LOCALLY_VERIFIED`
- `UNKNOWN`

`HYPOTHESIS` must never be presented as `EVIDENCE_BACKED`.

## Baseline references and allowed conclusions

| Reference | Handoff-supported relevance | Classification |
| --- | --- | --- |
| SODIUM — arXiv:2603.18447 | Open-web discovery plus structured database generation is multi-stage; structure/reuse can improve acquisition. Does not select crawler, DB, ICP, or require cloning SODIUM. | `EVIDENCE_BACKED` |
| WebLists — arXiv:2504.12682 | Interactive extraction can be discovered and then reused; motivates “discover once, reuse many times.” | `EVIDENCE_BACKED` direction |
| WideSearch — arXiv:2508.07999 | Finding some results is not equivalent to coverage; recall/coverage is a future discovery metric. | `EVIDENCE_BACKED` |
| WANDR — arXiv:2608.14747 | Wide discovery + deep investigation + evidence-backed records strongly resembles lead enrichment workflow. | `EVIDENCE_BACKED` direction |
| WebDS — arXiv:2508.01222 | Browser navigation competence alone is insufficient; selection should prioritize data-acquisition quality. | `EVIDENCE_BACKED` |
| MaDI-Bench — arXiv:2606.30371 | Data integration decomposes into schema matching, normalization, blocking, entity matching, fusion, conflict resolution. | `EVIDENCE_BACKED` / core architectural evidence |
| Automatic End-to-End Data Integration using LLMs — arXiv:2603.10547 | LLMs can help produce mappings/configuration/training artifacts while conventional components execute the pipeline. | `EVIDENCE_BACKED` direction |
| Fast Record Linkage for Company Entities — arXiv:1907.08667 | Company entity resolution is a distinct measurable problem; company name alone is insufficient identity. | `EVIDENCE_BACKED` |
| CompanyName2Vec — arXiv:2201.04687 | Company name matching is relevant to enrichment/sales/marketing; name match is not entity match. | `EVIDENCE_BACKED` direction |
| ComEM — ACL 2025.coling-main.8 | Candidate-set/context-aware matching may outperform isolated pair decisions in some settings. Applying it here remains unvalidated. | `HYPOTHESIS` for local application |
| ALER — PVLDB 2026, DOI 10.14778/3811243.3811251 | Active learning supports selective review of ambiguous/high-impact/informative entity-resolution cases. | `EVIDENCE_BACKED` direction |
| PARSE — ACL 2025.emnlp-industry.184 | Entity extraction should be schema-constrained and validated rather than arbitrary JSON. | `EVIDENCE_BACKED` direction |
| W3C PROV / PROV-O | Provenance concepts support answering where a fact came from, when, and through which activity/agent. | `EVIDENCE_BACKED` standard |

## Logical architecture supported by the handoff

```text
DISCOVERY
↓
ACQUISITION
↓
EVIDENCE
↓
STRUCTURED EXTRACTION
↓
NORMALIZATION
↓
ENTITY RESOLUTION
↓
ENRICHMENT / FUSION
↓
QUALIFICATION
↓
EXPORT
```

Cross-cutting concerns:

```text
PROVENANCE
VALIDATION
CONFIDENCE
REVIEW
```

## Non-negotiable distinctions

- `COMPANY ≠ LEAD`
- `FOUND ≠ VALID`
- `NAME MATCH ≠ ENTITY MATCH`
- `CONTACT FOUND ≠ CONTACT VALID`
- `VALUE WITHOUT EVIDENCE ≠ VERIFIED FACT`
- `DISCOVERY SUCCESS ≠ DISCOVERY COVERAGE`

## Current domain hypothesis

`B2B` is `HYPOTHESIS` / `PROVISIONAL`, not a finalized market requirement.

The following remain `UNKNOWN` and are not implemented as requirements here:

- final ICP
- industry/segment
- geography
- company size
- target role
- exclusion criteria
- priority channel
- qualification weights
- contact-validation method
