# Company Size Registry Signal V1

Post-handoff technical extension. This work uses a field already exposed by the integrated BrasilAPI CNPJ source; it does not add a new source and does not define an ICP.

## Source contract

The current BrasilAPI CNPJ response contract documents registry size fields including:

```text
porte
codigo_porte
descricao_porte
```

The existing SERPRO source fixture already contains:

```text
porte = DEMAIS
```

## Extraction contract

Direct source mappings added:

```text
porte        -> registry_size_class
codigo_porte -> registry_size_code
```

These are raw registry classifications.

The adapter deliberately does **not** infer:

```text
employee_count
revenue
size_band
company_size
```

A blank/missing registry size is not emitted.

## Canonicalization

`registry_size_class` may be passed through the existing conservative qualification-field canonicalization rule:

```text
one observation -> canonical with source provenance
agreement -> canonical
conflict -> open Conflict
```

This does not make the registry classification equivalent to a commercial size metric.

## ICP readiness effect

Before registry size extraction:

```text
READY = 4
PARTIAL = 2
BLOCKED = 2
```

After a canonical `registry_size_class` signal:

```text
READY = 4
PARTIAL = 3
BLOCKED = 1
```

`COMPANY_SIZE` moves:

```text
BLOCKED -> PARTIAL
```

It intentionally does not become READY because the business has not decided whether registered `porte` is the desired company-size definition, and employee/revenue measures remain unavailable.

The sole BLOCKED ICP dimension is now:

```text
TARGET_MARKET
```

which is a business requirement and must not be inferred from the B2B hypothesis.

Remaining PARTIAL dimensions:

```text
GEOGRAPHY
COMPANY_SIZE
REQUIRED_CONTACTABILITY
```

Reasons:

- GEOGRAPHY: state is canonical; city remains an explicit `BRASILIA` vs `Brasília` conflict/non-canonical field.
- COMPANY_SIZE: registry classification exists, but commercial size semantics are not selected and no employee/revenue metric exists.
- REQUIRED_CONTACTABILITY: validated contact signals are qualification-consumable, but official publication/corroboration is not deliverability/reachability.

## Validation

Repository tests were extended to cover:

- direct `registry_size_class` extraction;
- optional `registry_size_code` extraction;
- blank size suppression;
- no inferred employee/revenue/size-band fields;
- conservative canonicalization of the registry class;
- PARTIAL rather than READY company-size semantics;
- readiness progression to `4 READY / 3 PARTIAL / 1 BLOCKED`.

An isolated executable contract suite for the changed size/readiness logic ran:

```text
TESTS_EXECUTED = 8
TESTS_PASSED = 8
```

The prior full technical acceptance remains separately validated at 162/162 on its acceptance branch.

## Boundary

```text
ICP_DEFINED = NO
REAL_QUALIFICATION = NOT_EVALUABLE
```

No company-size cutoff or target market is selected by this extension.
