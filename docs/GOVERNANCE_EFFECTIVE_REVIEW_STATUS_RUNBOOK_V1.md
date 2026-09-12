# Governance Effective Evidence Review Status Runbook v1

## Purpose

Wave Agent 35 adds one read-only effective human-review view for an exact verified governance evidence bundle. It combines the unanimous consolidated review state from Wave 33 with explicit conflict resolutions from Wave 34.

This view is observational only. It does not authorize send, authorize a campaign, satisfy `AUTH-CAMPAIGN-001`, alter preflight, alter pilot release, replace legal/compliance signoff, replace professional verification, or satisfy source freshness.

## Command

```bash
python scripts/show_governance_effective_review_status.py \
  --bundle path/to/governance-evidence-bundle.json \
  --review-db path/to/evidence-reviews.sqlite \
  --resolution-db path/to/evidence-review-resolutions.sqlite
```

The bundle is verified through the existing review/resolution stack before an effective state is returned.

## Effective states

- `NO_REVIEW`: no review exists for the exact bundle.
- `EFFECTIVE_REVIEW_DECISION`: all persisted reviews agree; the decision source is `CONSOLIDATED_REVIEWS`.
- `EFFECTIVE_RESOLVED_DECISION`: contradictory reviews exist and one non-conflicting explicit human resolution applies to the exact current review set; the source is `HUMAN_CONFLICT_RESOLUTION`.
- `UNRESOLVED_CONFLICT`: contradictory reviews exist and no applicable resolution exists.
- `STALE_RESOLUTION`: a prior resolution exists but is no longer bound to the exact current review set.
- `RESOLUTION_CONFLICT`: multiple applicable human resolutions disagree.

Only the two `EFFECTIVE_*` states expose `effective_decision`. All unresolved/stale/conflicting states fail closed with `effective_decision = null`.

## Decision provenance

Every effective decision includes an explicit `decision_source`:

- `CONSOLIDATED_REVIEWS`
- `HUMAN_CONFLICT_RESOLUTION`

When no effective decision exists, `decision_source = NONE`.

The output also exposes the exact `review_ids`, applicable resolution IDs, and stale resolution IDs.

## Governance invariants

Every output preserves:

```text
send_authorized = false
review_is_campaign_authorization = false
changes_auth_campaign_001 = false
changes_preflight = false
changes_pilot_release = false
changes_legal_signoff = false
changes_professional_verification = false
changes_source_freshness = false
status_is_observational_only = true
```

An `APPROVED` effective review decision means only that the evidence-review domain currently resolves to approval. It is not campaign authorization and cannot be interpreted as permission to dispatch or send.

## Failure behavior

Tampered or invalid bundles fail closed. Integrity failures in review or resolution persistence also prevent effective status production.

## CI classification

The targeted governance CI gate includes the Wave 35 service and CLI tests. If GitHub Actions reports jobs with `runner_id=0` or no executed steps (`steps=[]`), classify the result as `BLK-CI-001 / CI_EXTERNAL_RUNNER_BLOCKED`. Do not claim PASS and do not infer product regression without executed test evidence.
