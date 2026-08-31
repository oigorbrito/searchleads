# ENGINEERING_BASELINE_FREEZE_V1

Status: CANONICAL

## Baseline Snapshot

- baseline_id: `engineering-baseline-2026-08-31`
- baseline_commit_sha: `fb774cc6ddc4f8c7fc397476f868bd1de3a70506`
- freeze_commit_sha: `2c3ffcdad2fcc6527f299e8dc0e6a402df36b35d`
- date: `2026-08-31`

## Version Set

- requirements_version: `docs/PRODUCT_REQUIREMENTS.md`
- architecture_version: `docs/SYSTEM_ARCHITECTURE.md`
- domain_model_version: `docs/DOMAIN_MODEL.md`
- data_evidence_version: `docs/DATA_AND_EVIDENCE_MODEL.md`
- er_decision_version: `docs/ER_AND_NORMALIZATION_DECISION_V1.md`
- quality_model_version: `docs/QUALITY_MODEL.md`
- completion_plan_version: `docs/SEARCHLEADS_COMPLETION_PLAN.md`

## Known Provisional Decisions

- Company ER = `PROVISIONAL_COMPOSE`
- Person ER = `PROVISIONAL_COMPOSE`
- qualification remains separate from send readiness
- evidence remains distinct from statements
- acquisition runtime remains an adapter boundary
- API/application chassis remains thin

## Known External Blockers

- `BR-001`: acquisition runtime environment still needs a sanctioned operational path
- `BR-002`: additional challenger breadth remains partially blocked by Windows ICU/pyicu installation constraints

## Interpretation

This freeze records the evidence boundary for the engineering baseline. It does not freeze the implementation or prevent later ADR-backed changes.
