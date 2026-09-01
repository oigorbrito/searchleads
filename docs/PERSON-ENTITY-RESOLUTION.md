# Person Entity Resolution v1

## Work unit

`PERSON_ENTITY_RESOLUTION_V1`

This unit closes the deferred cross-observation Person identity decision layer without changing WU8 discovery identity.

WU8 Person IDs remain immutable and observation-scoped:

```text
company + Evidence snapshot + ordinal + normalized name + role
```

Person ER consumes those observations later. It does not rewrite discovery IDs and it does not persist person merges.

## Evidence boundary

A `PersonRecord` preserves evidence-linked signals already available in the clean stack:

- Company relationship Evidence from the WU8 `Person`;
- `person_name` CandidateFact Evidence;
- `professional_role_title` CandidateFact Evidence;
- locally associated Person e-mail Evidence;
- locally associated Person phone Evidence;
- direct `PROFESSIONAL_PROFILE` Evidence.

The triage decision carries the union of underlying Evidence IDs. No identity decision replaces the source evidence with a name-only key.

## Comparison features

V1 exposes explicit diagnostics:

- same Company;
- normalized exact name overlap;
- normalized exact role overlap;
- exact structurally valid e-mail overlap;
- exact phone digits overlap without inventing country codes;
- exact direct LinkedIn `/in/<slug>` profile overlap;
- overlapping Company-relationship Evidence snapshots.

Name/role folding is limited to Unicode normalization, whitespace normalization, case folding and accent removal. No fuzzy-name similarity, nickname inference or title taxonomy is introduced.

Relationship-Evidence overlap is diagnostic only and never authorizes identity.

## Why no operational AUTO_MATCH

A tempting rule is:

```text
same Company
+ normalized exact name
+ exact direct professional profile
→ candidate same Person
```

That rule was evaluated explicitly rather than granted authority by intuition.

The 25-pair adversarial benchmark contains 12 true same-person pairs and 13 distinct-person pairs, including:

- changed snapshots;
- changed roles;
- accent/case name variants;
- cross-company observations;
- same-name homonyms;
- same-name/same-role homonyms;
- shared e-mail aliases;
- shared phone numbers;
- profile association with differing names;
- an adversarial same-name pair with the same misassociated direct profile.

Experimental rule result:

```text
CANDIDATE_MATCHES = 5
TRUE_POSITIVE = 4
FALSE_POSITIVE = 1
PRECISION = 80.0%
RECALL = 33.3%
FALSE_MERGE_RATE = 7.69%
```

Because false merge is non-zero, V1 does **not** authorize that rule for automatic identity.

This mirrors the project principle used in Company ER: a useful diagnostic score/rule is not automatically operational merge authority.

## Operational triage

V1 has only two operational dispositions:

- `REVIEW`
- `INSUFFICIENT_EVIDENCE`

`REVIEW` is emitted for explicit corroborating patterns such as:

- same Company + same name + same professional profile (the failed experimental auto rule is demoted to review);
- same direct profile across observations with differing name/company context;
- same name + same e-mail;
- same name + same phone;
- same name + same role;
- same e-mail + same phone even when name text differs.

These are review cues, not identity truth.

Same name alone is always insufficient. Similar names are not fuzzily merged. A shared single e-mail or phone with different names is insufficient. Different Companies are not treated as a distinct-person veto because one human may legitimately have multiple professional relationships.

## Operational benchmark

On the same 25-pair adversarial benchmark:

```text
PAIRS = 25
TRUE_SAME_PERSON = 12
TRUE_DISTINCT_PERSON = 13
AUTO_MATCHES = 0
REVIEWS = 16
INSUFFICIENT = 9
REVIEW_RATE = 64.0%
INSUFFICIENT_RATE = 36.0%
TRUE_SAME_PERSON_ROUTED_TO_REVIEW = 10/12 = 83.3%
OPERATIONAL_FALSE_MERGES = 0
```

The benchmark is intentionally adversarial and enriched for ambiguous cases. Review rate is therefore a calibration/regression result, not an estimate of production prevalence.

## Builder from existing domain records

`person_record_from_observation()` accepts existing `Person`, `CandidateFact`, and `ContactPoint` objects.

It:

- filters facts/contacts to the target Person owner/subject;
- consumes only `person_name`, `professional_role_title`, EMAIL, PHONE and PROFESSIONAL_PROFILE for V1 comparison;
- prefers a nonblank string `normalized_value` from CandidateFact when already available, otherwise raw string value;
- preserves discovery and validation Evidence IDs rather than converting contact status into identity authority;
- ignores unrelated fields/contact kinds rather than treating them as matching evidence.

A `VALIDATED` contact in WU9 means publication association, not human identity or account control, so validation status itself is not an auto-match switch.

## Deliberately not included

- name-only deduplication;
- fuzzy Person auto-match;
- nickname or transliteration inference beyond deterministic accent/case folding;
- employment inference from e-mail domain;
- social-account-control claims;
- title taxonomy;
- current-employment freshness inference;
- automatic persisted Person merges/splits;
- cross-company veto rules;
- opaque Person identity scores.

## Verification

```text
FOCUSED_TESTS = 20/20 PASS
MODULE_LINE_COVERAGE = 100%
MEASURED_STATEMENTS = 218
MEASURED_BRANCHES = 76
EXPERIMENTAL_AUTO_RULE_PRECISION = 80.0%
EXPERIMENTAL_AUTO_RULE_FALSE_MERGE_RATE = 7.69%
OPERATIONAL_AUTO_MATCH_AUTHORITY = NO
OPERATIONAL_FALSE_MERGES = 0
```

These are curated local calibration/regression metrics, not production identity accuracy.

## Gates

```text
WU8_OBSERVATION_IDS_IMMUTABLE = YES
NAME_ONLY_AUTO_IDENTITY = NO
EVIDENCE_FEATURES_EXPLICIT = YES
RELATIONSHIP_EVIDENCE_PRESERVED = YES
CONTACT_EVIDENCE_PRESERVED = YES
EXPERIMENTAL_AUTO_RULE_MEASURED = YES
EXPERIMENTAL_AUTO_RULE_FALSE_MERGE = NONZERO
OPERATIONAL_AUTO_MATCH = NO
AMBIGUOUS_TO_REVIEW = YES
PERSISTED_PERSON_MERGE = NO
ICP_DEFINED = NO
B2B_ASSUMPTION = PROVISIONAL
```
