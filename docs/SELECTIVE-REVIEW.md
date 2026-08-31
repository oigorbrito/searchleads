# Selective Review v1

## Work unit

`SELECTIVE_REVIEW_V1`

This work unit converts **already-computed ambiguity or conflict states** into a small auditable human-review queue. It does not alter the underlying ER, conflict, contact, Person, or qualification state and does not invent a second matching/truth model.

## Principle

```text
obvious outcome → no review
explicit ambiguity / unresolved high-impact state → review item
review item → human work, not automatic adjudication
```

No probability, confidence score, weighted ambiguity score, or hidden threshold is used by V1 review routing.

## Reviewable signals

### Company match

Only `ResolutionDisposition.REVIEW` from WU5 creates a company-match review item.

The following remain outside the queue:

- `AUTO_MATCH`;
- `DISTINCT`;
- `INSUFFICIENT_EVIDENCE`.

The review item carries the two observation IDs and the explicit WU5 triage reasons. Review does not change or reproduce the ER decision.

### Person identity

Person review is explicit because Person Entity Resolution is still deferred.

V1 requires:

- two distinct Person observation IDs;
- one Company ID;
- an explicit human-readable ambiguity reason;
- at least one Evidence ID.

Therefore same-name observations alone cannot generate a review item without evidence/context.

### Data conflict

Only `ConflictStatus.OPEN` is reviewable. `RESOLVED` and `DEFERRED` conflicts are not requeued.

The review record preserves:

- subject ID;
- conflict ID;
- all candidate-fact IDs;
- evidence IDs supplied by the caller when available.

A caller may mark a conflict `high_impact=True`; this changes queue priority to `HIGH`, not the truth value of any candidate.

### Contact

Only `DISCOVERED` and `UNKNOWN` contacts are reviewable. `VALIDATED`, `STALE`, and `INVALID` contacts are terminal/non-ambiguous for this routing unit and are excluded.

Discovery and validation Evidence IDs are unioned into the review item when available.

### Qualification

The clean stack does not yet define an ICP/qualification engine. WU11 therefore does not create qualification results.

It may route an existing `Lead` only when:

- `qualification_status == UNKNOWN`; and
- the caller explicitly marks the case `high_value=True`.

This creates a `HIGH` review item while preserving the Lead's `UNKNOWN` status. Qualified/not-qualified records and unknown low-value cases are not queued.

## Review item contract

Each `ReviewItem` contains:

- deterministic `review_id`;
- categorical `kind`;
- categorical `priority` (`HIGH` / `NORMAL`);
- related record IDs;
- explicit reason;
- sorted unique Evidence IDs where available.

Review identity intentionally excludes priority/evidence count. If the same semantic review arrives twice, queue construction:

- deduplicates it;
- unions Evidence IDs;
- promotes `NORMAL` to `HIGH` if any copy is high priority.

A manual `review_id` collision across different semantic contents is rejected rather than silently merging unrelated work.

## Ordering

Queue order is deterministic:

```text
HIGH
→ NORMAL
→ kind
→ stable review_id
```

This is an engineering ordering, not a calibrated risk score.

## Curated routing benchmark

The deterministic fixture contains 19 scenarios spanning company ER dispositions, explicit Person ambiguity, conflict states, contact states, and existing Lead qualification states.

Measured routing:

```text
SCENARIOS = 19
TRUE_REVIEW = 8
FALSE_REVIEW = 0
TRUE_NO_REVIEW = 11
MISSED_REVIEW = 0
HIGH_PRIORITY_TRUE_REVIEW = 2
PRECISION = 100.0%
RECALL = 100.0%
OBVIOUS_CASE_FALSE_REVIEW = 0/11
```

These are curated routing-contract metrics, not human-review productivity, model accuracy, operational prevalence, or business-value estimates.

## Verification

```text
WU11_FOCUSED_TESTS = 31/31 PASS
WU11_MODULE_LINE_COVERAGE = 100%
WU11_MEASURED_STATEMENTS = 109
SELECTIVE_REVIEW_BENCHMARK = PASS
PYTHON_MODULE_COMPILE = PASS
```

The module uses only contracts already present in the clean stack (`Conflict`, `ContactPoint`, `Lead`, `CompanyRecord`, `TriageDecision`) and does not change persistence/domain schemas.

## Gates

```text
COMPANY_ER_REVIEW_ROUTED = PASS
AUTO_MATCH_REVIEWED = NO
DISTINCT_REVIEWED = NO
INSUFFICIENT_ER_REVIEWED = NO
PERSON_REVIEW_REQUIRES_EVIDENCE = YES
OPEN_CONFLICT_REVIEW = PASS
RESOLVED_OR_DEFERRED_CONFLICT_REVIEW = NO
DISCOVERED_OR_UNKNOWN_CONTACT_REVIEW = PASS
TERMINAL_CONTACT_REVIEW = NO
HIGH_VALUE_UNKNOWN_QUALIFICATION_REVIEW = PASS
QUALIFICATION_STATUS_MUTATED = NO
DUPLICATE_REVIEW_WORK = CONSOLIDATED
EVIDENCE_UNION_ON_DUPLICATES = PASS
HIGH_PRIORITY_PROMOTION = PASS
OPAQUE_REVIEW_SCORE = NO
CURATED_PRECISION = 100.0%
CURATED_RECALL = 100.0%
FOCUSED_TESTS = 31/31 PASS
LINE_COVERAGE_NEW_MODULE = 100%
ICP_DEFINED = NO
B2B_ASSUMPTION = PROVISIONAL
```

## Next work unit

The next original-handoff unit should be audited after this review-routing boundary is published.
