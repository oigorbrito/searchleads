# SearchLeads

B2B lead discovery and enrichment project following the supplied staged handoff.

## Strict handoff status

```text
ARCHITECTURAL_DIRECTION = ALIGNED
NON_NEGOTIABLE_PRINCIPLES = ALIGNED
LEAD_SPECIALIZATION = PRESERVED

PERSON_ENTITY_RESOLUTION = IMPLEMENTED_V1
PERSON_PROFESSIONAL_CONTACTS = IMPLEMENTED_V1
HANDOFF_METRICS = REPRESENTED_V1
WU14_EXECUTION_REASSESSMENT = IMPLEMENTED_V1

TECHNICAL_E2E_BASELINE = PASS
LATEST_E2E_PERSON_CONTACT_EXTENSION = CODED_NOT_FULLY_EXECUTED

WU3_LIVE_HTTP = PENDING_EXTERNAL_SMOKE
ICP_DEFINED = NO
REAL_QUALIFICATION = NOT_EVALUABLE
COMMERCIAL_E2E = BLOCKED_BY_UNDEFINED_ICP
LATEST_HEAD_FULL_REGRESSION = PENDING
MAIN_INTEGRATION = NOT_DONE
```

See [`HANDOFF-AUDIT-CLOSURE.md`](HANDOFF-AUDIT-CLOSURE.md) for the strict work-unit audit.

## Roadmap boundaries

- `Company != Lead`.
- `Found != Valid`.
- `Name Match != Entity Match`.
- `Contact Found != Contact Valid`.
- Raw evidence is preserved and facts carry per-fact provenance.
- Company ER is separate from Person ER.
- Fuzzy company/person identity evidence routes to review unless a V1 strong identifier rule is met.
- Contact `VALIDATED` means official-publication corroboration, not deliverability.
- Person professional e-mail/phone observations are person-owned `DISCOVERED` contacts.
- A shared curriculum/profile URL is contextual evidence, not a strong person identifier.
- Repeatable web discovery is source-specific and deterministic; no generic crawler or LLM-per-page loop.
- Gap automation is bounded to already-known capabilities.
- No real lead is qualified without an explicit externally supplied ICP/policy.

## Original roadmap status

1. `LEADS_SCIENTIFIC_FOUNDATION_AND_DOMAIN_V1` — PASS
2. `LEADS_PERSISTENCE_AND_EVIDENCE_V1` — PASS
3. `LEADS_FIRST_REAL_SOURCE_V1` — adapter implemented; literal live HTTP smoke pending external egress
4. `COMPANY_NORMALIZATION_V1` — PASS
5. `COMPANY_ENTITY_RESOLUTION_V1` — PASS_V1
6. `COMPANY_ENRICHMENT_V1` — PASS
7. `CONTACT_DISCOVERY_V1` — PASS
8. `PERSON_AND_ROLE_DISCOVERY_V1` — PASS_V1_SOURCE_LIMITED; professional contacts included, current profile locator shared
9. `CONTACT_VALIDATION_V1` — PASS_V1
10. `REPEATABLE_WEB_DISCOVERY_V1` — PASS
11. `LEAD_QUALIFICATION_V1` — BLOCKED_BY_UNDEFINED_ICP for real business execution
12. `SELECTIVE_REVIEW_V1` — PASS
13. `LEADS_EXPORT_V1` — PASS
14. `GAP_DETECTION_AND_AUTOMATION_V1` — PASS_V1
15. `END_TO_END_ACCEPTANCE_V1` — baseline technical PASS; commercial qualification blocked; latest person-contact extension pending complete-head execution

## Section 41 metrics

The metric surface is represented for discovery, entity resolution, enrichment, contacts, qualification and operation. A metric whose universe, ground truth or telemetry is missing is returned as `UNAVAILABLE` with a reason rather than guessed.

Notably:

```text
ER_FALSE_SPLIT_RATE = REPRESENTED
QUALIFICATION_PRECISION_RECALL = UNAVAILABLE_UNTIL_ICP_AND_LABELS
OPERATIONAL_COST_METRICS = UNAVAILABLE_UNTIL_TELEMETRY
```

See [`HANDOFF-METRICS-V1.md`](HANDOFF-METRICS-V1.md).

## Validation state

Last whole-repository baseline:

```text
162 / 162 PASS
```

Post-baseline executable contracts completed before the latest E2E integration extension:

```text
AUDIT_AND_CHANGE_IMPACT = 86 / 86 PASS
HANDOFF_METRICS = 11 / 11 PASS
PERSON_PROFESSIONAL_CONTACTS = 9 / 9 PASS
TOTAL_DISTINCT_POST_BASELINE_TESTS_EXECUTED = 106 / 106 PASS
```

The earlier affected-module E2E replay reproduced its historical accepted export hash:

```text
81af24599d7b0bc6ca012a397c243b4049d2e70f0e31a50e0c5eb1d747d0139d
```

That hash belongs to the earlier export shape and is not reused after person contacts were added.

The latest E2E extension is coded to exercise:

```text
VALIDATED_COMPANY_CONTACTS = 2
DISCOVERED_PERSON_CONTACTS = 4
PERSON_PROFESSIONAL_PROFILES = 0  # current shared curriculum locator is not strong identity
PEOPLE = 2
ROLES = 2
BUSINESS_QUALIFICATION = UNKNOWN
```

A fresh full `python -m unittest discover` of the latest private head remains pending because this execution environment cannot clone/download the private repository over outbound network.

## Commands

```bash
python -m unittest discover -s tests -v
python scripts/run_end_to_end_acceptance.py
python scripts/run_icp_decision_support.py
python scripts/evaluate_entity_resolution.py
python scripts/evaluate_field_fusion.py
python scripts/run_live_brasilapi_smoke.py
```

The live BrasilAPI smoke performs one point CNPJ lookup only; it is not a crawler/full scan.
