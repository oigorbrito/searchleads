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
| FR-003 | Company ER | `src/searchleads/entity_resolution/company.py` | `tests/test_company_enrichment.py`, `tests/test_field_fusion.py`, experimental ER tests | benchmark fixtures, scorecard | DEFER | Yes |
| FR-004 | Person ER | `src/searchleads/person_entity_resolution/person.py` | `tests/test_person_entity_resolution.py`, experimental ER tests | benchmark fixtures, scorecard | DEFER | Yes |
| FR-005 | Contact discovery | `src/searchleads/contact_discovery/company_page.py` | `tests/test_contact_discovery.py` | local tests | CANONICAL | No |
| FR-006 | Contact validation | `src/searchleads/contact_validation/publication.py` | `tests/test_contact_validation.py`, `tests/test_contact_lead_state_invariants.py` | local tests | CANONICAL | No |
| DR-001 | Persistence / evidence | `src/searchleads/persistence/v3.py`, `src/searchleads/persistence/sqlite.py` | `tests/test_evidence_envelope_*`, `tests/test_persistence*.py` | persistence integrity tests | CANONICAL | No |
| DR-002 | Persistence / provenance | `src/searchleads/domain/provenance.py`, `src/searchleads/persistence/semantic.py` | `tests/test_persistence_semantic_references.py`, `tests/test_fact_provenance_reference_invariants.py` | unit/invariant tests | CANONICAL | No |
| QR-001 | Acceptance / export | `src/searchleads/acceptance/end_to_end.py`, `src/searchleads/lead_export/export.py` | `tests/test_end_to_end_acceptance.py`, `tests/test_lead_export.py` | export/acceptance runs | CANONICAL | No |
| QR-002 | ER review routing | `src/searchleads/selective_review/routing.py` | `tests/test_selective_review.py` | curated review routing tests | CANONICAL | No |
| CR-001 | Qualification | `src/searchleads/qualification_policy/dental_v1.py`, `src/searchleads/qualification/dental.py` | `tests/test_dental_qualification.py`, `tests/test_dental_commercial_acceptance.py` | policy and acceptance tests | CANONICAL | No |
| DR-001 | Persistence envelope integrity | `src/searchleads/persistence/v3.py`, `src/searchleads/persistence/ledger.py` | `tests/test_evidence_envelope_consistency.py` | digest mismatch and consistency rejection | CANONICAL | No |
| OR-001 | Acquisition runtime composition | `src/searchleads/gap_automation/execution.py`, `docs/ACQUISITION_RUNTIME_DECISION_V1.md` | experimental runtime probes | static decision evidence | CANONICAL | No |
