# WORK UNIT 10 REPORT — LEAD_QUALIFICATION_V1

## Scope

Implements a transparent qualification engine that **requires an explicit externally supplied policy**. The repository still does not define an ICP.

## Qualification semantics

```text
Company + CanonicalFact[] + explicit QualificationPolicy
→ evaluate each criterion
→ preserve criterion/fact trace
→ QUALIFIED / NOT_QUALIFIED / UNKNOWN
→ Lead with reasons + qualification fact IDs
```

Only `CanonicalFact` values are eligible. Candidate facts and unresolved/multiple canonical values do not silently satisfy qualification.

## No default ICP

```text
ICP_DEFINED = NO
DEFAULT_QUALIFICATION_POLICY = NONE
qualify_company(..., policy=None) = UNKNOWN
```

The test policy used in unit tests is synthetic and exists only to exercise engine behavior. It is not a product recommendation or inferred business ICP.

## Decision rules

- required criterion contradicted by a canonical fact → `NOT_QUALIFIED`;
- required evidence missing or unresolved → `UNKNOWN`;
- all required criteria met and explicit optional-match requirement met → `QUALIFIED`;
- every evaluation records criterion ID, predicate, canonical fact ID, actual value, and reason;
- a qualified Lead carries the explicit policy ID and supporting canonical fact IDs.

## Validation

```text
TESTS_DISCOVERED = 114
TESTS_EXECUTED = 114
TESTS_PASSED = 114
```

## Gate

```text
EXPLICIT_POLICY_ENGINE = PASS
EVIDENCE_TRACEABLE_DECISIONS = PASS
NO_POLICY_NO_QUALIFICATION = PASS
OPAQUE_DEFAULT_SCORE = NONE
ICP_DEFINED = NO
REAL_QUALIFIED_LEADS = NOT_EVALUABLE_UNTIL_ICP_DEFINED
TESTS = PASS
```

## Classification

### EVIDENCE_BACKED

Qualification references canonical evidence and explicit reasons.

### ENGINEERING_CHOICE

Declarative operators `EQ`, `IN`, `EXISTS`, `CONTAINS`; required/optional criteria; caller-supplied optional-match minimum.

### UNKNOWN / BLOCKED

- ICP criteria;
- real qualification precision/recall;
- real count of qualified leads;
- any business-specific criterion weights or thresholds.

## Next roadmap unit

`LEADS_EXPANSION_V1` can be implemented as acquisition/coverage infrastructure, but its business gate (`qualifying leads`) cannot be declared passed until an ICP/policy is explicitly defined.
