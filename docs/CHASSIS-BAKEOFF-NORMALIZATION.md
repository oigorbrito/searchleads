# Chassis Bake-Off — Normalization V1

Status: `EXPERIMENTAL_PROTOCOL`.

This document defines normalization and identifier-validation questions for the chassis bake-off. It is not production authority and it does not identify a winner.

The canonical methodological vocabulary is defined in `EMPIRICAL-HARNESS-METHODOLOGY.md`.

## Research questions

1. How do deterministic name-normalization strategies differ on the declared adversarial corpus?
2. Does changing only name normalization alter downstream Company ER behavior under a controlled ablation?
3. Does SearchLeads CNPJ handling satisfy the current formal validity contract, distinct from formatting/canonicalization?

Normalization is feature engineering. A normalized string is never entity identity and cannot by itself authorize a merge, canonical fact, Lead qualification, or contact-validation state.

## Evidence classes

Use current evidence classes rather than legacy `ENGINEERING_EVIDENCE`/`LOCAL_EXPERIMENT` labels:

- official CNPJ specification/examples: external authority for the identifier contract, not a benchmark result;
- library/API/source inspection: `STATIC_INSPECTION`;
- deterministic executable behavior checks: `FUNCTIONAL_PROBE`;
- repeated comparable name/ER measurements under a declared workload: `CONTROLLED_BENCHMARK` when the protocol requirements are satisfied.

A curated fixture is not independent market ground truth.

## Current SearchLeads architectural duplication

The current company-name field normalizer and current company ER do not share one normalization implementation:

- `searchleads.normalization._normalize_company_name` performs NFKC plus whitespace normalization and preserves case/accents;
- `searchleads.entity_resolution.company._fold` independently performs NFKC, whitespace normalization, casefold, NFKD decomposition, and combining-mark removal.

This is a static architectural observation. It supports a hypothesis that one explicit normalization contract could reduce duplication. It does not establish that any challenger improves ER quality.

## Company-name strategies under evaluation

The frozen protocol compares deterministic strategies over the same declared corpus, including:

1. current SearchLeads NFKC/whitespace projection;
2. Rigour `normalize_name`;
3. explicit Rigour NFKD/casefold/name pipeline;
4. the same folded representation with organization-type removal.

The corpus contains representation-equivalent pairs and distinct controls, including case, accent, punctuation, whitespace, Unicode composition/compatibility, format characters, legal forms, near spellings, geography, numeric tokens, extra tokens, and collision guards.

### Metrics

When defensible labels exist for the frozen corpus, the protocol may report:

- TP / FP / TN / FN;
- precision;
- recall;
- F0.5 when the research question explicitly assigns higher cost to false collisions;
- false-collision rate;
- Matthews correlation coefficient;
- error counts by declared perturbation category.

These are fixture-scoped measurements. They are not production-accuracy estimates.

No result may be summarized as `winner`, `better`, or `best` without a bounded claim that names the metric, workload, environment, and validity limits.

## Downstream ER ablation

`test_chassis_bakeoff_normalization_er_impact.py` changes the name representation while holding other Company ER behavior fixed as far as the protocol declares:

- registry rules unchanged;
- domain feature unchanged;
- phone feature unchanged;
- address feature unchanged;
- location feature unchanged;
- CNAE feature unchanged;
- weighting unchanged.

Only the name-related representation/similarity path is intended to vary.

The protocol may evaluate both a fixed historical threshold and a threshold selected from a calibration partition then applied to holdout data. Any threshold selection procedure must be recorded and must not be changed after observing holdout outcomes to favor a candidate.

Registry conflict remains a hard negative where the product policy defines it as such.

## CNPJ correctness boundary

CNPJ canonicalization and CNPJ validity are separate operations.

Current SearchLeads `_normalize_cnpj` compacts and canonicalizes a shaped identifier. Shape acceptance alone is not checksum validation.

The experiment compares:

1. a reference implementation of the declared Receita/Serpro validity algorithm;
2. current SearchLeads CNPJ canonicalization behavior;
3. the pinned external validation path through Rigour/python-stdnum.

The official specification remains the authority for the identifier contract. An external library is evaluated against that contract; it does not become authoritative merely because it is a challenger.

A source value may be preserved/canonicalized while failing validation. Validation must not erase raw Evidence.

## Claim boundaries

Supported static/correctness conclusions may include:

- SearchLeads currently has duplicated name-normalization logic in separate paths;
- canonicalization is not equivalent to formal CNPJ validity checking;
- a candidate library exposes specific normalization or validation APIs.

The following require controlled empirical evidence and raw observations:

- a normalization strategy improves downstream ER;
- a strategy reduces false collisions under a workload;
- one strategy has higher precision/recall under a declared dataset;
- a strategy should replace another in production.

The following are not authorized from a curated fixture alone:

- market-wide ER accuracy;
- universal normalization superiority;
- production false-merge rate;
- production adoption.

## Acceptance and rejection criteria

Before an active production recommendation, the study must preserve:

- complete SearchLeads regression outcome;
- environment manifest;
- raw JUnit execution evidence;
- raw structured observations for metrics not represented by JUnit;
- declared corpus identity/hash where applicable;
- false-collision outcomes, not only positive invariance;
- downstream ER effects when ER benefit is claimed;
- current official CNPJ contract cases when identifier correctness is claimed;
- explicit validity limits and threats.

A required missing artifact causes the current claim state to become `INSUFFICIENT_EVIDENCE` in the canonical report.

## Decision semantics

Historical decisions about normalization or identifier validation may remain documented elsewhere as engineering decisions. This experiment does not convert them into `SUPPORTED` evidence merely by executing probes.
