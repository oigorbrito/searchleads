# TRACEABILITY_MATRIX

Status: CANONICAL

## Matrix Rules

- use stable IDs
- derive where possible from requirement and test metadata
- keep manual duplication low
- unresolved rows must be explicit

| Requirement | Architecture Component | Implementation | Test | Evidence | Current Status | Release Blocker? |
|---|---|---|---|---|---|---|
| FR-001 | Acquisition / discovery | `src/searchleads/dental_discovery`, `src/searchleads/repeatable_discovery`, `src/searchleads/contact_discovery` | `tests/test_dental_public_discovery.py`, `tests/test_repeatable_web_discovery.py`, `tests/test_contact_discovery.py` | local test runs, fixture outputs | CANONICAL | No |
| FR-002 | Domain / normalization | `src/searchleads/normalization.py`, `src/searchleads/entity_resolution/company.py` | `tests/test_normalization.py`, `tests/test_entity_resolution.py` | unit test results | CANONICAL | No |
| FR-003 | Company ER | `src/searchleads/entity_resolution/company.py` | `tests/test_company_enrichment.py`, `tests/test_field_fusion.py`, experimental ER tests | benchmark fixtures, scorecard | PROVISIONAL_COMPOSE | Yes |
| FR-004 | Person ER | `src/searchleads/person_entity_resolution/person.py` | `tests/test_person_entity_resolution.py`, experimental ER tests | benchmark fixtures, scorecard | PROVISIONAL_COMPOSE | Yes |
| FR-005 | Contact discovery | `src/searchleads/contact_discovery/company_page.py` | `tests/test_contact_discovery.py` | local tests | CANONICAL | No |
| FR-006 | Contact validation | `src/searchleads/contact_validation/publication.py` | `tests/test_contact_validation.py`, `tests/test_contact_lead_state_invariants.py` | local tests | CANONICAL | No |
| DR-001 | Persistence / evidence | `src/searchleads/persistence/v3.py`, `src/searchleads/persistence/sqlite.py` | `tests/test_evidence_envelope_*`, `tests/test_persistence*.py` | persistence integrity tests | CANONICAL | No |
| DR-002 | Persistence / provenance | `src/searchleads/domain/provenance.py`, `src/searchleads/persistence/semantic.py` | `tests/test_persistence_semantic_references.py`, `tests/test_fact_provenance_reference_invariants.py` | unit/invariant tests | CANONICAL | No |
| QR-001 | Acceptance / export | `src/searchleads/acceptance/end_to_end.py`, `src/searchleads/lead_export/export.py`, `src/searchleads/lead_export/canonical.py`, `src/searchleads/application/chassis.py` | `tests/test_end_to_end_acceptance.py`, `tests/test_lead_export.py`, `tests/test_operational_canonical_integration.py` | export/acceptance runs and canonical operational integration | CANONICAL | No |
| QR-002 | ER review routing | `src/searchleads/selective_review/routing.py` | `tests/test_selective_review.py` | curated review routing tests | PROVISIONAL_COMPOSE | No |
| CR-001 | Qualification | `src/searchleads/qualification_policy/dental_v1.py`, `src/searchleads/qualification/dental.py` | `tests/test_dental_qualification.py`, `tests/test_dental_commercial_acceptance.py` | policy and acceptance tests | CANONICAL | No |
| DR-001 | Persistence envelope integrity | `src/searchleads/persistence/v3.py`, `src/searchleads/persistence/ledger.py` | `tests/test_evidence_envelope_consistency.py` | digest mismatch and consistency rejection | CANONICAL | No |
| OR-001 | Acquisition runtime composition | `src/searchleads/gap_automation/execution.py`, `src/searchleads/runtime_adapter.py`, `src/searchleads/application/chassis.py`, `docs/ACQUISITION_RUNTIME_DECISION_V1.md`, `docs/OPERATIONS_AND_DEPLOYMENT.md` | `tests/test_operational_canonical_integration.py`, experimental runtime probes | static decision evidence plus local fallback adapter | VERIFIED_PARTIAL | No |
| OR-003 | Operational lifecycle and recovery | `src/searchleads/operational.py`, `src/searchleads/persistence/sqlite.py`, `src/searchleads/application/chassis.py`, `docs/OPERATIONS_AND_DEPLOYMENT.md` | `tests/test_operational_readiness.py` | startup, health, readiness, backup, restore, recovery, and replay coverage | VERIFIED_PARTIAL | No |
| OR-004 | System readiness vs SEND_READY separation | `src/searchleads/operational.py`, `docs/SECURITY_PRIVACY_COMPLIANCE.md`, `docs/OPERATIONS_AND_DEPLOYMENT.md` | `tests/test_operational_readiness.py` | explicit SEND_READY state machine and compliance blocker register | VERIFIED_PARTIAL | No |
| OR-005 | External certification execution and source authority | `src/searchleads/operational.py`, `docs/SEARCHLEADS_COMPLETION_PLAN.md`, `docs/SECURITY_PRIVACY_COMPLIANCE.md`, `docs/RELEASE_READINESS.md` | `tests/test_operational_readiness.py` | certification inventory, source authority map, freshness policy, drift detection, and live observation records | VERIFIED_PARTIAL | Yes |
| OR-006 | Compliance policy and pilot gate finalization | `src/searchleads/operational.py`, `docs/SEARCHLEADS_COMPLETION_PLAN.md`, `docs/SECURITY_PRIVACY_COMPLIANCE.md`, `docs/RELEASE_READINESS.md` | `tests/test_operational_readiness.py` | compliance policy, manual authorization record, send-ready proof, suppression precedence, and pilot readiness | VERIFIED_PARTIAL | Yes |

## Current Verification Note

- `LEGACY_CONTRACT_RECONCILIATION = COMPLETE`
- `INTERNAL_REGRESSION_SUITE = PASS`
- full-suite result: `884 passed`, `24 skipped`, `1 xfailed`
- skips are external-dependency probes for bake-off capabilities, not hidden product failures
- the single xfail is `TEST_OBSOLETE` and intentionally retained as legacy benchmark evidence
- Company ER and Person ER are provisionally composed from local benchmark evidence; external challenger breadth remains open
- operational readiness helpers are now covered by `tests/test_operational_readiness.py`
- external certification inventory, contact-use policy, suppression, and pilot readiness helpers are covered by `tests/test_operational_readiness.py`
- source authority, freshness, compliance policy, manual authorization, drift detection, and send-ready proof helpers are covered by `tests/test_operational_readiness.py`
