# SearchLeads Commercial Pilot Runbook (v1)

**Document ID:** `docs/PILOT_RUNBOOK_V1.md`
**Purpose:** Operational execution procedure for running B2B lead generation dry-runs and preparing commercial pilot packages without making external outreach sends.

---

## 1. Operational Pre-Flight Checklist

Before executing any pilot pipeline run, the operator must verify system readiness using the pre-flight check command:

```bash
python3 -m searchleads.preflight
```

The pre-flight helper validates:
1. **System Readiness:** SQLite schema version, database connection, and operational health.
2. **Source Certification:** Required primary product-critical sources (BrasilAPI CNPJ v1) are certified and fresh.
3. **Policy Versioning:** `CampaignCompliancePolicy` is active and mapped (`policy:commercial-pilot:v1`).
4. **Legal Sign-Off:** A valid, active `ComplianceSignoffRecord` exists from legal counsel.
5. **Campaign Authorization:** A valid, active `ManualAuthorizationRecord` exists from the campaign owner.
6. **Suppression Controls:** Local suppression list is loaded and operational.
7. **Review Capability:** Review queues for Company ER, Person ER, and CFO/CRO Human Verification are accessible.

---

## 2. CFO/CRO Human Verification Workflow

For outreach targeting specific professionals (`BUSINESS_PERSONALIZED`), human verification of council registration status is required:

1. **Query Official Portal:** Manually consult the official CRO/CFO public search portal (e.g., CRO-SP, CRO-RJ).
2. **Formulate Verification Record:**
   - Record `verification_id`, `registration_number`, `council`, `subject_identity_ref`, `observed_status` (`VERIFIED` / `NOT_FOUND` / `CONFLICT`), `verified_at`, `source_reference`, and `reviewer_authority`.
   - **SAFETY RULE:** Under no circumstances store login credentials, passwords, session cookies, or CAPTCHA responses.
3. **Ingest Record:** Save the `HumanVerificationRecord` into the operational repository.

---

## 3. Pilot Dry-Run Execution Procedure

To execute a dry-run batch without network sends:

1. Load candidate corpus.
2. Execute Candidate -> Evidence -> Entity Resolution -> Relationship -> Contact Validation -> Qualification -> Compliance -> Authorization -> `SendReadyProof`.
3. Output dry-run metrics: candidate totals, AUTO_MATCH counts, review queue counts, suppression counts, and `SEND_READY` counts.
4. Export audit log (`AuditExportRecord`) for compliance archiving.

---

## 4. Emergency Kill / Stop Gate

If a policy, legal sign-off, or source certification is revoked or expired:
- Immediately revoke `ManualAuthorizationRecord` or `ComplianceSignoffRecord`.
- Re-evaluating candidates will instantly return `COMPLIANCE_BLOCKED` and halt any `SEND_READY` certification.
