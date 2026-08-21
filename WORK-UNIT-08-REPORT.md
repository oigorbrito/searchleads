# WORK UNIT 08 REPORT — CONTACT_VALIDATION_V1

## Scope

This work unit defines one explicit non-invasive contact-validation method: **official-publication corroboration**. The same contact must be observed in at least two official page observations for the already-associated company. This validates the published company/contact association, not mailbox deliverability or phone reachability.

## Method

```text
DISCOVERED ContactPoint
+ original official Evidence
+ corroborating official Evidence
→ structural check
→ exact kind/value equivalence
→ >= 2 official observations
→ separate VALIDATED ContactPoint snapshot
```

A later snapshot of the same official locator may count as the second observation when its retrieval time is strictly newer. A non-official page does not promote state. Absence from a later page yields `UNKNOWN`, not `STALE`, because page absence alone is not evidence of invalidation.

## State semantics

- `DISCOVERED`: observed once; no validation inference.
- `VALIDATED`: official publication/association corroborated by >=2 official observations.
- `INVALID`: structurally impossible value for its contact kind.
- `UNKNOWN`: evidence is insufficient for validation.
- `STALE`: not assigned by this V1 method.

`deliverability_verified` is always `False` in this work unit.

## Real-company calibration

Current official Serpro pages checked on 2026-08-21 publish the same CSS channels on multiple distinct official pages:

- `css.serpro@serpro.gov.br`
- `0800 728 2323`

Both appear on at least the customer-help page, support FAQ, and another current Serpro support page. Therefore:

```text
REAL_CONTACTS_CORROBORATED = 2
EMAIL_OFFICIAL_PAGE_OBSERVATIONS >= 3
PHONE_OFFICIAL_PAGE_OBSERVATIONS >= 3
DELIVERABILITY_VERIFIED = 0
```

## Validation

```text
TESTS_DISCOVERED = 94
TESTS_EXECUTED = 94
TESTS_PASSED = 94
```

Tests cover two-page validation, same-page later reconfirmation, non-official evidence rejection, one-observation `UNKNOWN`, absence not implying stale, structural invalidity, immutable discovered/validated snapshots, persistence round-trip, and missing references.

## Gate

```text
VALIDATION_METHOD_EXPLICIT = PASS
VALIDATION_METHOD_NON_INVASIVE = PASS
REAL_CONTACTS_VALIDATED_BY_METHOD > 0 = PASS (2)
DISCOVERED_DISTINCT_FROM_VALIDATED = PASS
DELIVERABILITY_CLAIMED = NO
TESTS = PASS
```

## Decision classification

### LOCALLY_VERIFIED

- two current Serpro contact values are corroborated across multiple official pages;
- validation state transitions and persistence pass the local suite.

### ENGINEERING_CHOICE

- official cross-page corroboration as V1 validation scope;
- two observations as the minimum;
- no active e-mail send, SMTP mailbox probing, phone call, or form submission.

### UNKNOWN

- inbox deliverability;
- telephone reachability;
- current human ownership;
- optimal stale-contact policy;
- production precision/recall of this validation definition.

## Next work unit

Per roadmap: `PERSON_DISCOVERY_AND_COMPANY_LINK_V1`.
