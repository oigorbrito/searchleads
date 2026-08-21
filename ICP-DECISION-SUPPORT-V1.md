# ICP Decision Support V1

This is a post-handoff decision-support extension. It does **not** define an ICP and does not change the rule that real lead qualification remains blocked until business requirements are supplied.

The handoff requires the future ICP to answer eight dimensions:

- TARGET MARKET
- INDUSTRY
- GEOGRAPHY
- COMPANY SIZE
- BUSINESS SIGNAL
- EXCLUSION CRITERIA
- TARGET ROLE
- REQUIRED CONTACTABILITY

## Measurement basis

The readiness snapshot is the deterministic `END_TO_END_ACCEPTANCE_V1` fixture, not a population sample and not a production-accuracy estimate.

Observed acceptance evidence:

- canonical facts: `business_registry_id`, `state`
- candidate facts include legal/trade name, registration status, primary CNAE, city/state, address, postal code and activity-start date
- unresolved city conflict: `BRASILIA` vs `Brasília`
- evidence-backed professional roles: 1
- corroborated contact kinds: EMAIL and PHONE
- current qualification operators: EQ, IN, EXISTS, CONTAINS
- deliverability/reachability verification: NO

## Readiness result

```text
ICP_DIMENSIONS = 8
READY = 0
PARTIAL = 6
BLOCKED = 2
ICP_DEFINED = NO
```

| ICP dimension | Readiness | Why |
|---|---|---|
| TARGET MARKET | BLOCKED | B2B remains a hypothesis; no market/segment criterion was supplied or inferred. |
| INDUSTRY | PARTIAL | CNAE evidence exists, but is not canonical in the accepted qualification path. |
| GEOGRAPHY | PARTIAL | State is canonical, while city remains an explicit unresolved conflict and some geography is candidate-only. |
| COMPANY SIZE | BLOCKED | No company-size evidence/source is implemented. |
| BUSINESS SIGNAL | PARTIAL | Registration status exists as source evidence but is not qualification-ready; broader signals are not implemented. |
| EXCLUSION CRITERIA | PARTIAL | Current engine has positive operators only; generic negative/exclusion semantics are not first-class. |
| TARGET ROLE | PARTIAL | ProfessionalRole evidence exists, but the qualification engine currently evaluates CanonicalFact only. |
| REQUIRED CONTACTABILITY | PARTIAL | Validated ContactPoint evidence exists, but is not directly consumable by qualification; validation proves official publication/corroboration, not deliverability. |

## Interpretation

`READY = 0` does **not** mean the pipeline is unusable. It means no complete ICP dimension should be silently promoted to a commercial rule from the current acceptance fixture.

Six dimensions already have evidence or engine capability that can be extended without choosing a commercial target. Two dimensions require information that does not exist in the current system:

1. TARGET MARKET is a business decision.
2. COMPANY SIZE needs an explicit source/data requirement before it can be measured.

## Technical gaps that can be closed without defining the ICP

1. Canonicalize qualification-relevant single-source fields such as CNAE and registration status while preserving provenance.
2. Add explicit negative qualification operators for exclusion policies.
3. Introduce evidence-backed qualification signals for ProfessionalRole and validated ContactPoint instead of coercing them into company facts.
4. Preserve the current contactability semantics: officially corroborated contact presence is not deliverability.

None of those changes supplies target values, thresholds, segment choices, target roles, required contact channels, or company-size cutoffs.

## Gate

```text
ICP_DECISION_SUPPORT = PASS
ICP_DIMENSIONS_MEASURED = 8
READY = 0
PARTIAL = 6
BLOCKED = 2
ICP_DEFINED = NO
REAL_QUALIFICATION = NOT_EVALUABLE
```

Run:

```bash
python scripts/run_icp_decision_support.py
```
