# RELEASE_CANDIDATE_INTERNAL_V1

Status: READY
Branch: `work/chassis-implementation-v1`

## Purpose

Define the internal engineering release-candidate boundary independently from external certification, legal/compliance sign-off, human professional-registration verification, and campaign authorization.

## Wave 10 disposition

Wave 10 is `SKIPPED_BY_OWNER / DEFERRED`.

This is not a PASS, VERIFIED, READY, legal approval, external certification closure, or campaign authorization. Its unresolved external/human gates remain carried forward.

## Internal RC criteria

The internal release candidate may be `READY` only when all of the following are true:

- package installs from the repository with the supported Python contract;
- installed package imports successfully;
- default test suite is offline and deterministic;
- canonical persistence/schema initialization remains valid;
- migration, backup/restore, evidence-integrity and recovery contracts remain covered by regression evidence;
- default configuration cannot send campaigns or infer commercial authorization;
- external/live tests remain opt-in;
- CI outcome is green for the supported matrix;
- tracked-file hygiene excludes local environments, local databases, coverage output and secret-bearing environment files;
- known blockers are separated into INTERNAL, EXTERNAL, HUMAN, LEGAL and OPTIONAL_BREADTH.

## Supported runtime

`pyproject.toml` declares Python `>=3.11`.

CI verifies Python 3.11, 3.12 and 3.13 on Ubuntu. The Wave 11 hardening found and fixed a Python 3.11 parser incompatibility in person discovery while preserving the canonical behavior.

## Install and CI evidence

CI run `33471375669` on tested commit `2c178c3f2868b8b12dd32ef086758d673e19dc09` passed all matrix jobs for Python 3.11, 3.12 and 3.13.

Each matrix job verifies:

```text
python -m pip install --upgrade pip setuptools wheel
python -m pip install .
python -c "import searchleads; print(searchleads.__name__)"
python scripts/check_internal_rc.py
python -m compileall -q src
python -m pytest -q <RC/recovery targeted battery>
python -m pytest -q
```

Reference Python 3.12 result:

- installed wheel/package: PASS;
- installed import: PASS;
- RC hygiene preflight: `RC_HYGIENE_READY`;
- targeted RC/recovery battery: `91 passed`;
- full regression: `894 passed, 24 skipped, 1 xpassed`.

The XPASS is explicitly classified as obsolete benchmark coverage: `tests/test_dental_qualification_benchmark.py::test_benchmark_exact_contract_routing` has been superseded by aggregate qualification analysis.

## Dependency boundary

The base package declares no production dependency on FollowTheMoney, Nomenklatura, Rigour, Crawlee or Yente. Those remain experimental/live-breadth concerns unless a later engineering decision explicitly changes the production dependency contract.

The experimental Chassis Bake-Off workflow is isolated from the implementation PR: it remains available on the bake-off line but is skipped as a release gate for `work/chassis-implementation-v1`.

## Repository hygiene

Wave 11 adds a tracked-file preflight that fails closed on:

- local SQLite/database artifacts;
- local environment/coverage artifacts;
- high-confidence private-key/token patterns;
- direct-send modules/calls in production Python source;
- experimental chassis imports in production Python source.

This is a scoped engineering hygiene check, not a claim of exhaustive secret-history or DLP scanning.

## Recovery boundary

The existing operational/persistence regression remains authoritative for startup/readiness, SQLite schema validation, migrations, backup/restore, raw Evidence preservation, future-schema rejection, ledger disagreement, and domain-payload tamper detection. No new RPO/RTO claim is made by this release-candidate document.

## Commercial boundary

Internal RC readiness does not imply `SEND_READY`, external certification, legal approval, campaign authorization or commercial-pilot readiness.

The following remain outside this internal gate unless separately closed:

- `LEGAL-001` legal/compliance sign-off;
- manual campaign authorization;
- human CFO/CRO professional-registration verification when campaign policy requires it;
- final SERPRO criticality/path decision;
- remaining BrasilAPI certification limitation, if still applicable.

## Current decision

`INTERNAL_RELEASE_CANDIDATE = READY`

`EXTERNALLY_CERTIFIED = PARTIAL`

`COMMERCIAL_PILOT_READY = BLOCKED_LEGAL`

No internal technical blocker is currently identified by the Wave 11 release-candidate gate. External, human and legal gates remain fail-closed and separate.
