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
- current evidence: hardened CI run `33471375669` passed package install, installed import, RC hygiene, compile, targeted RC/recovery regression and full offline regression on Python 3.11, 3.12 and 3.13; reference 3.12 result is `91 passed` targeted and `894 passed, 24 skipped, 1 xpassed` full
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

### Externally Certified

- criteria: every source that is actually required by the minimum commercial path has authority, freshness and evidence requirements classified and satisfied or explicitly human-gated
- current evidence: BrasilAPI remains certified with limitations/revalidation; CFO publishes an official professional consultation surface but person-specific current status remains human-gated; the SERPRO transparency enrichment path has been reclassified `NOT_REQUIRED` for the minimum commercial path after review of the distinct official SERPRO Consulta CNPJ API/service boundary
- status: PARTIAL
- blockers: `EXT-BRASILAPI-001` fresh revalidation and `EXT-CFO-001` person-specific current-status verification when policy requires it

### Commercial Pilot Ready

- criteria: qualification, contacts, compliance, required external certification, suppression and SEND_READY conditions are all satisfied under an approved policy and manual campaign authorization
- current evidence: qualification policy, contact-use, suppression, pilot readiness, compliance policy interface, manual authorization revocation, send-ready proof contracts, official-source authority references and a canonical legal-review packet are represented
- status: BLOCKED_LEGAL
- blockers: `LEGAL-001`, `AUTH-CAMPAIGN-001`, `EXT-CFO-001` when professional status is campaign-critical, and `EXT-BRASILAPI-001` fresh source revalidation

## Deferred wave status

- Wave 10: `SKIPPED_BY_OWNER / DEFERRED`
- this is not a PASS or readiness promotion
- unresolved Wave 10 external/human/legal gates remain carried forward only where they remain on the current critical path

## External-governance authority packet

`EXTERNAL_GOVERNANCE_REVIEW_PACKET_V1.md` records the official sources observed on 2026-09-01 and the ownership boundary for each remaining decision.

Engineering decisions:

- `EXT-SERPRO-001`: `NOT_REQUIRED` for the minimum commercial path; no longer a pilot blocker
- `EXT-CFO-001`: `REVIEW_REQUIRED` by a human, person-specific and timestamped
- `LEGAL-001`: `REVIEW_REQUIRED` by the controller/compliance authority; engineering cannot self-approve
- `AUTH-CAMPAIGN-001`: `BLOCKED` until manual campaign authorization exists
- `EXT-BRASILAPI-001`: `REVIEW_REQUIRED` for fresh product-source revalidation before campaign use

## Current critical-path split

Internal engineering release-candidate path: CLOSED / READY.

Remaining minimum external/human/legal path:

1. answer `LEGAL-001` through designated legal/compliance review against the exact campaign policy version;
2. revalidate BrasilAPI source/contract freshness immediately before approved campaign use;
3. perform person-specific CFO/CRO current-status verification only where the approved campaign policy requires professional status;
4. obtain campaign-specific manual authorization after the preceding gates are satisfied.

SERPRO transparency enrichment and Crawlee/challenger breadth are no longer on this minimum critical path.
