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
15. `END_TO_END_ACCEPTANCE_V1` — technical pipeline accepted; real commercial qualification remains blocked by undefined ICP.

Additional measured capabilities implemented during the staged work:

- conservative field fusion / truth-discovery diagnostics;
- controlled CNPJ-seed expansion;
- `ICP_DECISION_SUPPORT_V1`, which measures readiness of the eight handoff ICP dimensions without defining target values or a default policy;
- `QUALIFICATION_EVIDENCE_SIGNALS_V1`, which adds explicit exclusion operators and evidence-backed role/contact qualification inputs without defining an ICP.

## Final V1 acceptance state

```text
TECHNICAL_END_TO_END_ACCEPTANCE = PASS
ICP_DEFINED = NO
REAL_QUALIFICATION = NOT_EVALUABLE
COMMERCIAL_END_TO_END_ACCEPTANCE = BLOCKED_BY_UNDEFINED_ICP
```

The deterministic SERPRO acceptance run passes real-company discovery, multi-source enrichment, exact-CNPJ entity resolution/deduplication, provenance, contact discovery/corroboration, person/role extraction, selective review, export, and bit-reproducibility. A synthetic acceptance-only qualification policy proves the engine composes, but is never represented as the product ICP.

## ICP decision-support state

Baseline against the accepted full-run:

```text
ICP_DIMENSIONS = 8
READY = 0
PARTIAL = 6
BLOCKED = 2
ICP_DEFINED = NO
```

After the qualification evidence-signal bridge:

```text
READY = 2
PARTIAL = 4
BLOCKED = 2
EXCLUSION_CRITERIA = READY
TARGET_ROLE = READY
REQUIRED_CONTACTABILITY = PARTIAL
```

Contactability remains partial because officially corroborated contact presence is still not deliverability/reachability. This is readiness measurement, not an ICP. See `ICP-DECISION-SUPPORT-V1.md`, `QUALIFICATION-EVIDENCE-SIGNALS-V1.md`, and run `python scripts/run_icp_decision_support.py`.

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
- no real lead is qualified without an explicit externally supplied policy/ICP;
- qualification exclusions are explicit operators, not opaque score penalties;
- validated contacts and professional roles enter qualification only as typed evidence-backed inputs, not as invented company facts;
- ambiguous/high-impact cases can be routed selectively to human review;
- export is independent and validates that Company, People, Contacts, Facts, Evidence and provenance belong to one coherent record;
- gap automation only selects implemented known capabilities, blocks unknown sources, and represents bounded retry/cache/rate-limit metadata;
- controlled expansion is seed-driven and is not a crawler.

## Validation

```bash
python -m unittest discover -s tests -v
python scripts/run_end_to_end_acceptance.py
python scripts/run_icp_decision_support.py
```

Measured ER and fusion benchmarks:

```bash
python scripts/evaluate_entity_resolution.py
python scripts/evaluate_field_fusion.py
```
