# PERSON_ENTITY_RESOLUTION_V1

This post-audit correction closes a formal handoff gap from section 21 (`PERSON IDENTITY`). The handoff explicitly separates Company Entity Resolution from Person Entity Resolution and states that a same-name observation is not sufficient to assume identity.

## Signals represented

The resolver represents exactly the handoff-style signals that are currently available or plausible in the domain:

- name
- company
- role
- location
- profile URL
- professional email

No weighted person score is introduced.

## Conservative V1 decision policy

```text
same normalized name only
→ INSUFFICIENT_EVIDENCE

same name + exact normalized professional profile URL
→ AUTO_MATCH

same name + exact normalized professional email
→ AUTO_MATCH

same name + company and/or role context
→ REVIEW

same name + location only
→ INSUFFICIENT_EVIDENCE
```

Contextual evidence never causes irreversible auto-merge in this V1. Exact shared email/profile without compatible human name also does not auto-match, avoiding role/shared-account false identity.

## Curated adversarial smoke benchmark

The isolated test corpus includes:

- same person with same profile URL;
- same person with same professional email;
- same person with same company/role context;
- same-name false friend inside one company;
- same-name false friend in one location;
- shared functional email across different names;
- shared company profile URL across different names;
- same-name/same-role observation across different companies.

Measured result on the 8-pair smoke corpus:

```text
AUTO_TRUE = 2
AUTO_FALSE = 0
AUTO_MATCH_PRECISION = 100.0%
REVIEW_TRUE = 2
REVIEW_FALSE = 1
DUPLICATE_COVERAGE_WITH_REVIEW = 100.0%
```

These are locally curated engineering numbers, not production person-ER accuracy.

## Validation

The new isolated person-ER suite ran:

```text
TESTS = 8/8 PASS
```

The current repository head still requires a separate full regression run; this report does not relabel isolated tests as a full-suite pass.

## Decision classification

### EVIDENCE_BACKED

- same name is insufficient for identity;
- person ER is separate from company ER;
- strong identifiers and contextual signals are distinguished.

### ENGINEERING_CHOICE

- normalized name + exact profile URL may auto-match;
- normalized name + exact professional email may auto-match;
- same-name company/role context routes to REVIEW;
- location-only context remains insufficient.

### LOCALLY_VERIFIED

- 8/8 isolated tests pass;
- no false auto-merge appears in the curated adversarial smoke corpus.

### UNKNOWN

- production precision/recall;
- cross-source person duplicate prevalence;
- whether profile/email identity rules need source-specific restrictions;
- optimal human-review cost tradeoff.

## Gate correction

```text
PERSON_ENTITY_RESOLUTION_REPRESENTED = YES
NAME_ONLY_AUTO_MATCH = NO
CONTEXT_ONLY_AUTO_MATCH = NO
STRONG_IDENTITY_SIGNAL_AUTO_MATCH = CONSERVATIVE_V1
AMBIGUOUS_PERSON_MATCH = REVIEWABLE
```
