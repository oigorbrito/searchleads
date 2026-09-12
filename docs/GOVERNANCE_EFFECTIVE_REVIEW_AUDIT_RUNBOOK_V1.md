# Governance Effective Review Audit Runbook v1

## Purpose

Wave Agent 36 adds an append-only, tamper-evident audit trail for the effective human-review status produced by Wave 35.

The audit trail is observational only. It does not authorize a campaign, authorize send, satisfy `AUTH-CAMPAIGN-001`, alter preflight, alter pilot release, replace legal/compliance signoff, replace professional verification, or satisfy source freshness.

## Record an effective review status

```bash
python scripts/audit_governance_effective_review.py record \
  --bundle path/to/governance-evidence-bundle.json \
  --review-db path/to/evidence-reviews.sqlite \
  --resolution-db path/to/evidence-review-resolutions.sqlite \
  --audit-db path/to/effective-review-audit.sqlite \
  --audit-entry-id effective-review-audit-001
```

The command recomputes the current effective human-review status from the verified evidence bundle and current immutable review/resolution stores, then appends that exact status to the audit chain.

## Verify the chain

```bash
python scripts/audit_governance_effective_review.py verify \
  --audit-db path/to/effective-review-audit.sqlite
```

Verification checks:

- contiguous sequence numbers;
- predecessor-hash continuity from genesis;
- canonical status SHA-256;
- entry SHA-256;
- exact `audit_id` and `bundle_sha256` binding;
- non-authorization invariants.

Any mismatch fails closed.

## List entries

```bash
python scripts/audit_governance_effective_review.py list \
  --audit-db path/to/effective-review-audit.sqlite
```

`list` verifies the entire chain before returning entries.

## Replay and immutability

Reusing an `audit_entry_id` with the identical status is idempotent and returns `ALREADY_PRESENT`. Reusing the same ID with different content is rejected.

Each entry records:

- `audit_entry_id`;
- sequence;
- exact evidence `audit_id`;
- exact `bundle_sha256`;
- canonical `status_sha256`;
- `previous_entry_hash`;
- `entry_hash`;
- full historical effective-review status.

## Interpretation

An audited status is historical evidence of what the effective review layer reported at that point. Even an audited `APPROVED` review-domain decision is not campaign authorization and is not permission to dispatch or send.

The following invariants always remain true:

```text
send_authorized = false
audit_is_campaign_authorization = false
audit_is_observational_only = true
REAL_SEND = NOT_AUTHORIZED
LIVE_CERTIFICATION = BLOCKED
```

## CI classification

The targeted governance CI gate includes service and CLI tests for the effective review audit. If GitHub Actions reports jobs with `steps=[]`, classify the run as `BLK-CI-001 / CI_EXTERNAL_RUNNER_BLOCKED`; do not claim PASS and do not infer a product regression without executed test evidence.
