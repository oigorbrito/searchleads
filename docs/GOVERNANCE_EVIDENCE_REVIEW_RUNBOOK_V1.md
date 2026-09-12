# Governance Evidence Review Runbook v1

## Purpose

Record a human review decision for one exact, already-exported governance evidence bundle.

This workflow is intentionally separate from campaign authorization. A review decision can say that a reviewer approved, rejected, or requested more review of the evidence package they examined. It does **not** authorize outreach, dispatch, or send.

## Required artifacts

1. A verified `governance-evidence-bundle/v1` JSON file.
2. A review JSON object containing:
   - `review_id`
   - `audit_id`
   - `bundle_sha256`
   - `reviewer_reference`
   - `decision`: `APPROVED`, `REJECTED`, or `MORE_REVIEW_REQUIRED`
   - timezone-aware `reviewed_at`
   - non-empty `evidence_refs`
   - optional non-blank `note`
   - `send_authorized: false`
   - `review_is_campaign_authorization: false`

The `audit_id` and `bundle_sha256` must be copied from the exact bundle reviewed by the human reviewer.

## Record a review

```bash
python scripts/review_governance_evidence.py record \
  --bundle reviewed-bundle.json \
  --review review.json \
  --db evidence-reviews.sqlite
```

The command verifies the complete bundle before parsing the review binding. It then requires exact equality for both `audit_id` and `bundle_sha256` before persistence.

A successful first write reports `storage_action: INSERTED`. Replaying the exact same immutable review reports `ALREADY_PRESENT`. Reusing the same `review_id` with different content is rejected.

## List reviews for one exact bundle

```bash
python scripts/review_governance_evidence.py list \
  --bundle reviewed-bundle.json \
  --db evidence-reviews.sqlite
```

The bundle is re-verified before lookup. Only reviews with the same `audit_id` **and** `bundle_sha256` are returned.

## Fail-closed behavior

The command rejects the operation before persistence when:

- the bundle digest or audit chain does not verify;
- `audit_id` differs from the verified bundle;
- `bundle_sha256` differs from the verified bundle;
- `reviewed_at` has no timezone;
- reviewer/evidence references are blank or missing;
- the decision is outside the allowed review-decision enum;
- the payload attempts `send_authorized: true`;
- the payload attempts `review_is_campaign_authorization: true`.

Persisted review payloads are stored with SHA-256 integrity metadata. Tampering causes reads to fail closed.

## Authority semantics

An `APPROVED` evidence review means only that the named human reviewer recorded an approval of the exact evidence bundle identified by its cryptographic digest and audit ID.

It does not satisfy `AUTH-CAMPAIGN-001`, does not replace legal/compliance signoff, does not close source-freshness requirements, and does not authorize real send.

Operational invariants remain:

- `SEND_READY_OPERATIONAL_STATE = BLOCKED` unless independently changed by the existing authority chain.
- `LIVE_CERTIFICATION = BLOCKED` unless independently satisfied.
- `REAL_SEND = NOT_AUTHORIZED`.
