# TRACEABILITY_MATRIX

Status: CANONICAL

## Matrix Rules

- use stable IDs
- derive where possible from requirement and test metadata
- keep manual duplication low
- unresolved rows must be explicit

| Requirement | Architecture Component | Implementation | Test | Evidence | Current Status | Release Blocker? |
|---|---|---|---|---|---|---|
| FR-001 | Acquisition / discovery | `src/searchleads/dental_discovery`, `src/searchleads/repeatable_discovery`, `src/searchleads/contact_discovery` | discovery/contact tests | local test runs, fixture outputs | CANONICAL | No |
| FR-002 | Domain / normalization | `src/searchleads/normalization.py`, `src/searchleads/entity_resolution/company.py` | normalization/entity tests | unit test results | CANONICAL | No |
| FR-003 | Company ER | `src/searchleads/entity_resolution/company.py` | company/field-fusion/experimental ER tests | benchmark fixtures, scorecard | PROVISIONAL_COMPOSE | Yes |
| FR-004 | Person ER | `src/searchleads/person_entity_resolution/person.py` | person ER and experimental tests | benchmark fixtures, scorecard | PROVISIONAL_COMPOSE | Yes |
| FR-005 | Contact discovery | `src/searchleads/contact_discovery/company_page.py` | `tests/test_contact_discovery.py` | local tests | CANONICAL | No |
| FR-006 | Contact validation | `src/searchleads/contact_validation/publication.py` | contact validation/invariant tests | local tests | CANONICAL | No |
| DR-001 | Persistence / evidence | `src/searchleads/persistence/v3.py`, `src/searchleads/persistence/sqlite.py` | evidence/persistence tests | persistence integrity tests | CANONICAL | No |
| DR-002 | Persistence / provenance | `src/searchleads/domain/provenance.py`, `src/searchleads/persistence/semantic.py` | semantic/provenance invariant tests | unit/invariant tests | CANONICAL | No |
| QR-001 | Acceptance / export | acceptance/export/application chassis | E2E/export/operational integration tests | export/acceptance runs | CANONICAL | No |
| QR-002 | ER review routing | `src/searchleads/selective_review/routing.py` | `tests/test_selective_review.py` | curated review routing tests | PROVISIONAL_COMPOSE | No |
| CR-001 | Qualification | qualification policy and dental qualification | qualification/acceptance tests | policy and acceptance tests | CANONICAL | No |
| OR-001 | Acquisition runtime composition | runtime adapter/application chassis | operational integration + experimental probes | fallback adapter evidence | VERIFIED_PARTIAL | No |
| OR-003 | Operational lifecycle and recovery | `src/searchleads/operational.py`, SQLite persistence | `tests/test_operational_readiness.py` | startup/backup/restore/recovery | VERIFIED_PARTIAL | No |
| OR-004 | System readiness vs SEND_READY separation | `src/searchleads/operational.py` | operational readiness tests | explicit send-ready state machine | VERIFIED_PARTIAL | No |
| OR-005 | External certification and source authority | `src/searchleads/operational.py`, `src/searchleads/external_governance.py` | operational readiness + external governance tests | Wave 12 evidence and source authority references | VERIFIED_PARTIAL | Yes |
| OR-006 | Compliance policy and pilot gating | `src/searchleads/operational.py`, `src/searchleads/campaign_preflight.py` | operational readiness + campaign preflight tests | Wave 13 decision-intake evidence | VERIFIED_PARTIAL | Yes |
| OR-007 | External decision intake | `src/searchleads/campaign_preflight.py` | `tests/test_campaign_preflight.py` | scoped/expiring/revocable legal, professional and campaign authority records | VERIFIED | No internal blocker |

## Current Verification Note

- `LEGACY_CONTRACT_RECONCILIATION = COMPLETE`
- `INTERNAL_RELEASE_CANDIDATE = READY`
- `EXTERNAL_DECISION_INTAKE = READY`
- Wave 13 CI run `33507232293` passed Python 3.11, 3.12 and 3.13
- reference Python 3.12: RC/recovery `91 passed`; external governance/preflight `28 passed`; full suite `909 passed, 24 skipped, 1 xpassed`
- the XPASS remains an explicitly obsolete qualification benchmark superseded by aggregate qualification analysis
- Company ER and Person ER remain `PROVISIONAL_COMPOSE`; challenger breadth is not on the minimum commercial critical path
- `EXT-SERPRO-001` is `NOT_REQUIRED` for the minimum commercial path
- `LEGAL-001`, `EXT-BRASILAPI-001`, conditional `EXT-CFO-001`, and `AUTH-CAMPAIGN-001` remain external/human gates
- no campaign execution or send authorization is implied by any engineering verification state
