# Governance Snapshot Audit Runbook v1

## Purpose

Record and verify an append-only audit trail of governance operational snapshots. This trail is observational only. It does not authorize, schedule, send, dispatch, or otherwise execute a campaign.

## Record one snapshot

```bash
python scripts/audit_governance_snapshot.py record \
  --scope path/to/scope.json \
  --db path/to/governance.sqlite \
  --now 2026-09-12T03:00:00+00:00 \
  --audit-id audit-20260912-001
```

The command rebuilds the operational snapshot from the persisted governance state, then appends one immutable audit entry.

## Verify the complete chain

```bash
python scripts/audit_governance_snapshot.py verify \
  --db path/to/governance.sqlite
```

Successful output reports `chain_valid: true`, the number of audit entries, and `send_authorized: false`.

## List verified entries

```bash
python scripts/audit_governance_snapshot.py list \
  --db path/to/governance.sqlite
```

The command verifies the complete chain before returning entries.

## Integrity model

Each audit entry contains:

- immutable `audit_id`;
- monotonic SQLite sequence;
- exact campaign/policy/jurisdiction/channel scope;
- evaluation timestamp;
- preflight and pilot-release states;
- ordered blockers;
- persisted governance decision IDs referenced by the snapshot;
- canonical snapshot SHA-256;
- previous audit-entry hash;
- current audit-entry hash.

The first entry has no predecessor. Every later entry references the preceding entry hash. Verification fails closed if the snapshot payload, stored digest, predecessor pointer, or entry hash does not match.

## Operational constraints

- `audit_id` reuse is rejected.
- Audit records are append-only through the public repository API.
- The audit trail does not modify governance decisions.
- The audit trail does not change gate validity.
- `READY_FOR_AUTHORIZED_EXECUTION` remains a preflight/release classification only.
- Every CLI response carries `send_authorized: false`.
- `REAL_SEND = NOT_AUTHORIZED`.
- `LIVE_CERTIFICATION = BLOCKED` until its external requirements are actually satisfied.

## CI

The targeted governance regression includes:

- `tests/test_governance_audit.py`
- `tests/test_governance_audit_cli.py`

If GitHub Actions fails before any step with `runner_id=0` / `steps=[]`, classify that result under accepted external constraint `BLK-CI-001`; do not claim either product regression or PASS.
