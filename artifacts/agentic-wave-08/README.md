# WAVE-AGENT-08: Minimal Commercial Hardening

## Overview
This wave focused on hardening the `Minimal-A` approach by formalizing its commercial architecture, failure semantics, observability schema, and defining strict budget enforcement rules.
No new agentic frameworks were introduced, and LangGraph/AgentsSDK were explicitly NOT re-evaluated.

## Architecture & Abstraction
The `ModelProvider` abstraction was established to decouple the business logic from explicit Gemini bindings, although `gemini-3.5-flash` remains the reference implementation. Deterministic bypassing ensures the model is NOT called when the core resolves the case (`agent_activated=false`), reducing overhead.

## Experimental Tests
Experimental tests were implemented in `tests/experimental/test_wave08_hardening.py` to validate:
* Deterministic bypass
* Agent escalation triggers
* Failure injection (timeouts, budget exhaustion safely falling back to REVIEW)

## Git State
- **Canonical changes (`src/`)**: 0 (No silent implementations applied, preserving production safety).
- **Experimental implementation**: Tests added to `tests/experimental/`.
- **Artifacts**: Contracts and policies added to `artifacts/agentic-wave-08/`.

## OpenManus Research Status
The `OPENMANUS_EVIDENCE_STATUS = NOT_FUNCTIONALLY_EVALUATED` remains, documented in `openmanus_research_gap.md`, citing the strict requirement for Python 3.12 which blocked its integration into the Python 3.13 baseline.

## Regression
Canonical regression (`.venv-baseline`) confirmed 0 failed, 0 errors across 883 passed tests.

## Closure Decision
`MINIMAL_A_HARDENED`
The Minimal-A topology is now hardened and ready for commercial integration. No silent changes were made to the canonical `src/` codebase; the conceptual hardening and interfaces are fully defined in the architectural JSON policies.
