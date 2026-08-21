# SearchLeads

B2B lead discovery and enrichment project following the supplied staged handoff.

Implemented work units:

1. `LEADS_SCIENTIFIC_FOUNDATION_AND_DOMAIN_V1`
2. `LEADS_PERSISTENCE_AND_EVIDENCE_V1`
3. `LEADS_FIRST_REAL_SOURCE_V1`
4. `COMPANY_NORMALIZATION_V1`
5. `COMPANY_ENTITY_RESOLUTION_V1`
6. `COMPANY_FIELD_FUSION_AND_TRUTH_DISCOVERY_V1`
7. `CONTACT_DISCOVERY_V1`
8. `CONTACT_VALIDATION_V1`
9. `PERSON_DISCOVERY_AND_COMPANY_LINK_V1`
10. `LEAD_QUALIFICATION_V1`
11. `LEADS_EXPANSION_V1`

The project now has evidence-preserving company acquisition, normalization, measured entity resolution, explicit field conflicts, professional contact discovery/validation, evidence-backed person/company role links, policy-required lead qualification, and controlled expansion from explicit CNPJ seeds.

## Run tests

```bash
python -m unittest discover -s tests -v
```

## Key V1 policies

- exact full registry/CNPJ equality may auto-match companies; fuzzy matching goes to review;
- only unanimous effective field values auto-canonicalize; disagreement remains a `Conflict`;
- contact discovery never implies validation;
- contact `VALIDATED` means official-publication corroboration, not deliverability;
- a `Person` is separate from a `Company`, and every `ProfessionalRole` requires provenance;
- no lead is qualified without explicit externally supplied criteria;
- expansion accepts explicit seeds, deduplicates them, skips already-persisted companies before acquisition, and reports failures per seed instead of turning into a crawler.

Measured ER and fusion benchmarks remain reproducible with:

```bash
python scripts/evaluate_entity_resolution.py
python scripts/evaluate_field_fusion.py
```
