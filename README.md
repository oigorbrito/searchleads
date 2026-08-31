# searchleads

B2B lead discovery and enrichment project.

Canonical project documentation now lives in `docs/`:

- [`docs/PROJECT_CHARTER.md`](docs/PROJECT_CHARTER.md)
- [`docs/PRODUCT_REQUIREMENTS.md`](docs/PRODUCT_REQUIREMENTS.md)
- [`docs/SYSTEM_ARCHITECTURE.md`](docs/SYSTEM_ARCHITECTURE.md)
- [`docs/DOMAIN_MODEL.md`](docs/DOMAIN_MODEL.md)
- [`docs/DATA_AND_EVIDENCE_MODEL.md`](docs/DATA_AND_EVIDENCE_MODEL.md)
- [`docs/QUALITY_MODEL.md`](docs/QUALITY_MODEL.md)
- [`docs/VERIFICATION_AND_VALIDATION_PLAN.md`](docs/VERIFICATION_AND_VALIDATION_PLAN.md)
- [`docs/OPERATIONS_AND_DEPLOYMENT.md`](docs/OPERATIONS_AND_DEPLOYMENT.md)
- [`docs/SECURITY_PRIVACY_COMPLIANCE.md`](docs/SECURITY_PRIVACY_COMPLIANCE.md)
- [`docs/TRACEABILITY_MATRIX.md`](docs/TRACEABILITY_MATRIX.md)
- [`docs/RELEASE_READINESS.md`](docs/RELEASE_READINESS.md)
- [`docs/SEARCHLEADS_COMPLETION_PLAN.md`](docs/SEARCHLEADS_COMPLETION_PLAN.md)

The historical bake-off and decision-evidence docs remain in place, but they are subordinate to the canonical documents above. When they conflict, canonical docs win.

## Current State

- Company ER and Person ER are still benchmark-dependent.
- evidence/persistence, contact discovery, qualification, and acceptance are already represented in the implementation and tests.
- the next unblocked canonical work is architecture baseline consolidation and traceability completion.

## Run tests

```bash
python -m pytest
```

GitHub Actions status and external certification are still separate gates. No production-readiness claim is made here.
