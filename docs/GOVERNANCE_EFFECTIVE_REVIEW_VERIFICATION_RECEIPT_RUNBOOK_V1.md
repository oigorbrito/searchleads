# Effective Review Verification Receipt Runbook v1

## Purpose

Wave Agent 38 records immutable technical receipts for effective-review evidence bundles that have already passed the Wave 37 offline verifier. A receipt is operational evidence that one exact `evidence_sha256` was verified at a declared timestamp by a declared technical verifier reference.

A receipt is not human approval, campaign authorization, legal/compliance signoff, professional verification, pilot release, preflight satisfaction, source-freshness approval, or permission to send.

## Commands

Record a receipt:

```bash
python scripts/record_governance_effective_review_verification.py record \
  --evidence effective-review-evidence.json \
  --receipt verification-receipt.json \
  --db verification-receipts.sqlite
```

List receipts for one exact evidence digest:

```bash
python scripts/record_governance_effective_review_verification.py list \
  --evidence-sha256 <sha256> \
  --db verification-receipts.sqlite
```

## Binding contract

Before persistence, the complete Wave 37 evidence bundle is verified offline. The receipt must then match the verified artifact exactly on:

- `evidence_sha256`
- `audit_entry_id`
- `audit_id`
- `bundle_sha256`

Any mismatch fails closed.

## Persistence contract

`receipt_id` is immutable. Exact replay is idempotent. Reuse of the same ID with different content is rejected. Stored payloads carry a SHA-256 digest and are integrity-checked on load and before idempotent replay.

Receipts are listed deterministically by `verified_at`, then `receipt_id`.

## Authority semantics

Every receipt enforces:

- `send_authorized = false`
- `verification_is_campaign_authorization = false`
- `verification_is_human_approval = false`
- `receipt_is_observational_only = true`

Successful technical verification means only that the artifact passed the deterministic verifier. It does not imply that the underlying review decision is correct, current, legally sufficient, commercially approved, or authorized for dispatch.

## Failure behavior

Tampered evidence, unsupported schema, digest mismatch, chain failure, authority rewrite, receipt binding mismatch, stored receipt tampering, or immutable-ID conflict returns `INVALID` from the CLI and does not create a valid receipt.

## CI interpretation

If GitHub Actions reports `failure` while jobs expose no executed steps (`steps=[]`), classify the run as `BLK-CI-001 / CI_EXTERNAL_RUNNER_BLOCKED`. Do not claim PASS and do not infer a product regression from a runner that never executed tests.
