# Handoff Metrics V1

This extension implements the **measurement contract** requested by section 41 of the supplied handoff without inventing missing denominators, labels, ICP criteria, or cost telemetry.

The rule is explicit:

```text
NO DENOMINATOR / NO GROUND TRUTH / NO TELEMETRY
→ METRIC = UNAVAILABLE
```

An unavailable metric carries a reason instead of a fabricated zero or estimate.

## Discovery

Represented:

- company coverage;
- discovery precision;
- duplicate discovery rate.

`duplicate discovery rate` is measurable from discovery observations alone.

`company coverage` requires an explicit company universe/denominator.

`discovery precision` requires explicit relevance ground truth.

## Entity Resolution

Represented from a labeled confusion matrix:

- precision;
- recall;
- F1;
- false merge rate;
- false split rate.

The false-split rate is explicitly represented as:

```text
FN / (TP + FN)
```

This does not alter the conservative company/person merge policies.

## Enrichment

Represented:

- field coverage;
- field accuracy;
- provenance coverage;
- conflict rate.

`field coverage` requires an explicit list of company IDs and required predicates.

`field accuracy` is unavailable unless caller-supplied labeled field truth exists.

`provenance coverage` measures facts that actually carry Evidence IDs.

`conflict rate` is measured over canonical/conflicting subject-predicate groups actually evaluated.

## Contacts

Represented:

- contact discovery rate;
- validation rate;
- invalid rate;
- stale rate.

Immutable DISCOVERED/VALIDATED snapshots of the same logical contact are collapsed by owner + kind + normalized contact value, selecting the latest state by provenance timestamp. Equal-timestamp snapshots prefer the more conclusive state.

This does not change validation semantics: `VALIDATED` still means official-publication corroboration, not deliverability.

## Qualification

Represented:

- qualification precision;
- qualification recall;
- human disagreement rate.

Current project state remains:

```text
ICP_DEFINED = NO
REAL_QUALIFICATION = NOT_EVALUABLE
```

Therefore qualification precision/recall remain `UNAVAILABLE` until an explicit ICP plus labeled business ground truth exists.

Human disagreement rate also remains unavailable unless human review decisions are supplied.

## Operation

Represented:

- cost per discovered company;
- cost per enriched company;
- cost per qualified lead;
- cost per validated contact;
- time per lead.

These values are computed only from explicitly supplied total-cost / elapsed-time telemetry and explicit counts. No default currency, labor rate, API cost, or runtime estimate is assumed.

## Validation

Isolated executable contract:

```text
TESTS_DISCOVERED = 11
TESTS_EXECUTED = 11
TESTS_PASSED = 11
```

Coverage includes unavailable metrics, explicit denominator behavior, ER false split, enrichment/provenance/conflict rates, logical-contact snapshot dedupe, qualification ground truth, human disagreement, and operation telemetry.

## Decision classification

### EVIDENCE_BACKED

- metrics require explicit evidence/labels/denominators where appropriate;
- unavailable data is represented as unavailable, not guessed.

### ENGINEERING_CHOICE

- typed `MetricValue` with `AVAILABLE` / `UNAVAILABLE`;
- logical contact dedupe key and latest-state selection;
- conflict-rate denominator over evaluated canonical/conflicting field groups.

### UNKNOWN / NOT YET MEASURABLE

- production company universe and discovery coverage;
- production discovery precision;
- production field accuracy;
- qualification precision/recall before ICP + ground truth;
- human disagreement before review labels;
- operational cost/time until telemetry is supplied.
