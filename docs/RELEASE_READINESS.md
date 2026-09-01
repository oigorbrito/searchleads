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
- current evidence: last locally recorded full regression passed with `885 passed`, `24 skipped`, `1 xfailed`; Wave 11 hardened CI now requires package installation and installed import before the offline test suite
- status: PASS_WITH_CI_REVALIDATION_PENDING
- blockers: current hardened CI result pending; skip/xfail inventory remains classified

### Operationally Ready

- criteria: startup, shutdown, recovery, observability, and deployment topology are specified and verified
- current evidence: startup, health, readiness, backup, restore, recovery, structured events, live certification planning, and deployment topology are implemented and covered by the operational regression contract
- status: READY
- blockers: commercial/live certification remains separate from service operational readiness

### Internal Release Candidate

- criteria: clean package installation, installed import, offline deterministic regression, repository hygiene, recovery contracts, explicit blocker separation, and green hardened CI
- current evidence: Wave 11 added `RELEASE_CANDIDATE_INTERNAL_V1.md`, hardened CI install/import checks, and stricter local artifact/secret ignore rules
- status: VERIFICATION_PENDING
- blockers: hardened CI must complete successfully on the Wave 11 head; this execution environment cannot clone GitHub directly due DNS/network restriction

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
