# Governance Effective Review Verification Audit Evidence — Runbook v1

## Purpose

Wave Agent 40 exports one historical Wave 39 verification-receipt audit entry as a deterministic JSON bundle that can be verified without the original SQLite database.

Schema: `effective-review-verification-audit-evidence-bundle/v1`.

This evidence is observational only. It does not authorize campaign dispatch, does not represent human approval, and does not satisfy `AUTH-CAMPAIGN-001`.

## Export

```bash
python scripts/export_governance_effective_review_verification_audit_evidence.py export \
  --audit-db verification-audit.sqlite \
  --audit-entry-id verification-audit-001 \
  --output verification-audit-evidence.json
```

The exporter verifies the full stored Wave 39 chain before selecting the target entry. The output contains the historical receipt, the selected audit entry, and the complete chain-header prefix from sequence 1 through the selected entry.

## Offline verification

```bash
python scripts/export_governance_effective_review_verification_audit_evidence.py verify \
  --bundle verification-audit-evidence.json
```

Verification checks:

- canonical `export_sha256`;
- historical receipt digest;
- exact receipt/audit-entry equality;
- exact `audit_entry_id + receipt_id + evidence_sha256` binding;
- complete exported sequence and predecessor chain;
- each audit entry hash;
- final header equality with the selected audit entry;
- receipt and audit-entry non-authorization invariants;
- top-level negative-scope invariants independently of the digest.

Any mismatch exits with code 2 and `INVALID:` on stderr.

## Governance boundary

The export remains technical evidence only. The following are always false: `send_authorized`, `evidence_is_campaign_authorization`, `evidence_is_human_approval`, `changes_auth_campaign_001`, `changes_preflight`, `changes_pilot_release`, `changes_legal_signoff`, `changes_professional_verification`, and `changes_source_freshness`.

`evidence_is_observational_only` must remain true. Recomputing `export_sha256` after changing these semantics does not make the artifact valid.
