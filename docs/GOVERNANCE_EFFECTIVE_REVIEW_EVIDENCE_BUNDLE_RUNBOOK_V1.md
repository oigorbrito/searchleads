# Governance Effective Review Evidence Bundle Runbook v1

## Purpose

Wave Agent 37 exports one historical effective human-review audit entry from the Wave 36 tamper-evident chain into a deterministic JSON artifact that can be verified offline without access to the SQLite audit database.

The artifact is observational evidence only. It does not authorize a campaign, authorize send, satisfy `AUTH-CAMPAIGN-001`, alter preflight, alter pilot release, replace legal/compliance signoff, replace professional verification, or satisfy source freshness.

## Export

```bash
python scripts/export_governance_effective_review_evidence.py export \
  --audit-db path/to/effective-review-audit.sqlite \
  --audit-entry-id effective-audit-123 \
  --output path/to/effective-review-evidence.json
```

The export verifies the complete stored Wave 36 audit chain first. It then selects the requested historical entry and includes only the chain prefix through that entry. Later audit records do not change the exported proof for an earlier entry.

## Offline verification

```bash
python scripts/export_governance_effective_review_evidence.py verify \
  --bundle path/to/effective-review-evidence.json
```

Verification does not require any database. It validates:

- schema version `effective-review-evidence-bundle/v1`;
- deterministic `evidence_sha256` over the complete unsigned artifact;
- canonical status digest against the selected audit entry;
- exact `audit_entry_id`, `audit_id`, and `bundle_sha256` binding;
- complete chain-prefix sequence and predecessor continuity;
- every audit entry hash in the exported prefix;
- final chain header equality with the selected audit entry;
- non-authorization invariants on both the bundle and historical status.

## Historical semantics

The exported `status` is the exact effective human-review status recorded at the selected audit entry. It is not recomputed from current review or resolution databases.

The `chain_headers` array starts from sequence 1 and ends at the selected entry. This allows an offline verifier to prove that the selected entry was anchored in the append-only Wave 36 chain as it existed at that sequence.

## Determinism

For unchanged audit data and the same `audit_entry_id`, repeated exports are byte-semantically deterministic after JSON canonicalization and produce the same `evidence_sha256`.

## Failure behavior

The command exits with code `2` and prints `INVALID: ...` for unreadable or invalid JSON, unknown audit entry IDs, tampered stored audit chains, bundle digest mismatch, status digest mismatch, chain discontinuity, binding mismatch, or authorization claims.

## Authority boundaries

Every valid artifact preserves:

```text
send_authorized = false
evidence_is_campaign_authorization = false
evidence_is_observational_only = true
changes_auth_campaign_001 = false
changes_preflight = false
changes_pilot_release = false
changes_legal_signoff = false
changes_professional_verification = false
changes_source_freshness = false
```

An effective review decision of `APPROVED` remains a review-domain fact only. It is not permission to dispatch or send.

## CI classification

The targeted governance CI gate includes the Wave 37 service and CLI tests. If GitHub Actions again reports jobs without executed steps (`steps=[]`), classify the run as `BLK-CI-001 / CI_EXTERNAL_RUNNER_BLOCKED`; do not claim PASS and do not infer a product regression without executed-test evidence.
