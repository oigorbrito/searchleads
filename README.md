# SearchLeads

B2B lead discovery and enrichment project following the supplied staged handoff.

## Strict handoff status

The technical architecture is implemented as a stacked draft-PR series, but the repository does **not** claim literal completion of gates that require unavailable external/business inputs.

```text
ARCHITECTURAL_DIRECTION = ALIGNED
TECHNICAL_END_TO_END_ACCEPTANCE = PASS
PERSON_ENTITY_RESOLUTION = IMPLEMENTED_V1
WU14_EXECUTION_REASSESSMENT = IMPLEMENTED_V1
WU3_LIVE_HTTP = PENDING_EXTERNAL_SMOKE
ICP_DEFINED = NO
REAL_QUALIFICATION = NOT_EVALUABLE
COMMERCIAL_END_TO_END_ACCEPTANCE = BLOCKED_BY_UNDEFINED_ICP
MAIN_INTEGRATION = NOT_DONE
```

See [`HANDOFF-AUDIT-CLOSURE.md`](HANDOFF-AUDIT-CLOSURE.md) for the strict work-unit-by-work-unit audit.

## Original roadmap capabilities

1. `LEADS_SCIENTIFIC_FOUNDATION_AND_DOMAIN_V1`
2. `LEADS_PERSISTENCE_AND_EVIDENCE_V1`
3. `LEADS_FIRST_REAL_SOURCE_V1` — adapter implemented; literal live HTTP smoke still pending in an environment with outbound DNS/HTTPS.
4. `COMPANY_NORMALIZATION_V1`
5. `COMPANY_ENTITY_RESOLUTION_V1`
6. `COMPANY_ENRICHMENT_V1`
7. `CONTACT_DISCOVERY_V1`
8. `PERSON_AND_ROLE_DISCOVERY_V1`
9. `CONTACT_VALIDATION_V1`
10. `REPEATABLE_WEB_DISCOVERY_V1`
11. `LEAD_QUALIFICATION_V1` engine — business execution remains blocked by undefined ICP.
12. `SELECTIVE_REVIEW_V1`
13. `LEADS_EXPORT_V1`
14. `GAP_DETECTION_AND_AUTOMATION_V1` — bounded plan → execute → retry/cache/rate-limit/schedule → reassess loop over known capabilities.
15. `END_TO_END_ACCEPTANCE_V1` — technical composition accepted; commercial qualification blocked by undefined ICP.

Person Entity Resolution is implemented separately from Company Entity Resolution, as required once people are introduced. Same-name observations never auto-match by themselves.

## Post-handoff measured capabilities

- conservative field fusion / truth-discovery diagnostics;
- controlled CNPJ-seed expansion;
- `ICP_DECISION_SUPPORT_V1`;
- `QUALIFICATION_EVIDENCE_SIGNALS_V1`;
- `QUALIFICATION_FIELD_CANONICALIZATION_V1`;
- `COMPANY_SIZE_REGISTRY_SIGNAL_V1`, preserving BrasilAPI `porte` as registry classification rather than employees/revenue;
- `PERSON_ENTITY_RESOLUTION_V1`;
- bounded gap execution/reassessment.

## ICP readiness

```text
BASE_ACCEPTANCE                 READY 0 / PARTIAL 6 / BLOCKED 2
WITH_QUALIFICATION_SIGNALS      READY 2 / PARTIAL 4 / BLOCKED 2
WITH_FIELD_CANONICALIZATION     READY 4 / PARTIAL 2 / BLOCKED 2
WITH_REGISTRY_SIZE_SIGNAL       READY 4 / PARTIAL 3 / BLOCKED 1
```

Current READY dimensions: `INDUSTRY`, `BUSINESS_SIGNAL`, `EXCLUSION_CRITERIA`, `TARGET_ROLE`.

Current PARTIAL dimensions: `GEOGRAPHY`, `COMPANY_SIZE`, `REQUIRED_CONTACTABILITY`.

Current BLOCKED dimension: `TARGET_MARKET`.

This is readiness measurement, not an ICP.

## Validation state

The last recorded whole-repository baseline is:

```text
162 / 162 PASS
```

During the strict post-baseline audit:

```text
POST_BASELINE_ISOLATED_CONTRACT_TESTS = 53 / 53 PASS
CHANGE_IMPACT_REGRESSION = 33 / 33 PASS
UNIQUE_POST_BASELINE_TESTS_EXERCISED = 86 / 86 PASS
```

The affected-current-module E2E replay reproduces the accepted export SHA-256 exactly:

```text
81af24599d7b0bc6ca012a397c243b4049d2e70f0e31a50e0c5eb1d747d0139d
```

This is not mislabeled as a fresh full `unittest discover` run of every private-branch file because the current execution environment cannot clone/download the private repository archive over outbound DNS.

## Commands

Normal deterministic tests/benchmarks:

```bash
python -m unittest discover -s tests -v
python scripts/run_end_to_end_acceptance.py
python scripts/run_icp_decision_support.py
python scripts/evaluate_entity_resolution.py
python scripts/evaluate_field_fusion.py
```

Literal WU3 live smoke, to run only from an environment with outbound DNS/HTTPS:

```bash
python scripts/run_live_brasilapi_smoke.py
```

That command performs one point CNPJ lookup only; it is not a crawler or full scan.

## Core policies

- `Company != Lead`;
- `Found != Valid`;
- `Name Match != Entity Match`;
- `Contact Found != Contact Valid`;
- raw evidence is preserved and facts carry provenance;
- exact full registry/CNPJ equality may auto-match companies; fuzzy company matching goes to review;
- same-name people do not auto-match; strong person identifiers are separated from contextual review signals;
- disagreement remains an explicit `Conflict`;
- contact `VALIDATED` means official-publication corroboration, not deliverability;
- no real lead is qualified without an explicit externally supplied ICP/policy;
- gap execution uses only already-known capabilities and remains bounded;
- controlled expansion is seed-driven and is not a crawler.
