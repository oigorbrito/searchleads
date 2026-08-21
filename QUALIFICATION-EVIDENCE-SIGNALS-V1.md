# Qualification Evidence Signals V1

Post-handoff technical extension. This work does **not** define an ICP. It closes qualification-engine representation gaps that were measured by `ICP_DECISION_SUPPORT_V1`.

## What changed

### Explicit negative operators

`CriterionOperator` now supports:

```text
EQ
NE
IN
NOT_IN
EXISTS
NOT_EXISTS
CONTAINS
NOT_CONTAINS
```

This allows future exclusion criteria to be expressed explicitly rather than encoded indirectly or through a score.

### Typed qualification inputs

`ProfessionalRole` and `ContactPoint.VALIDATED` are not coerced into company `CanonicalFact` records. Instead, the bridge creates evidence-bearing `QualificationInput` values:

```text
professional_role_title
validated_contact_kind
validated_contact_present
```

Each input keeps its source evidence IDs.

Only `ContactPoint` values already in `VALIDATED` state can enter the qualification-signal bridge. `DISCOVERED` contacts remain ineligible.

### Multi-value semantics

For positive criteria over repeated signals (for example multiple professional roles), a match occurs when any evidence-backed value matches.

For negative criteria (`NE`, `NOT_IN`, `NOT_CONTAINS`), all observed values must satisfy the exclusion condition. This prevents one non-excluded value from hiding another explicitly excluded value.

Missing required positive evidence remains `UNKNOWN`, not `NOT_QUALIFIED`.

## Measured readiness effect

Before this bridge, against the accepted full-run fixture:

```text
READY = 0
PARTIAL = 6
BLOCKED = 2
```

After this bridge:

```text
READY = 2
PARTIAL = 4
BLOCKED = 2
```

Dimensions that became engine-ready:

```text
EXCLUSION_CRITERIA = READY
TARGET_ROLE = READY
```

`REQUIRED_CONTACTABILITY` deliberately remains `PARTIAL` because the current validation contract proves official publication/corroboration, not mailbox deliverability or phone reachability.

The remaining technical/data limitations are:

```text
INDUSTRY = PARTIAL
GEOGRAPHY = PARTIAL
BUSINESS_SIGNAL = PARTIAL
REQUIRED_CONTACTABILITY = PARTIAL
TARGET_MARKET = BLOCKED
COMPANY_SIZE = BLOCKED
```

## Validation

Local isolated bridge/readiness tests:

```text
TESTS_EXECUTED = 15
TESTS_PASSED = 15
```

The prior acceptance base remains separately validated at 162/162 tests and the decision-support extension at 10/10 isolated tests.

## Non-negotiable boundary

```text
ICP_DEFINED = NO
REAL_QUALIFICATION = NOT_EVALUABLE
```

No target market, industry, geography, size cutoff, business signal, excluded segment, target role or required contact channel is selected by this extension.
