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

- criteria: live dependency paths and compliance gates are validated
- current evidence: Wave 09 closed BrasilAPI replay/freshness, source authority, and policy boundaries; SERPRO remains partial; CFO/CRO remains human-gated
- status: PARTIAL
- blockers: remaining live certification, external dependencies, and human verification

### Commercial Pilot Ready

- criteria: qualification, contacts, compliance, and SEND_READY conditions are all satisfied
- current evidence: qualification policy, contact-use, suppression, pilot readiness, compliance policy interface, manual authorization revocation, and send-ready proof contracts are represented canonically
- status: BLOCKED_LEGAL
- blockers: `LEGAL-001`, campaign authorization, policy-required professional verification, and remaining external certification constraints

## Deferred wave status

- Wave 10: `SKIPPED_BY_OWNER / DEFERRED`
- this is not a PASS or readiness promotion
- unresolved Wave 10 external/human/legal gates remain carried forward

## Current critical-path split

Internal engineering release-candidate path: CLOSED / READY.

External/human/legal path remains open:

1. `LEGAL-001` legal/compliance sign-off;
2. campaign-specific manual authorization;
3. CFO/CRO human professional-registration verification when policy requires it;
4. SERPRO criticality/path confirmation if it remains required;
5. remaining BrasilAPI certification limitation if applicable.
