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

No broad search, second source, normalization, entity resolution, contact discovery, person discovery, canonicalization, or qualification was added in this work unit.

## Source selection

BrasilAPI was selected because its public documentation exposes a keyless CNPJ endpoint and the project terms allow point queries while discouraging crawling/full scans. The single-CNPJ endpoint `GET /api/cnpj/v1/{cnpj}` is used in V1.

## Source-derived predicates

Direct extraction only; no normalization is claimed here:

- `business_registry_id` ← `cnpj`
- `legal_name` ← `razao_social`
- `trade_name` ← `nome_fantasia`
- `registration_status` ← `descricao_situacao_cadastral`
- `primary_cnae_code` ← `cnae_fiscal`
- `primary_cnae_description` ← `cnae_fiscal_descricao`
- `city` ← `municipio`
- `state` ← `uf`
- later extension: source-supplied registry size fields when present.

## Identity behavior

Company identity for this source adapter uses the source-provided CNPJ as a deterministic external identifier:

```text
company:cnpj:<14 digits>
```

This is a source-adapter identity key, not a general statement that all entity-resolution problems are solved by CNPJ equality.

## Historical unit validation

Original WU3 suite:

```text
TESTS_DISCOVERED = 32
TESTS_EXECUTED = 32
TESTS_PASSED = 32
```

Validated behavior includes raw evidence preservation, source identity validation, idempotence, changed-payload snapshots, persistence/reopen behavior, and explicit separation from contacts/people.

## Live HTTP closure

The earlier local execution environment could not resolve outbound DNS, so this report originally left the literal live-ingestion gate pending.

That external-runtime blocker is now closed by GitHub Actions full regression run `32544027242` on 2026-08-22.

Command:

```bash
PYTHONPATH=. python scripts/run_live_brasilapi_smoke.py
```

Observed result:

```text
WU3_LIVE_HTTP=PASS
COMPANY_ID=company:cnpj:33683111000280
EVIDENCE_ID=evidence:brasilapi:33683111000280:0fd37b41051557340f5d
CANDIDATE_FACTS=10
```

The smoke performed a literal live HTTP acquisition of the SERPRO CNPJ `33683111000280` through the implemented BrasilAPI adapter and persisted the resulting evidence/company facts.

## Current gate

```text
ONE_REAL_SOURCE_IMPLEMENTED = YES
RAW_EVIDENCE_PRESERVED = YES
COMPANY_CANDIDATE_CREATED = YES
PERSISTENCE_CONNECTED = YES
REAL_COMPANIES_INGESTIBLE = YES
REAL_COMPANIES_INGESTED_BY_LIVE_HTTP > 0 = YES
WU3_LIVE_HTTP = PASS
WU3_STRICT_GATE = PASS
```

## Current full-regression evidence

The current stacked PR branch subsequently executed the entire repository suite in GitHub Actions:

```text
FULL_CURRENT_TEST_COUNT = 234/234 PASS
DETERMINISTIC_E2E = PASS
DENTAL_BATCH_50_SMOKE = PASS
WU3_LIVE_HTTP = PASS
```

See `FULL-REGRESSION-REPORT-2026-08-22.md` for the exact execution record.

## Decision classification

### EVIDENCE_BACKED

- raw source evidence precedes derived facts;
- source facts retain provenance;
- source-derived values remain candidate facts until later fusion/validation.

### ENGINEERING_CHOICE

- BrasilAPI as the first source;
- direct known-CNPJ lookup for V1;
- stdlib `urllib` transport with explicit User-Agent;
- deterministic source/evidence/candidate IDs.

### HISTORICAL NOTE

The earlier `EXECUTION_ENVIRONMENT_NO_OUTBOUND_DNS` blocker applied only to the local/reconstructed environment. It is superseded for the WU3 strict gate by the successful GitHub Actions live HTTP smoke above.
