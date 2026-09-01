# Commercial Pilot Compliance Sign-Off Package (v1)

**Document ID:** `docs/COMMERCIAL_PILOT_COMPLIANCE_SIGNOFF_V1.md`
**Target Domain:** Outbound Lead Discovery & Commercial Qualification
**Jurisdiction:** Brazil (BR)
**Channel:** Commercial B2B Electronic Mail (Email)
**Campaign Policy Version:** `policy:commercial-pilot:v1`
**Current Administrative State:** `REVIEW_REQUIRED` (Pending Legal Reviewer Signature)

---

## 1. Campaign Scope & Parameters

| Attribute | Specification |
| :--- | :--- |
| **Campaign ID** | `campaign:dental-pilot-v1` |
| **Target Sector / ICP** | Dental Clinics & Facial Surgery Practices (BR) |
| **Channel** | B2B Professional Email (`email`) |
| **Jurisdiction** | Federative Republic of Brazil |
| **Approved Contact Classes** | `COMPANY_GENERIC` (contact@), `BUSINESS_PERSONALIZED` (dr.firstname@clinic.com) |
| **Prohibited Contact Classes** | `PERSONAL` (@gmail.com, @hotmail.com, personal mobile) |

---

## 2. Legal Basis & Jurisdiction Analysis

Under Brazil's **Lei Geral de Proteção de Dados (LGPD - Lei 13.709/2018)**:
- **Primary Legal Basis Candidate:** Legitimate Interest (Art. 7, IX, LGPD) / B2B Commercial Inquiry.
- **Balancing Test Safeguards:**
  - Strict limitation to published B2B business contact channels.
  - Transparent provenance tracking for all captured facts.
  - Granular opt-out and suppression enforcement (`SuppressionRule`).
  - No personal sensitive data or direct consumer marketing.

---

## 3. Contact Provenance & Technical Safeguards

1. **Source Authority:** Primary registry facts derived exclusively from certified sources (BrasilAPI CNPJ v1).
2. **Professional Verification Boundary:** CFO/CRO professional registration verification required for personalized professional outreach (`HumanVerificationRecord`).
3. **Suppression Controls:** Automated check against `SuppressionRule` database prior to `SEND_READY` certification.
4. **Two-Key Authority Model:** Requires both `ComplianceSignoffRecord` (Legal) AND `ManualAuthorizationRecord` (Campaign Owner).

---

## 4. Legal Decision Interface (`ComplianceSignoffRecord`)

To ingest formal approval or rejection into the system, the legal reviewer/policy owner completes a decision record in the following format:

```json
{
  "signoff_id": "signoff:commercial-pilot:v1:20260831",
  "review_authority": "legal.counsel@organization.test",
  "policy_version": "policy:commercial-pilot:v1",
  "jurisdiction": "BR",
  "channel": "email",
  "decision": "APPROVED",
  "approved_contact_classes": ["COMPANY_GENERIC", "BUSINESS_PERSONALIZED"],
  "conditions": [
    "Must enforce immediate opt-out upon request",
    "Must verify active CRO registration for personalized doctor outreach"
  ],
  "reviewed_at": "2026-08-31T12:00:00Z",
  "reference": "LEGAL-OPINION-2026-001",
  "expires_at": "2027-08-31T12:00:00Z"
}
```

Available `decision` states:
- `APPROVED`
- `APPROVED_WITH_CONDITIONS`
- `REJECTED`
- `MORE_REVIEW_REQUIRED`

*Note: The automated software agent DOES NOT auto-populate `APPROVED` on behalf of human legal counsel.*
