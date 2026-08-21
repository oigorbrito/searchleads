# WORK UNIT 03 REPORT — LEADS_FIRST_REAL_SOURCE_V1

## Scope

Exactly one source was integrated: **BrasilAPI CNPJ API**.

Pipeline implemented:

```text
known CNPJ
→ HTTP JSON acquisition
→ validate source identity fields
→ persist Source
→ persist complete raw Evidence payload
→ create/reuse Company shell
→ derive CandidateFact records
→ persist candidate facts
```

No broad search, second source, normalization, entity resolution, contact discovery, person discovery, canonicalization, or qualification was added.

## Source selection

BrasilAPI was selected because its current public documentation exposes a keyless CNPJ endpoint and the project terms allow point queries while explicitly discouraging crawling/full scans. The CNPJ endpoint is documented as a Minha Receita-backed lookup. Recent BrasilAPI issue/discussion history also records stale/divergent CNPJ results, which fits the existing candidate-fact/provenance model: source values are observations, not automatically canonical facts.

The single-CNPJ endpoint `GET /api/cnpj/v1/{cnpj}` is used in V1. BrasilAPI terms explicitly discourage crawling/full scans, so this adapter remains a single-company lookup and is not a bulk discovery mechanism.

## Implemented files

- `searchleads/brasilapi.py`
- `tests/test_brasilapi.py`
- `README.md`
- `ARCHITECTURE-PRINCIPLES.md`
- `searchleads/__init__.py`
- `pyproject.toml`
- `WORK-UNIT-03-REPORT.md`

## Source-derived predicates

Direct extraction only; no normalization is claimed:

- `business_registry_id` ← `cnpj`
- `legal_name` ← `razao_social`
- `trade_name` ← `nome_fantasia`
- `registration_status` ← `descricao_situacao_cadastral`
- `primary_cnae_code` ← `cnae_fiscal`
- `primary_cnae_description` ← `cnae_fiscal_descricao`
- `city` ← `municipio`
- `state` ← `uf`

## Identity behavior

Company identity for this source adapter uses the source-provided CNPJ as a deterministic external identifier:

```text
company:cnpj:<14 digits>
```

This is a source adapter identity key, not a general claim that every future company/entity-resolution problem can be solved by CNPJ equality. A repeated observation reuses the existing Company shell; changed source payloads create new Evidence and CandidateFact snapshots.

## Validation

```text
TESTS_DISCOVERED = 32
TESTS_EXECUTED = 32
TESTS_PASSED = 32
```

Validated behaviors include:

- formatted CNPJ input is reduced to its 14 source digits;
- returned CNPJ must match the requested CNPJ before persistence;
- a non-blank legal name is required to create a company candidate;
- the full transport response mapping is preserved as raw evidence;
- source-derived facts point to the raw evidence through provenance;
- no contacts or people are extracted in this work unit;
- same payload is idempotent;
- changed payload creates a new evidence snapshot while reusing the same Company;
- evidence/company survive database close/reopen.

## Real-source verification

Current BrasilAPI documentation (checked 2026-08-21) documents the CNPJ endpoint and its Receita-derived schema. Current external evidence also shows the endpoint in active use in July–August 2026, including successful requests when a non-generic User-Agent is supplied. A separate current indexed company page reports CNPJ `33683111000280` as `SERVICO FEDERAL DE PROCESSAMENTO DE DADOS (SERPRO)`.

The execution container used for the local test suite has no outbound DNS, so the automated unit suite uses an injected transport and does not claim a live network request occurred inside the container. The production transport is implemented with Python stdlib `urllib`, sends an explicit User-Agent, and targets the documented endpoint.

This distinction is intentional:

```text
REAL_SOURCE_CONTRACT_VERIFIED = YES
REAL_COMPANY_EXAMPLE_VERIFIED = YES
LIVE_HTTP_REQUEST_IN_TEST_CONTAINER = NO
```

## Gate

```text
ONE_REAL_SOURCE_IMPLEMENTED = YES
RAW_EVIDENCE_PRESERVED = YES
COMPANY_CANDIDATE_CREATED = YES
PERSISTENCE_CONNECTED = YES
REAL_COMPANIES_INGESTIBLE = YES
REAL_COMPANIES_INGESTED_BY_LIVE_CONTAINER_HTTP = 0
LIVE_HTTP_BLOCKER = EXECUTION_ENVIRONMENT_NO_OUTBOUND_DNS
TESTS = PASS
```

Because the handoff gate literally states `REAL_COMPANIES_INGESTED > 0`, the strictest interpretation of that gate is **not fully satisfied in this execution environment** until one live HTTP request succeeds outside the network-restricted test container. The code path is implemented and source contract is verified; the report does not relabel a documented fixture as a live ingestion.

## Decision classification

### EVIDENCE_BACKED

- raw source evidence precedes derived facts;
- source facts retain provenance;
- source-derived values remain candidate facts rather than verified/canonical facts.

### LOCALLY_VERIFIED

- BrasilAPI currently documents `GET /api/cnpj/v1/{cnpj}`;
- BrasilAPI identifies the CNPJ lookup as Minha Receita-backed;
- current BrasilAPI terms discourage crawling/full scans;
- current BrasilAPI issue/discussion history shows that CNPJ data can lag or diverge from Receita, so values remain candidate facts rather than canonical truth.

### ENGINEERING_CHOICE

- BrasilAPI as the first source;
- direct known-CNPJ lookup for V1;
- stdlib `urllib` transport with explicit User-Agent;
- deterministic source/evidence/candidate IDs;
- the small initial field mapping above.

### HYPOTHESIS

- B2B remains provisional.

### UNKNOWN

- ICP;
- normalization rules;
- entity-resolution weights/thresholds;
- contact-validation method;
- broad discovery coverage from this source.

## Next work unit

Per the supplied roadmap: `COMPANY_NORMALIZATION_V1`.
