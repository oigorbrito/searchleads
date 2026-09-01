# RELEASE_READINESS

Status: CANONICAL

## Gates

### Architecture Baseline

- criteria: canonical charter, architecture, domain, data, quality, V&V, and completion plan exist
- current evidence: canonical docs are present and synchronized with the green internal regression state; Company ER and Person ER have provisional local benchmark policies; the clean implementation line is live
- status: READY
- blockers: external challenger breadth remains post-baseline and does not block the internal release-candidate path

### Integrated

- criteria: main capabilities compose and run together
- current evidence: canonical operational integration tests passed, the fallback runtime adapter is wired, the API chassis exposes health/readiness plus qualification/export surfaces, and the operational readiness harness covers startup, shutdown, backup, restore, recovery, and SEND_READY gating
- status: READY
- blockers: live Crawlee breadth remains external but does not block the internal integrated path

### Internally Verified

- criteria: internal test battery and evidence gates pass
- current evidence: Wave 14 CI run `33507553399` passed package install, installed import, RC hygiene, compile, RC/recovery, external-governance/preflight, one opt-in BrasilAPI live point revalidation on Python 3.12, and full offline regression across Python 3.11, 3.12 and 3.13; reference full result remains `909 passed, 24 skipped, 1 xpassed`
- status: PASS
- blockers: none internal; the single XPASS is an explicitly obsolete benchmark contract superseded by aggregate qualification analysis

### Operationally Ready

- criteria: startup, shutdown, recovery, observability, and deployment topology are specified and verified
- current evidence: startup, health, readiness, backup, restore, recovery, structured events, live certification planning, and deployment topology are implemented and covered by the operational regression contract
- status: READY
- blockers: commercial/live certification remains separate from service operational readiness

### Internal Release Candidate

- criteria: clean package installation, installed import, offline deterministic regression, repository hygiene, recovery contracts, explicit blocker separation, and green hardened CI
- current evidence: `RELEASE_CANDIDATE_INTERNAL_V1.md`, green Python 3.11/3.12/3.13 hardened CI, `RC_HYGIENE_READY`, targeted RC/recovery battery, cross-platform configuration tests, and experimental bake-off isolation
- status: READY
- blockers: none internal

### External Decision Intake

- criteria: legal/compliance, professional-verification and campaign-authorization decisions can be ingested with exact scope, provenance, expiry/revocation and fail-closed validation
- current evidence: Wave 13 added `ComplianceSignoffRecord`, `ProfessionalVerificationRecord`, `CampaignAuthorizationRecord`, `evaluate_campaign_preflight`, dedicated tests and CI coverage
- status: READY
- blockers: none internal; actual human decisions remain external inputs

### Externally Certified

- criteria: every source actually required by the minimum commercial path has authority, freshness and evidence requirements classified and either currently validated or explicitly candidate-specific/human-gated
- current evidence: Wave 14 executed one safe live BrasilAPI CNPJ point lookup through the product adapter on 2026-09-01T12:25:17Z; HTTP 200, required contract fields present, evidence digest `sha256:f4c55ba5ba3910bfffe1c643250c527d0b3b17732153c9b4fc0962adbeccd909`, raw payload not published. SERPRO transparency enrichment remains `NOT_REQUIRED`. CFO/CRO status remains candidate-specific human evidence only when approved campaign policy requires current professional status
- status: READY_WITH_LIMITATIONS
- limitations: BrasilAPI freshness is point-in-time and policy remains `REVALIDATE_BEFORE_USE`; CFO/CRO is conditional, person-specific, human-gated evidence

### Commercial Pilot Ready

- criteria: qualification, contacts, compliance, required external certification, suppression and SEND_READY conditions are all satisfied under an approved policy and manual campaign authorization
- current evidence: qualification policy, contact-use, suppression, pilot readiness, compliance policy interface, manual authorization revocation, send-ready proof contracts, official-source authority references, legal-review packet, campaign authority preflight, and current BrasilAPI live contract evidence are represented canonically
- status: BLOCKED_LEGAL
- blockers: `LEGAL-001`, `AUTH-CAMPAIGN-001`, conditional `EXT-CFO-001`, and a repeat of `EXT-BRASILAPI-001` immediately before any approved campaign use because freshness is not perpetual

## Deferred wave status

- Wave 10: `SKIPPED_BY_OWNER / DEFERRED`
- this is not a PASS or readiness promotion
- unresolved Wave 10 external/human/legal gates remain carried forward only where they remain on the current critical path

## External-governance authority packet

`EXTERNAL_GOVERNANCE_REVIEW_PACKET_V1.md` records the official sources observed on 2026-09-01 and the ownership boundary for each remaining decision.

Engineering decisions:

- `EXT-SERPRO-001`: `NOT_REQUIRED` for the minimum commercial path; no longer a pilot blocker
- `EXT-CFO-001`: `REVIEW_REQUIRED` by a human only when policy requires current professional status, person-specific and timestamped
- `LEGAL-001`: `REVIEW_REQUIRED` by the controller/compliance authority; engineering cannot self-approve
- `AUTH-CAMPAIGN-001`: `BLOCKED` until manual campaign authorization exists
- `EXT-BRASILAPI-001`: current live contract PASS; repeat immediately before approved use under `REVALIDATE_BEFORE_USE`

## Campaign authority preflight

Wave 13 makes the remaining decisions machine-checkable without granting them. The preflight rejects missing, expired, revoked, rejected or scope-mismatched legal signoff and authorization records. Professional verification is required only when the approved campaign policy requires current professional status. A synthetic positive fixture proves the state machine, not real-world approval.

## Wave 14 live-source observation

The product BrasilAPI adapter performed exactly one read-only point lookup in GitHub Actions. The probe did not crawl, loop, send contact data, print the raw response, or execute a campaign. The live observation is evidence of the contract at its timestamp, not blanket future certification.

## Current critical-path split

Internal engineering release-candidate path: CLOSED / READY.

External decision-intake path: CLOSED / READY.

External source certification: READY_WITH_LIMITATIONS.

Remaining minimum human/commercial path:

1. answer `LEGAL-001` through designated legal/compliance review against the exact campaign policy version;
2. perform person-specific CFO/CRO current-status verification only where the approved campaign policy requires professional status;
3. obtain campaign-specific manual authorization after the preceding gates are satisfied;
4. immediately before any approved use, repeat the bounded BrasilAPI revalidation required by freshness policy.

SERPRO transparency enrichment and Crawlee/challenger breadth are no longer on this minimum critical path.
