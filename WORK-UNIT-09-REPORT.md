# WORK UNIT 09 REPORT — PERSON_DISCOVERY_AND_COMPANY_LINK_V1

## Scope

Discovers named professionals and explicit titles from one known official company page, creates separate `Person` shells, and persists evidence-backed `ProfessionalRole` links to the already-known `Company`.

## Pipeline

```text
persisted Company
→ official people/leadership page
→ raw HTML Evidence
→ role heading + human-name observation
→ Person
→ ProfessionalRole(Person ↔ Company, title, provenance)
```

No employer is inferred from a name, email domain, social profile, or fuzzy similarity. The caller supplies the company context, and the page must explicitly publish a role/title adjacent to a plausible human name.

## Real-company gate

The official Serpro `Quem é quem` page was updated on 2026-08-04 and currently lists seven members of the Diretoria Executiva. The V1 smoke fixture exercises these seven official name/title pairs, including:

- Wilton Itaiguara Gonçalves Mota — Diretor-Presidente
- Ermes Ferreira Costa Neto — Diretor de Negócios Governamentais
- Wallyson Lemos dos Reis Oliveira — Diretor de Infraestrutura
- Osmar Quirino da Silva — Diretor de Administração e Finanças
- Alexandre Brandão Henriques Maimoni — Diretor de Pessoas e Assuntos Jurídicos
- Ariadne de Santa Teresa Lopes Fonseca — Diretora de Negócios Econômico-Fazendários
- André Picoli Agatte — Diretor de Novos Negócios e Inteligência de TI

```text
REAL_PEOPLE_DISCOVERED = 7
REAL_PERSON_COMPANY_ROLE_LINKS = 7
ROLE_PROVENANCE = PASS
COMPANY_AND_PERSON_DISTINCT = PASS
```

## Role persistence

`ProfessionalRole` uses an additive `professional_roles` table initialized by the role-persistence extension. This avoids changing the existing base persistence schema version merely to add a later bounded capability. Role persistence requires:

- existing `Person`;
- existing `Company`;
- existing evidence referenced by provenance.

## Validation

```text
TESTS_DISCOVERED = 102
TESTS_EXECUTED = 102
TESTS_PASSED = 102
```

## Gate

```text
REAL_PEOPLE_DISCOVERED > 0 = PASS (7)
REAL_PERSON_COMPANY_LINKS > 0 = PASS (7)
PERSON_COMPANY_LINK_REQUIRES_EVIDENCE = PASS
PERSON_NOT_COMPANY = PASS
ROLE_ROUNDTRIP = PASS
TESTS = PASS
```

## Decision classification

### LOCALLY_VERIFIED

- current official Serpro leadership page publishes the seven smoke-test executives and roles;
- role persistence/provenance passes the local suite.

### ENGINEERING_CHOICE

- exact source-scoped normalized name + company as the V1 person shell key;
- title/name adjacency extraction from an explicit official leadership page;
- additive role-persistence extension.

### UNKNOWN

- cross-company/cross-source person entity resolution;
- employment validity outside the page snapshot;
- title normalization/taxonomy;
- production extraction precision/recall across arbitrary organization pages.

## Next work unit

Per roadmap: `LEAD_QUALIFICATION_V1`.
