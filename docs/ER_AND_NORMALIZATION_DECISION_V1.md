# ER_AND_NORMALIZATION_DECISION_V1

Status: `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT`; GitHub-hosted runners still terminate with `steps=[]` / no usable logs, so quality numbers are not claimed as executed results.

## Scope

This decision covers company ER, person ER, normalization, identifier validation, and the benchmark harness quality checks that gate them.

## What was inspected

The current harness already separates the relevant questions:

- `tests/experimental/test_chassis_bakeoff_matching.py`
- `tests/experimental/test_chassis_bakeoff_nomenklatura_algorithms.py`
- `tests/experimental/test_chassis_bakeoff_external_canonical.py`
- `tests/experimental/test_chassis_bakeoff_external_regression.py`
- `tests/experimental/test_chassis_bakeoff_normalization.py`
- `tests/experimental/test_chassis_bakeoff_normalization_er_impact.py`
- `tests/experimental/test_chassis_bakeoff_cnpj.py`
- `tests/experimental/test_chassis_bakeoff_dependency_contract.py`

Static audit findings:

- Company ER and Person ER are kept separate in the harness, which is correct.
- The holdout/calibration split is explicit in the company fixtures, which is correct.
- The SearchLeads baseline is not treated as an untouchable winner in the assertions, which is correct.
- The external canonical regression fixture is held out from the matcher inputs, which is correct.
- The CNPJ probe already distinguishes canonicalization from validation, which is correct.
- The normalization ablation holds the matcher constant and varies only name normalization, which is correct.
- No runner-produced benchmark number is available yet, so no ER winner can be claimed.

## Decision matrix

| Component | Current SearchLeads | Candidate | Decision | Why |
|---|---|---|---|---|
| Company ER | baseline matcher/feature fusion | Nomenklatura `LogicV2`, `RegressionV1`, `EntityResolveRegression` and challengers | `DEFER` | the comparison harness is structurally sound, but no executed benchmark result exists yet |
| Person ER | baseline person resolution | separate Person ER benchmark with strict false-merge cost | `DEFER` | person false merges are high-impact, but there is no executed person benchmark result yet |
| Normalization boundary | duplicated SearchLeads normalizers | Rigour-based normalization boundary with explicit legal-form policy | `COMPOSE` | the current duplicate boundary is unnecessary; one shared normalization layer is the right semantic split |
| CNPJ validation | shape-only canonicalization in parts of the stack | formal validation using `python-stdnum` / official Receita-Serpro contract | `REPLACE` | shape-only acceptance is not validation and allows bad routing keys to reach acquisition |

## Normalization decision

The winning architectural boundary is not "SearchLeads string munging everywhere" and it is not "normalization becomes identity".

The correct split is:

```text
raw source value
    -> normalization feature / canonical display key
    -> ER feature input
    -> entity identity decision (separate step)
```

That means:

- SearchLeads should keep raw values and Evidence intact;
- Rigour should own the explicit normalization contract where it is the better library;
- legal-form stripping must remain a measured policy choice, not a blanket rule;
- normalized strings must never authorize merge, qualification, or contact reuse by themselves.

This is a `COMPOSE` decision, not a blanket replacement of all SearchLeads text handling.

## CNPJ decision

The current `searchleads.gap_automation.planning._normalize_cnpj` behavior is only canonicalization. It does not reject invalid check digits.

That is insufficient for planner/runtime admission control.

The right boundary is:

- preserve and normalize the source value for auditability;
- validate against the official CNPJ contract before dispatching network acquisition;
- reject invalid CNPJ values early so the planner does not create avoidable requests;
- keep raw Evidence separate from the validation result.

This is a `REPLACE` decision.

## Harness quality checks

The harness is structurally acceptable because it already encodes the right separations:

- train/calibration/evaluation are not conflated;
- SearchLeads baseline and challenger are compared on the same labeled pairs;
- external canonical data is not fed to the matcher as a feature;
- normalization ablation keeps non-name features fixed;
- CNPJ canonicalization is tested against an official oracle and a routing-key scenario.

What is missing is execution. Therefore:

- the harness can be trusted as a protocol;
- the benchmark result cannot yet be trusted as an outcome;
- company/person ER remain open until the runner returns.

## Claims table

| Claim | Evidence available | Execution required? | Decision possible now? | Confidence |
|---|---|---|---|---|
| SearchLeads normalization duplicates logic | static code/docs inspection | no | yes | high |
| Rigour should be the shared normalization boundary | static code/docs inspection | no | yes | medium |
| CNPJ shape-only acceptance is not validation | static code/docs inspection + official contract | no | yes | high |
| SearchLeads normalization winner vs Rigour winner | benchmark harness only | yes | no | low |
| SearchLeads company ER winner | benchmark harness only | yes | no | low |
| SearchLeads person ER winner | benchmark harness only | yes | no | low |

## Current decision

- `Normalization` = `COMPOSE`
- `Identifier validation` = `REPLACE`
- `Company ER` = `DEFER`
- `Person ER` = `DEFER`

## Implication for implementation

Do not start a new clean implementation line yet.

The normalization and validation boundaries are closed enough to wire into the eventual implementation, but the ER quality choice that could still change the chassi remains benchmark-dependent and unexecuted.

The next executable gate is the same harness on a working runner, starting with the company ER and person ER comparisons.
