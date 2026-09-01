# Person and Role Discovery v1

## Work unit

`PERSON_AND_ROLE_DISCOVERY_V1`

This unit discovers **Person observations** and explicit professional roles from one supplied company people/leadership page. It requires an already-known `Company` and preserves page Evidence before creating any Person observation.

## Pipeline

```text
known persisted Company
→ explicit company people/leadership page
→ raw page Evidence
→ role text + plausible adjacent human name
→ source-observation Person
→ person_name CandidateFact + Provenance
→ professional_role_title CandidateFact + Provenance
→ optional local professional contacts (DISCOVERED)
→ SQLite persistence
```

## Identity boundary

WU8 does **not** perform Person Entity Resolution.

The Person observation key is deterministic from:

```text
company_id
+ evidence_id
+ observation ordinal
+ normalized name
+ normalized role title
```

Consequences:

- repeated processing of the same snapshot is idempotent;
- two same-name observations with different roles remain distinct;
- changed page snapshots create distinct Person observations;
- name equality never merges people;
- cross-source/cross-snapshot identity remains deferred to a separate Person ER unit.

This corrects the unsafe legacy pattern `company + normalized name`, which could collapse homonyms before Person ER had a chance to evaluate them.

## Company relationship evidence

Every Person created by this unit contains:

```text
company_id = known Company
relationship_evidence_ids = people-page Evidence
```

The company association is therefore explicit and reprocessable. WU8 does not infer employer from an e-mail domain, social profile, common name, or fuzzy similarity.

## Name and role representation

The existing clean domain is reused rather than adding a parallel `ProfessionalRole` table:

- `person_name` → `CandidateFact`
- `professional_role_title` → `CandidateFact`

Each fact is `EVIDENCE_BACKED`, references the page Evidence, and has its own `Provenance`. Raw title/name text is preserved as observed.

## Optional person-associated contacts

Within a bounded local block after the identified Person, WU8 may associate:

- professional e-mail;
- professional phone;
- direct LinkedIn personal profile `/in/<slug>`.

All such `ContactPoint` records remain `DISCOVERED`.

Not promoted to a person profile/contact:

- LinkedIn company profiles;
- LinkedIn subroutes such as posts;
- generic/shared “Currículo” links;
- arbitrary directory links;
- contacts that occur after the next role block;
- contacts outside the bounded local event window.

No deliverability, phone reachability, social-account control, or current employment validity is claimed.

## Curated role/name extraction benchmark

A deterministic 15-scenario adversarial fixture covers:

- multiple valid executives;
- uppercase names;
- the `Diretoria Executiva` heading distractor;
- name without role;
- role without plausible name;
- corporate/contact text after a role;
- hidden template/script content;
- same-name/different-role observations;
- links between role and name;
- a new role appearing before a candidate name;
- bounded name-search window;
- contact text before a later valid name;
- `Head` and `Sócia` role forms;
- punctuation-only fake name components.

Measured local contract:

```text
SCENARIOS = 15
EXPECTED_PERSON_ROLE_PAIRS = 12
TRUE_POSITIVE = 12
FALSE_POSITIVE = 0
FALSE_NEGATIVE = 0
PRECISION = 100.0%
RECALL = 100.0%
F1 = 100.0%
```

These are curated deterministic regression metrics, not production accuracy estimates across arbitrary sites.

## Current public SERPRO calibration — checked 2026-08-25

The official SERPRO “Quem é quem” page reports `Atualizado em 04 de agosto de 2026` and currently lists seven members of the Diretoria Executiva with title, name, phone, and professional e-mail:

1. Wilton Itaiguara Gonçalves Mota — Diretor-Presidente
2. Ermes Ferreira Costa Neto — Diretor de Negócios Governamentais
3. Wallyson Lemos dos Reis Oliveira — Diretor de Infraestrutura
4. Osmar Quirino da Silva — Diretor de Administração e Finanças
5. Alexandre Brandão Henriques Maimoni — Diretor de Pessoas e Assuntos Jurídicos
6. Ariadne de Santa Teresa Lopes Fonseca — Diretora de Negócios Econômico-Fazendários
7. André Picoli Agatte — Diretor de Novos Negócios e Inteligência de TI

Reference checked:

- `https://www.transparencia.serpro.gov.br/acesso-a-informacao/institucional/quem-e-quem`

The tests use minimal HTML calibrated to the currently published role/name/e-mail/phone values. They are not represented as a byte-for-byte live page snapshot.

## Verification

```text
WU8_FOCUSED_TESTS = 47/47 PASS
WU8_MODULE_LINE_COVERAGE = 100%
WU8_MEASURED_STATEMENTS = 259
WU6_PLUS_WU7_PLUS_WU8_RECONSTRUCTED = 133/133 PASS
PERSON_ROLE_BENCHMARK = PASS
PYTHON_MODULE_COMPILE = PASS
```

The base PR #48 remains separately validated according to its published verification. Prior whole-stack counts are not relabeled as newly executed after runtime reconstruction.

## Gate

```text
KNOWN_COMPANY_REQUIRED = YES
RAW_PEOPLE_PAGE_EVIDENCE = PASS
PERSON_COMPANY_RELATIONSHIP_EVIDENCE = PASS
PERSON_NAME_FACT = PASS
ROLE_TITLE_FACT = PASS
NAME_MATCH_AS_PERSON_IDENTITY = NO
OBSERVATION_SCOPED_PERSON_ID = YES
SAME_NAME_DIFFERENT_ROLE_DISTINCT = PASS
CHANGED_SNAPSHOT_DISTINCT_OBSERVATION = PASS
LOCAL_PERSON_CONTACT_ASSOCIATION = PASS
PERSON_CONTACT_STATUS = DISCOVERED
SHARED_PROFILE_PROMOTION = NO
PERSON_ENTITY_RESOLUTION = DEFERRED
CURATED_PRECISION = 100.0%
CURATED_RECALL = 100.0%
FOCUSED_TESTS = PASS
LINE_COVERAGE_NEW_MODULE = 100%
ICP_DEFINED = NO
B2B_ASSUMPTION = PROVISIONAL
```

## Next work unit

Per the supplied roadmap: `CONTACT_VALIDATION_V1`.
