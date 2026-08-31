# Chassis Bake-Off — Normalization V1

## Decision rule

SearchLeads normalization is a baseline, not a protected design. Rigour 2.3.1 is a challenger, not an assumed winner.

Normalization is evaluated as feature engineering. A normalized string is never entity identity and cannot, by itself, authorize a merge, canonical fact, qualified Lead, or contact validation state.

## Evidence classes

- `OFFICIAL_SPEC`: Receita Federal / Serpro current CNPJ alphanumeric specification and published examples.
- `ENGINEERING_EVIDENCE`: Rigour 2.3.1 public normalization APIs, organization-type reference database, tests and implementation; python-stdnum 2.2 current CNPJ implementation.
- `LOCAL_EXPERIMENT`: frozen SearchLeads adversarial name corpus, downstream ER ablation, and CNPJ challenger probes in this PR.
- `HYPOTHESIS`: any proposed production replacement before the GitHub runner actually executes the benchmark.

No scientific-performance claim is made from the curated fixture alone.

## Current SearchLeads architectural duplication

The current company-name field normalizer and current company ER do not share one normalization implementation:

- `searchleads.normalization._normalize_company_name` performs NFKC + whitespace normalization and preserves case/accents;
- `searchleads.entity_resolution.company._fold` independently performs NFKC + whitespace normalization, casefold, NFKD decomposition, and combining-mark removal.

Therefore replacing only the field normalizer can produce a cleaner stored projection without changing company ER at all. The bake-off treats this duplication as an engineering problem to measure, not as a reason to preserve either implementation.

A production change should prefer one explicit, testable name-feature contract if the benchmark shows that doing so preserves or improves ER behavior.

## Company-name challengers

The key-level benchmark compares four deterministic strategies over the same 44-pair frozen corpus:

1. `searchleads_nfkc_whitespace_v1`
   - current SearchLeads company-name projection;
   - Unicode NFKC + whitespace collapse;
   - preserves case and accents.
2. `rigour_normalize_name_2_3_1`
   - Rigour public `normalize_name` convenience key;
   - Unicode casefold + name tokenization.
3. `rigour_nfkd_casefold_name_2_3_1`
   - explicit `NFKD | CASEFOLD | NAME` pipeline;
   - tests whether compatibility decomposition and casefold improve representation invariance.
4. `rigour_nfkd_casefold_name_strip_org_type_2_3_1`
   - same folded key plus Rigour organization-type removal;
   - tests the recall/collision trade-off of dropping legal-form tokens.

The corpus has 20 representation-equivalent pairs and 24 distinct controls. It includes case, accent, punctuation, whitespace, Unicode compatibility/composition, invisible format characters, legal forms, near spellings, geography, numeric tokens, extra tokens, and four explicit legal-form collision guards.

### Key-level metrics

For equality of normalized keys as a *feature*:

- TP / FP / TN / FN;
- precision;
- recall;
- F0.5, because false collisions are intentionally expensive in this experiment;
- false-collision rate;
- Matthews correlation coefficient;
- error counts by perturbation category.

There is deliberately no assertion that Rigour or SearchLeads must win.

The curated fixture is an adversarial engineering corpus, not a market-representative sample and not independent evidence of entity-resolution precision.

## Downstream ER ablation

`test_chassis_bakeoff_normalization_er_impact.py` applies the name strategies inside the existing company ER benchmark while holding the other components fixed:

- registry conflict/exact rules unchanged;
- domain feature unchanged;
- phone feature unchanged;
- address feature unchanged;
- location feature unchanged;
- CNAE feature unchanged;
- weighted feature weights unchanged.

Only `name_similarity` changes.

The experiment reports both:

- the existing fixed `0.78` weighted threshold, to show the direct effect of changing only the name representation;
- a threshold selected from the 18-pair calibration partition and evaluated on the 36-pair holdout, to avoid rejecting a challenger merely because its score scale shifted.

Registry conflict remains a hard negative and cannot be overridden by aggressive name normalization.

This corpus predates the experiment, so independence of the SearchLeads baseline is not certified. The result is regression/comparative evidence, not a final unbiased market-quality estimate.

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
3. Rigour 2.3.1 `rigour.ids.CNPJ`, with the experiment pinning `python-stdnum==2.2`.

The official implementation is the acceptance oracle for the six frozen valid/invalid cases. SearchLeads and Rigour are measured against it.

### Dependency verification

Nomenklatura 4.14.0 requires `rigour >= 2.2.3, < 3.0.0`, so Rigour 2.3.1 is within its supported dependency range.

python-stdnum 2.2 explicitly added support for the new Brazilian CNPJ format. Its `stdnum.br.cnpj` implementation:

- accepts 14 alphanumeric characters;
- uppercases and compacts valid separators;
- maps each of the first 12 characters with `ord(character) - 48`;
- applies the official modulo-11 weight sequences;
- requires the last two characters to match the computed numeric check digits;
- includes `12.ABC.345/01DE-35` as a documented valid example.

Thus support for alphanumeric CNPJ is no longer a hypothesis for the pinned external dependency. The remaining empirical question is whether the complete Rigour wrapper, SearchLeads handling, and official oracle agree across the frozen cases and future adversarial cases.

### Important semantic distinction

Current SearchLeads `_normalize_cnpj` checks compact shape (`14` alphanumeric characters) and canonicalizes formatting/case. It is not a checksum validator. Accepting a syntactically shaped identifier must not be described as validating the CNPJ.

Rigour exposes a validation-oriented API via python-stdnum. Even if it wins the validation benchmark, canonicalization and validation should remain distinguishable operations: a source value may be preserved and normalized while failing validation, and a validation result must not erase raw Evidence.

If the external validator and official oracle disagree on any current official case, the official specification wins for the Brazilian identifier contract; the external library remains replaceable.

## Adoption gate

No normalization implementation is replaced until:

- the complete SearchLeads regression suite executes;
- all normalization probes execute on Python 3.11 and 3.12;
- false collisions are reviewed, not only positive invariance;
- the chosen name representation does not create a prohibited false-merge regression in downstream ER;
- the chosen approach resolves or explicitly justifies the duplicate normalization logic currently split between field normalization and ER;
- the CNPJ behavior matches current Receita official examples, including alphanumeric identifiers;
- raw source values and Evidence remain unchanged and auditable.

## Current CI gate

GitHub-hosted jobs for this repository have repeatedly terminated before checkout/setup with no job steps. Until that infrastructure gate is resolved, the files in this PR are executable protocols and hypotheses, not PASS results.
