# SearchLeads

B2B lead discovery and enrichment project following the supplied staged handoff.

Implemented work units:

1. `LEADS_SCIENTIFIC_FOUNDATION_AND_DOMAIN_V1`
2. `LEADS_PERSISTENCE_AND_EVIDENCE_V1`

The project now has a minimal domain model plus SQLite-backed persistence for companies, people, contact points, sources, raw evidence, candidate facts, canonical facts, and conflicts. Raw evidence is preserved independently from normalized/canonical facts and can be reopened for reprocessing.

It still intentionally stops before real-source acquisition, normalization algorithms, entity-resolution scoring, contact validation, qualification scoring, exports, scheduling, or any universal framework.

## Run tests

```bash
python -m unittest discover -s tests -v
```
