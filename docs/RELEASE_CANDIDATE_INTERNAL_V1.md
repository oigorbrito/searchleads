# RELEASE_CANDIDATE_INTERNAL_V1

Status: CANDIDATE
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
- CI outcome is green for the supported matrix, or an exact CI blocker is recorded;
- tracked-file hygiene excludes local environments, local databases, coverage output and secret-bearing environment files;
- known blockers are separated into INTERNAL, EXTERNAL, HUMAN, LEGAL and OPTIONAL_BREADTH.

## Supported runtime

`pyproject.toml` currently declares Python `>=3.11`.

CI covers Python 3.11, 3.12 and 3.13 on Ubuntu and must install the package before running the offline regression suite.

## Install contract

```text
python -m pip install --upgrade pip setuptools wheel
python -m pip install .
python -c "import searchleads; print(searchleads.__name__)"
python -m pytest -q
```

## Dependency boundary

The base package declares no production dependency on FollowTheMoney, Nomenklatura, Rigour, Crawlee or Yente. Those remain experimental/live-breadth concerns unless a later engineering decision explicitly changes the production dependency contract.

## Commercial boundary

Internal RC readiness does not imply `SEND_READY`, external certification, legal approval, campaign authorization or commercial-pilot readiness.

The following remain outside this internal gate unless separately closed:

- `LEGAL-001` legal/compliance sign-off;
- manual campaign authorization;
- human CFO/CRO professional-registration verification when campaign policy requires it;
- final SERPRO criticality/path decision;
- remaining BrasilAPI certification limitation, if still applicable.

## Recovery boundary

The existing operational contract remains authoritative for startup/readiness, SQLite schema validation, backup/restore and recovery. No new RPO/RTO claim is made by this release-candidate document.

## Current decision

`INTERNAL_RELEASE_CANDIDATE = VERIFICATION_PENDING`

Promote to `READY` only after the hardened CI matrix and current regression evidence pass on the resulting commit.
