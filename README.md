# searchleads

B2B lead discovery and enrichment project.

Canonical project documentation lives in `docs/`:

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

Historical bake-off and decision-evidence documents remain available for auditability, but they are subordinate to the canonical documents above when describing current architecture or product state.

## Runtime baseline

The package declares Python `>=3.11`. The repository CI matrix targets Python 3.11, 3.12, and 3.13.

Create an isolated environment and install the package plus the test runner:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
python -m pip install pytest
```

No `[test]` extra is currently declared in `pyproject.toml`, so `pytest` is installed explicitly.

## Deterministic core validation

Compile the package first:

```bash
python -m compileall -q src scripts
```

Run the non-experimental regression suite:

```bash
python -m pytest -q tests --ignore=tests/experimental -W error::ResourceWarning
```

Run the full default pytest collection when the current environment supports every collected test:

```bash
python -m pytest -q
```

`tests/experimental` is a separate evidence surface. Optional challenger dependencies or external datasets must not be treated as part of the core gate, and a skipped or dependency-blocked experiment is not a PASS.

## CI interpretation

GitHub Actions status is an independent execution gate. A workflow job that terminates before runner allocation or before any step executes is an infrastructure blocker, not evidence that repository tests failed.

Likewise, live-network certification, professional verification, legal/compliance signoff, and campaign authorization are separate authority gates. Passing the offline regression suite does not by itself make a campaign `SEND_READY` or establish production readiness.
