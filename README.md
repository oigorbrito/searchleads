# SearchLeads

B2B lead discovery and enrichment project following the supplied staged handoff.

## Handoff roadmap status

Implemented:

1. `LEADS_SCIENTIFIC_FOUNDATION_AND_DOMAIN_V1`
2. `LEADS_PERSISTENCE_AND_EVIDENCE_V1`
3. `LEADS_FIRST_REAL_SOURCE_V1`
4. `COMPANY_NORMALIZATION_V1`
5. `COMPANY_ENTITY_RESOLUTION_V1`
6. `COMPANY_ENRICHMENT_V1`
7. `CONTACT_DISCOVERY_V1`
8. `PERSON_AND_ROLE_DISCOVERY_V1`
9. `CONTACT_VALIDATION_V1`
10. `REPEATABLE_WEB_DISCOVERY_V1`
11. `LEAD_QUALIFICATION_V1` engine — implemented, but the real business gate remains blocked because `ICP_DEFINED = NO`.
12. `SELECTIVE_REVIEW_V1`
13. `LEADS_EXPORT_V1`
14. `GAP_DETECTION_AND_AUTOMATION_V1` — bounded planning over known capabilities; no generic scheduler.

Additional measured capabilities implemented during the staged work:

- conservative field fusion / truth-discovery diagnostics;
- controlled CNPJ-seed expansion.

Still pending from the original handoff: Work Unit 15 acceptance.

## Core V1 policies

- `Company != Lead`;
- raw evidence is preserved and facts carry provenance;
- exact full registry/CNPJ equality may auto-match companies; fuzzy matching goes to review;
- only unanimous effective field values auto-canonicalize; disagreement remains a `Conflict`;
- company enrichment exercises two independent sources for the same real company;
- known-source discovery uses a versioned deterministic recipe and does not invoke an LLM per page;
- contact discovery never implies validation;
- contact `VALIDATED` means official-publication corroboration, not deliverability;
- every `ProfessionalRole` requires explicit evidence linking Person, Company and title;
- no lead is qualified without an explicit externally supplied policy/ICP;
- ambiguous/high-impact cases can be routed selectively to human review;
- export is independent and validates that Company, People, Contacts, Facts, Evidence and provenance belong to one coherent record;
- gap automation only selects implemented known capabilities, blocks unknown sources, and represents bounded retry/cache/rate-limit metadata;
- controlled expansion is seed-driven and is not a crawler.

## Run tests

```bash
python -m unittest discover -s tests -v
```

Measured ER and fusion benchmarks:

```bash
python scripts/evaluate_entity_resolution.py
python scripts/evaluate_field_fusion.py
```
