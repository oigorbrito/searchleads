# Governance Effective Review Verification Audit Runbook v1

## Purpose
Wave Agent 39 adds an append-only, tamper-evident audit trail for the technical verification receipts introduced in Wave 38. This audit exists only to preserve historical evidence that a specific receipt was recorded in a specific order.

It does not create human approval, campaign authorization, send authorization, preflight approval, pilot release, legal/compliance signoff, professional verification, or source-freshness approval.

## Data model
Each audit entry stores:

- `audit_entry_id`
- monotonic `sequence`
- `receipt_id`
- `evidence_sha256`
- canonical `receipt_sha256`
- `previous_entry_hash`
- `entry_hash`
- the full historical receipt mapping

The entry hash is SHA-256 over the canonical header fields above. The first entry has `previous_entry_hash = null`; each later entry points to the prior entry hash.

## Commands
Record one existing receipt:

```bash
python scripts/audit_governance_effective_review_verification.py record \
  --receipt-db receipts.sqlite \
  --audit-db receipt-audit.sqlite \
  --receipt-id <receipt-id> \
  --audit-entry-id <audit-entry-id>
```

Verify the full audit chain:

```bash
python scripts/audit_governance_effective_review_verification.py verify \
  --audit-db receipt-audit.sqlite
```

List entries only after full-chain verification:

```bash
python scripts/audit_governance_effective_review_verification.py list \
  --audit-db receipt-audit.sqlite
```

## Fail-closed behavior
The implementation rejects or detects:

- blank audit entry IDs;
- reuse of an audit entry ID with different receipt content;
- receipt payload digest tampering;
- receipt-to-entry binding mismatch;
- entry-hash mismatch;
- predecessor mismatch;
- sequence discontinuity;
- receipts that claim send authorization;
- receipts that claim campaign authorization or human approval;
- receipts that are not explicitly observational only.

Exact replay of an existing audit entry is idempotent only after the stored entry passes integrity verification.

## Governance invariants

- `REAL_SEND = NOT_AUTHORIZED`
- `SEND_READY_OPERATIONAL_STATE = BLOCKED`
- `LIVE_CERTIFICATION = BLOCKED`
- audit does not satisfy `AUTH-CAMPAIGN-001`
- audit does not alter preflight or pilot release
- audit does not replace legal/compliance signoff
- audit does not replace professional verification
- audit does not alter source freshness
- software does not invent human decisions

## CI evidence
If GitHub Actions returns failed jobs with no executed steps, classify the observation as `BLK-CI-001 / CI_EXTERNAL_RUNNER_BLOCKED`. Do not report PASS and do not infer a product regression without executed-test evidence.
