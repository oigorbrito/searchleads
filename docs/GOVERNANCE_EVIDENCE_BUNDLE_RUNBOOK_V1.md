# Governance Evidence Bundle Runbook v1

## Purpose

Export one deterministic, offline-verifiable governance evidence package for external human review without changing governance decisions, campaign state, release state, or send authorization.

The bundle is observational evidence only. It never authorizes campaign execution.

## Preconditions

An audited governance snapshot must already exist in the append-only governance audit database. The selected `audit_id` identifies the historical evaluation to export.

The export path does not recompute current governance state. It reads the historical snapshot that was already committed to the verified audit chain, preventing time-dependent drift between evaluation and review.

## Export

```bash
python scripts/export_governance_evidence.py export \
  --audit-db path/to/governance.sqlite \
  --audit-id audit-2026-09-12-001 \
  --output evidence/governance-evidence.json
```

The command verifies the audit chain before reading the historical snapshot. On success it writes deterministic JSON and prints a compact receipt containing the selected `audit_id`, bundle SHA-256 and `send_authorized: false`.

## Offline verification

The exported JSON can be verified without the original SQLite database:

```bash
python scripts/export_governance_evidence.py verify \
  --bundle evidence/governance-evidence.json
```

Verification checks:

1. bundle schema version;
2. top-level and nested `send_authorized` invariants;
3. SHA-256 of the complete unsigned bundle;
4. SHA-256 of the historical snapshot against the selected audit entry;
5. every audit-chain header from genesis through the selected entry;
6. continuity of `previous_entry_hash`;
7. recomputed `entry_hash` for every header;
8. agreement between final chain header and selected audit entry;
9. agreement between provenance decision IDs and the audit entry.

Any mismatch returns exit code `2` and an `INVALID:` error.

## Bundle contents

The package contains:

- `schema_version`;
- selected `audit_id`;
- complete historical operational snapshot;
- selected audit entry;
- audit chain headers from sequence 1 through the selected entry;
- decision provenance extracted from snapshot gates;
- explicit authority semantics;
- deterministic `bundle_sha256`;
- `send_authorized: false`.

## Authority semantics

The evidence bundle does not constitute legal approval, professional-status approval, campaign-owner authorization, live certification, operational promotion, or send authorization.

A nested `READY_FOR_AUTHORIZED_EXECUTION` state means only that the recorded authority-chain inputs satisfied the preflight contract for that historical evaluation. It does not authorize dispatch.

## Failure handling

Do not modify an exported package to make verification pass. If verification fails, treat the package as untrusted and re-export from the verified append-only audit database.

If the underlying audit database fails chain verification, stop evidence export and investigate the integrity failure. Do not bypass audit verification.

## Explicit non-scope

This workflow does not:

- send email or messages;
- dispatch campaigns;
- alter governance decisions;
- create human approvals;
- revalidate BrasilAPI;
- scrape CFO/CRO or other professional registries;
- promote `SEND_READY_OPERATIONAL_STATE`;
- promote `LIVE_CERTIFICATION`.

`REAL_SEND = NOT_AUTHORIZED` remains invariant.
