# Governance Evidence Review Status Runbook v1

## Purpose

Wave Agent 33 adds a read-only consolidated view of all human reviews bound to one exact governance evidence bundle identified by `audit_id + bundle_sha256`.

The status view is observational only. It does not authorize a campaign, authorize send, alter preflight, alter pilot release, replace legal/compliance signoff, replace professional verification, or satisfy source freshness.

## Command

```bash
python scripts/show_governance_evidence_review_status.py \
  --bundle path/to/governance-evidence-bundle.json \
  --db path/to/evidence-reviews.sqlite
```

The bundle is fully verified before any review status is returned. A tampered bundle fails closed.

## Consolidated states

- `NO_REVIEW`: no persisted review exists for the exact verified bundle.
- `APPROVED`: one or more reviews exist and every review decision is `APPROVED`.
- `REJECTED`: one or more reviews exist and every review decision is `REJECTED`.
- `MORE_REVIEW_REQUIRED`: one or more reviews exist and every review decision is `MORE_REVIEW_REQUIRED`.
- `CONFLICT`: two or more distinct review decisions coexist for the exact bundle.

`CONFLICT` is never auto-resolved. The most recent review is exposed only as metadata. It does not override older contradictory reviews.

## Deterministic latest review

`latest_review_id` is chosen by maximum `(reviewed_at, review_id)`. This makes ordering deterministic when timestamps are equal while preserving the full review history.

## Output invariants

Every successful result preserves:

```text
send_authorized = false
review_is_campaign_authorization = false
changes_preflight = false
changes_pilot_release = false
changes_legal_signoff = false
changes_professional_verification = false
changes_source_freshness = false
```

The output includes the exact `audit_id`, exact `bundle_sha256`, consolidated state, conflict marker, conflicting decisions, full review records, and `latest_review_id`.

## Failure behavior

The command exits with code `2` and prints `INVALID: ...` when the bundle cannot be read, is invalid JSON, fails cryptographic verification, or the persisted review store detects integrity failure.

A review with incorrect bundle binding cannot enter the store through the Wave 32 review intake path and therefore cannot influence the Wave 33 consolidated status.

## Operational interpretation

`APPROVED` means only that all stored human evidence-review decisions for that exact evidence bundle are approvals. It does not mean `AUTH-CAMPAIGN-001` is satisfied and does not mean a send may occur.

`CONFLICT` requires explicit human resolution outside this read-only layer. Engineering must not invent or infer the authoritative human decision.

## CI classification

The targeted governance CI gate includes both the consolidation service tests and CLI tests. If GitHub Actions again reports `runner_id=0` with `steps=[]`, classify it as `BLK-CI-001 / CI_EXTERNAL_RUNNER_BLOCKED`; do not claim PASS and do not classify it as a product regression without executed test evidence.
