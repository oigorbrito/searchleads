# SearchLeads

B2B lead discovery and enrichment project following the supplied staged handoff.

Implemented work units:

1. `LEADS_SCIENTIFIC_FOUNDATION_AND_DOMAIN_V1`
2. `LEADS_PERSISTENCE_AND_EVIDENCE_V1`
3. `LEADS_FIRST_REAL_SOURCE_V1`

The project now has a minimal domain model, evidence-preserving SQLite persistence, and one deliberately narrow real-source adapter for the Minha Receita CNPJ API. The source path is:

```text
known CNPJ
→ Minha Receita JSON
→ raw Evidence
→ Company shell
→ source-derived CandidateFact records
→ SQLite persistence
```

The adapter does not create canonical facts, contacts, people, leads, or qualification decisions. It also does not implement the experimental paginated search endpoint; broad discovery remains a later concern.

## Run tests

```bash
python -m unittest discover -s tests -v
```
