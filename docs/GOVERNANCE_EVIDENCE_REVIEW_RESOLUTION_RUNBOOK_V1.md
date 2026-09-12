# Governance Evidence Review Resolution Runbook v1

## Purpose

Wave Agent 34 adds explicit human conflict-resolution records for a governance evidence bundle whose consolidated evidence-review state is currently `CONFLICT`.

A resolution is observational governance state only. It does not authorize a campaign, authorize send, satisfy `AUTH-CAMPAIGN-001`, alter preflight, alter pilot release, replace legal/compliance signoff, replace professional verification, or satisfy source freshness.

## Exact binding

Every resolution is bound to:

- exact `audit_id`;
- exact `bundle_sha256`;
- exact sorted `review_ids` currently present for that bundle;
- `review_set_sha256`, the SHA-256 of the canonical sorted review-id list.

The bundle is fully verified before resolution persistence. The current consolidated review state must be `CONFLICT`.

If the review set changes after a resolution is recorded, the prior resolution becomes `STALE_RESOLUTION` and has no effective decision for the new review set.

## Commands

Record a human resolution:

```bash
python scripts/resolve_governance_evidence_review.py record \
  --bundle path/to/governance-evidence-bundle.json \
  --review-db path/to/evidence-reviews.sqlite \
  --resolution-db path/to/evidence-review-resolutions.sqlite \
  --resolution path/to/resolution.json
```

Inspect resolution status:

```bash
python scripts/resolve_governance_evidence_review.py status \
  --bundle path/to/governance-evidence-bundle.json \
  --review-db path/to/evidence-reviews.sqlite \
  --resolution-db path/to/evidence-review-resolutions.sqlite
```

## Resolution states

- `NO_RESOLUTION`: no human resolution exists for the exact bundle.
- `RESOLVED`: one or more applicable resolutions exist for the exact current review set and all applicable resolutions agree on one decision.
- `RESOLUTION_CONFLICT`: applicable human resolutions for the same exact review set disagree. No decision is chosen automatically.
- `STALE_RESOLUTION`: resolution records exist, but none bind to the exact current review set.

`latest_resolution_id` is metadata only and never overrides contradictory resolutions.

## Allowed human decisions

Resolution decisions use the existing evidence-review decision vocabulary:

- `APPROVED`
- `REJECTED`
- `MORE_REVIEW_REQUIRED`

The software never invents a resolution decision. It validates and persists externally supplied human authority input.

## Persistence

Resolution IDs are immutable. Exact replay is idempotent. Reusing the same `resolution_id` with different content is a conflict. Persisted payloads are protected by SHA-256 and integrity mismatch fails closed.

## Safety invariants

Every successful resolution/status output preserves:

```text
send_authorized = false
resolution_is_campaign_authorization = false
changes_auth_campaign_001 = false
changes_preflight = false
changes_pilot_release = false
changes_legal_signoff = false
changes_professional_verification = false
changes_source_freshness = false
REAL_SEND = NOT_AUTHORIZED
```

An evidence-review resolution is not campaign-owner authorization and cannot substitute for any operational gate.

## CI classification

The targeted governance CI gate includes the Wave 34 resolution service and CLI tests. If GitHub Actions reports jobs with `steps=[]` before test execution, classify the result as `BLK-CI-001 / CI_EXTERNAL_RUNNER_BLOCKED`; do not claim PASS and do not infer a product regression.
