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

The project now has a minimal domain model, evidence-preserving SQLite persistence, one deliberately narrow real-source adapter for the BrasilAPI CNPJ API, deterministic company normalization, measured entity resolution, explicit field conflicts, professional contact discovery, and non-invasive official-publication contact validation.

## Run tests

```bash
python -m unittest discover -s tests -v
```

## Entity resolution V1

`COMPANY_ENTITY_RESOLUTION_V1` adds a transparent pairwise matcher, blocking keys, a curated 54-pair benchmark, threshold sweeps, and an operational triage policy. Exact registry/CNPJ equality may auto-match; fuzzy multi-signal evidence is routed to review rather than irreversible merge.

```bash
python scripts/evaluate_entity_resolution.py
```

## Field fusion V1

`COMPANY_FIELD_FUSION_AND_TRUTH_DISCOVERY_V1` canonicalizes only unanimous effective values. Disagreements remain open `Conflict` records; majority support is diagnostic only.

```bash
python scripts/evaluate_field_fusion.py
```

## Contact discovery and validation V1

`CONTACT_DISCOVERY_V1` preserves a company contact page as evidence and extracts professional e-mail, phone, contact-form, LinkedIn, and Instagram observations. Discovered contacts remain `DISCOVERED`.

`CONTACT_VALIDATION_V1` may create a separate `VALIDATED` snapshot only when the same contact is corroborated by at least two official page observations (or a strictly later official snapshot of the same page). This validates official publication/association only. Mailbox deliverability and phone reachability remain explicitly unverified.
