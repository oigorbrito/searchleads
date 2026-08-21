# Qualification Field Canonicalization V1

Post-handoff technical extension. This work does **not** define an ICP. It applies the already-measured conservative field-fusion rule to an explicit set of qualification-relevant predicates.

## Rule

For each explicitly requested predicate:

```text
0 candidate facts -> MISSING
1 candidate fact -> CANONICAL under existing field-fusion rule
2+ equivalent effective values -> CANONICAL
2+ disagreeing effective values -> OPEN CONFLICT
```

The operation never rewrites source `CandidateFact` records and never introduces source-authority ranking.

## Qualification-relevant fields exercised

The accepted full-run already contains source evidence for:

```text
primary_cnae_code
primary_cnae_description
registration_status
```

These fields are uncontested in the acceptance fixture and therefore can be canonicalized using the existing fusion semantics.

## Measured ICP-readiness progression

Baseline acceptance:

```text
READY = 0
PARTIAL = 6
BLOCKED = 2
```

After typed qualification-signal bridge:

```text
READY = 2
PARTIAL = 4
BLOCKED = 2
```

After qualification-field canonicalization:

```text
READY = 4
PARTIAL = 2
BLOCKED = 2
```

Dimensions now READY:

```text
INDUSTRY
BUSINESS_SIGNAL
EXCLUSION_CRITERIA
TARGET_ROLE
```

Dimensions intentionally still PARTIAL:

```text
GEOGRAPHY
REQUIRED_CONTACTABILITY
```

Why they remain partial:

- `GEOGRAPHY`: state is canonical, but city remains an explicit `BRASILIA` vs `Brasília` conflict and some geography remains non-canonical. No accent/city-equivalence rule is invented here.
- `REQUIRED_CONTACTABILITY`: validated contacts are engine-consumable, but validation proves official publication/corroboration, not deliverability or reachability.

Dimensions still BLOCKED:

```text
TARGET_MARKET
COMPANY_SIZE
```

- `TARGET_MARKET` is a business decision. B2B remains a hypothesis, not an ICP.
- `COMPANY_SIZE` has no implemented evidence source/field in the accepted pipeline.

## Validation

Local isolated canonicalization/readiness suite:

```text
TESTS_EXECUTED = 11
TESTS_PASSED = 11
```

The existing field-fusion behavior is separately covered by its measured benchmark/tests; this extension only orchestrates that rule over an explicit predicate list.

## Boundary

```text
ICP_DEFINED = NO
REAL_QUALIFICATION = NOT_EVALUABLE
```

No target industry, geography, size, signal, exclusion, role or contact requirement is selected by this extension.
