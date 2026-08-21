# Work Unit 12 Report — SELECTIVE_REVIEW_V1

## Scope

Implements selective human-review routing from already-computed ambiguity/conflict signals. It does not review all records and does not alter the underlying match, contact, conflict, or qualification decision.

## Reviewable cases

- ambiguous company match (`ResolutionDisposition.REVIEW`)
- explicitly signaled ambiguous person match
- open data conflict, with optional high priority when the caller identifies the field/source context as authoritative/high impact
- uncertain contact (`DISCOVERED` or `UNKNOWN`)
- high-value qualification ambiguity (`LeadStatus.UNKNOWN` + explicit `high_value=True`)

Cases not queued:

- exact company auto-match
- resolved conflict
- validated/invalid/stale contact
- non-high-value qualification ambiguity

## Queue behavior

- deterministic stable review IDs
- duplicate review items removed
- `HIGH` before `NORMAL`
- explicit human-readable reason required
- evidence IDs retained when available
- no opaque review score

## Validation

`python -m unittest discover -s tests -v`

- `TESTS_DISCOVERED = 140`
- `TESTS_EXECUTED = 140`
- `TESTS_PASSED = 140`

## Gates

- `AMBIGUOUS_COMPANY_MATCH_REVIEW = PASS`
- `AMBIGUOUS_PERSON_MATCH_REPRESENTABLE = YES`
- `CONFLICT_REVIEW = PASS`
- `UNCERTAIN_CONTACT_REVIEW = PASS`
- `HIGH_VALUE_QUALIFICATION_REVIEW = PASS`
- `OBVIOUS_CASES_EXCLUDED = PASS`
- `SELECTIVE_NOT_UNIVERSAL = PASS`

## Classification

Review routing is an `ENGINEERING_CHOICE` aligned with the ALER direction in the supplied handoff. Priority labels are explicit categories, not calibrated probabilities.
