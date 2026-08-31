# RELEASE_READINESS

Status: CANONICAL

## Gates

### Architecture Baseline

- criteria: canonical charter, architecture, domain, data, quality, V&V, and completion plan exist
- current evidence: canonical docs are present and synchronized with the green internal regression state; Company ER and Person ER now have provisional local benchmark policies; the clean implementation line is live
- status: READY
- blockers: external challenger breadth and operational runtime gaps remain open

### Integrated

- criteria: main capabilities compose and run together
- current evidence: canonical operational integration tests passed, the fallback runtime adapter is wired, the API chassis exposes health/readiness plus qualification/export surfaces, and the operational readiness harness now covers startup, shutdown, backup, restore, recovery, and SEND_READY gating
- status: READY
- blockers: live Crawlee breadth remains external, but it no longer blocks the internal integrated path

### Internally Verified

- criteria: internal test battery and evidence gates pass
- current evidence: full internal regression suite passed with `882 passed`, `24 skipped`, `1 xfailed`
- status: PASS
- blockers: skip/xfail inventory is classified; external benchmark challengers still need sanctioned runtime support

### Operationally Ready

- criteria: startup, shutdown, recovery, observability, and deployment topology are specified and verified
- current evidence: startup, health, readiness, backup, restore, recovery, structured events, live certification planning, and deployment topology are now implemented and tested locally
- status: READY
- blockers: live certification and compliance remain external

### Externally Certified

- criteria: live dependency paths and compliance gates are validated
- current evidence: none claimed
- status: NOT_YET
- blockers: live certification, external dependencies, compliance

### Commercial Pilot Ready

- criteria: qualification, contacts, compliance, and SEND_READY conditions are all satisfied
- current evidence: qualification policy exists; contact-use, suppression, and pilot readiness contracts are now represented canonically; send readiness remains separate from external authorization
- status: NOT_YET
- blockers: commercial compliance and live certification
