# SearchLeads

B2B lead discovery and enrichment project following the supplied staged handoff.

Implemented work units:

1. `LEADS_SCIENTIFIC_FOUNDATION_AND_DOMAIN_V1`
2. `LEADS_PERSISTENCE_AND_EVIDENCE_V1`
3. `LEADS_FIRST_REAL_SOURCE_V1`
4. `COMPANY_NORMALIZATION_V1`

The project now has a minimal domain model, evidence-preserving SQLite persistence, one deliberately narrow real-source adapter for the BrasilAPI CNPJ API, and deterministic non-destructive company-field normalization. The source path is:

```text
known CNPJ
→ BrasilAPI JSON
→ raw Evidence
→ Company shell
→ source-derived CandidateFact records
→ SQLite persistence
```

The adapter does not create canonical facts, contacts, people, leads, or qualification decisions. It performs only point lookup by known CNPJ. It does not crawl or full-scan BrasilAPI; broad discovery remains a later concern.

Normalization is a projection over raw `CandidateFact` records. It preserves `raw_value`, emits `normalized_value` plus an explicit `normalization_rule`, and can be recomputed from persisted facts without rewriting source evidence.

## Run tests

```bash
python -m unittest discover -s tests -v
```
