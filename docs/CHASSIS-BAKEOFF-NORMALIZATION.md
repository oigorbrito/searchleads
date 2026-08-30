# Chassis Bake-Off — Normalization V1

## Decision rule

SearchLeads normalization is a baseline, not a protected design. Rigour 1.4.0 is a challenger, not an assumed winner.

Normalization is evaluated as feature engineering. A normalized string is never entity identity and cannot, by itself, authorize a merge, canonical fact, qualified Lead, or contact validation state.

## Evidence classes

- `OFFICIAL_SPEC`: Receita Federal / Serpro current CNPJ alphanumeric specification and published examples.
- `ENGINEERING_EVIDENCE`: Rigour 1.4.0 public normalization APIs, organization-type reference database, tests and implementation.
- `LOCAL_EXPERIMENT`: frozen SearchLeads adversarial name corpus and CNPJ challenger probes in this PR.
- `HYPOTHESIS`: any proposed production replacement before the GitHub runner actually executes the benchmark.

No scientific-performance claim is made from the curated fixture alone.

## Company-name challengers

The benchmark compares four deterministic strategies over the same 44-pair frozen corpus:

1. `searchleads_nfkc_whitespace_v1`
   - current SearchLeads company-name projection;
   - Unicode NFKC + whitespace collapse;
   - preserves case and accents.
2. `rigour_normalize_name_1_4_0`
   - Rigour public `normalize_name` convenience key;
   - Unicode casefold + name tokenization.
3. `rigour_nfkd_casefold_name_1_4_0`
   - explicit `NFKD | CASEFOLD | NAME` pipeline;
   - tests whether compatibility decomposition and casefold improve representation invariance.
4. `rigour_nfkd_casefold_name_strip_org_type_1_4_0`
   - same folded key plus Rigour organization-type removal;
   - tests the recall/collision trade-off of dropping legal-form tokens.

The corpus has 20 representation-equivalent pairs and 24 distinct controls. It includes case, accent, punctuation, whitespace, Unicode compatibility/composition, invisible format characters, legal forms, near spellings, geography, numeric tokens, extra tokens, and four explicit legal-form collision guards.

### Metrics

For equality of normalized keys as a *feature*:

- TP / FP / TN / FN;
- precision;
- recall;
- F0.5, because false collisions are intentionally expensive in this experiment;
- false-collision rate;
- Matthews correlation coefficient;
- error counts by perturbation category.

There is deliberately no assertion that Rigour or SearchLeads must win.

The curated fixture is an adversarial engineering corpus, not a market-representative sample and not independent evidence of entity-resolution precision. A production choice must also be checked downstream against the independent ER benchmark.

## CNPJ challengers

As of 2026-07-31, Receita Federal has generated the first alphanumeric CNPJ. Current systems therefore must not assume that CNPJ is numeric-only.

Official sources used by the experiment:

- Receita Federal announcement of the first alphanumeric CNPJ, `00.000.000/E08G-12`:
  https://www.gov.br/receitafederal/pt-br/assuntos/noticias/2026/julho/receita-federal-gera-o-primeiro-cnpj-em-formato-alfanumerico
- Receita Federal / Serpro technical DV documentation:
  https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/documentos-tecnicos/cnpj
- Published worked example: `12.ABC.345/01DE-35`.

The frozen CNPJ probe compares:

1. the official reference algorithm implemented directly from the Receita/Serpro specification;
2. current SearchLeads CNPJ canonicalization from the gap planner;
3. Rigour 1.4.0 `rigour.ids.CNPJ`, which delegates to `python-stdnum` validation.

The official implementation is the acceptance oracle for the six frozen valid/invalid cases. SearchLeads and Rigour are measured against it.

### Important semantic distinction

Current SearchLeads `_normalize_cnpj` checks compact shape (`14` alphanumeric characters) and canonicalizes formatting/case. It is not a checksum validator. Accepting a syntactically shaped identifier must not be described as validating the CNPJ.

Rigour exposes a validation-oriented API. Whether its pinned dependency version accepts the new alphanumeric format is an empirical question for this benchmark, not an assumption.

If neither challenger covers the official current format correctly, the winning production idea may be neither existing implementation: use the official algorithm as a dedicated SearchLeads identifier validator while keeping normalization and identity resolution separate.

## Adoption gate

No normalization implementation is replaced until:

- the complete SearchLeads regression suite executes;
- all normalization probes execute on Python 3.11 and 3.12;
- false collisions are reviewed, not only positive invariance;
- the chosen name normalization is tested as an ER feature on the independent linkage benchmark;
- the CNPJ behavior matches current Receita official examples, including alphanumeric identifiers;
- raw source values and Evidence remain unchanged and auditable.

## Current CI gate

GitHub-hosted jobs for this repository have repeatedly terminated before checkout/setup with no job steps. Until that infrastructure gate is resolved, the files in this PR are executable protocols and hypotheses, not PASS results.
