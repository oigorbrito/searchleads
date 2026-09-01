# SearchLeads First Real Source v1

## Work unit

`LEADS_FIRST_REAL_SOURCE_V1`

Exactly one real-source adapter is introduced: **BrasilAPI CNPJ v1**.

The implemented path is deliberately narrow:

```text
known CNPJ
→ one BrasilAPI point lookup
→ raw HTTP response Evidence
→ validate response identity
→ Company shell
→ direct source-field Provenance
→ CandidateFact records
→ SQLite persistence
```

This is not a discovery crawler and not a bulk company enumerator.

## Current source contract rechecked on 2026-08-24

The current BrasilAPI documentation describes CNPJ v1 as accepting a 14-character identifier composed of digits and letters A-Z, with or without formatting. The clean adapter therefore does **not** copy the older digits-only assumption.

Current BrasilAPI terms still ask consumers not to automate crawling/full scans or loop across the identifier space. This work unit performs only a point lookup for a CNPJ already known by the caller.

Current BrasilAPI issue history also shows practical anti-abuse behavior on CNPJ v1:

- issue #826 (2026-06-22): HTTP 403 can depend on a generic/default User-Agent; an explicit identifying User-Agent is a working mitigation reported by users;
- issue #835 (2026-07-29): HTTP 429 / `x-vercel-mitigated: deny` can occur and no stable public numeric rate-limit contract was established in that report.

Accordingly the adapter sends an explicit User-Agent, uses a bounded timeout, preserves HTTP response bodies as Evidence before raising non-200 errors, and does not invent retry/rate-limit policy in this work unit.

References checked:

- https://brasilapi.com.br/
- https://brasilapi.com.br/docs
- https://github.com/BrasilAPI/BrasilAPI/issues/826
- https://github.com/BrasilAPI/BrasilAPI/issues/835

## Evidence-before-interpretation contract

For any HTTP response that reaches the transport boundary, the textual body is stored as Evidence before JSON validation, CNPJ matching, legal-name validation, or field extraction.

This includes non-200 responses such as 403, 404, 429, and 500. A network failure with no HTTP response cannot produce source Evidence and raises `BrasilAPIAcquisitionError`.

Evidence identity is derived from **request URL + exact textual body**, while `Evidence.content_digest` is the SHA-256 of the body alone. Including the URL prevents generic identical anti-abuse bodies from different CNPJ lookups from colliding.

## Current CNPJ routing key

`normalize_cnpj_key()` performs only adapter-key cleanup:

- removes `.`, `/`, `-`, and whitespace;
- uppercases letters;
- requires exactly 14 characters in `0-9A-Z`.

This is not claimed as `COMPANY_NORMALIZATION_V1`. The returned source value remains the `CandidateFact.raw_value`, and `normalized_value` remains `None` in this unit.

## Source-derived predicates

Only a bounded set of company fields is emitted:

| SearchLeads field | BrasilAPI field |
| --- | --- |
| `business_registry_id` | `cnpj` |
| `legal_name` | `razao_social` |
| `trade_name` | `nome_fantasia` |
| `registration_status` | `descricao_situacao_cadastral` |
| `primary_cnae_code` | `cnae_fiscal` |
| `primary_cnae_description` | `cnae_fiscal_descricao` |
| `city` | `municipio` |
| `state` | `uf` |

Blank optional values are skipped. `cnpj` must match the requested routing key and `razao_social` must be non-blank before a Company is created.

Fields such as e-mail, telephone, QSA/socios, or other people-related values are intentionally ignored here. Contact and Person work units remain separate.

## Identity and repeat observations

The source adapter uses a deterministic external shell ID:

```text
company:brasilapi-cnpj:<14-char source key>
```

This is a source-scoped engineering key, not a general entity-resolution rule.

- same URL + same raw body: reuses the existing Evidence and facts;
- changed body: creates a new Evidence/fact snapshot and reuses the Company shell;
- same generic HTTP error body for different URLs: creates distinct Evidence records.

## Real-company calibration

The point-lookup example retained for the smoke path is:

```text
CNPJ = 33.683.111/0002-80
COMPANY = SERVICO FEDERAL DE PROCESSAMENTO DE DADOS (SERPRO)
LOCATION = BRASILIA / DF
```

Independent current public company-data pages checked in July/August 2026 continue to report this identifier and legal name, so the smoke target itself is not a fabricated company.

This independent verification does not substitute for a successful BrasilAPI HTTP response.

## Local execution and gate

Final deterministic test run for the clean WU3 stack:

```text
TESTS = 172/172 PASS
LINE_COVERAGE = 100%
MEASURED_STATEMENTS = 678
RESOURCE_WARNINGS_AS_ERRORS = PASS
```

A live HTTP smoke using the adapter's explicit User-Agent was attempted from the execution container on 2026-08-24 and failed before HTTP because DNS could not resolve `brasilapi.com.br`:

```text
CURL_RC = 6
HTTP_CODE = 000
ERROR = Could not resolve host: brasilapi.com.br
```

Therefore the strict gate is reported without relabeling an injected fixture as live acquisition:

```text
ONE_REAL_SOURCE_IMPLEMENTED = YES
REAL_SOURCE_CONTRACT_VERIFIED = YES
RAW_HTTP_EVIDENCE_BEFORE_INTERPRETATION = YES
COMPANY_CANDIDATE_CREATED_BY_EXECUTABLE_ADAPTER = YES
PERSISTENCE_CONNECTED = YES
ALPHANUMERIC_CNPJ_CONTRACT = PASS
EXPLICIT_USER_AGENT = PASS
HTTP_403_429_EVIDENCE_PATH = PASS
REAL_COMPANY_SMOKE_TARGET_VERIFIED = YES
LIVE_HTTP_REQUEST_IN_EXECUTION_CONTAINER = BLOCKED_BY_DNS
REAL_COMPANIES_INGESTED_BY_LIVE_CONTAINER_HTTP = 0
STRICT_REAL_COMPANIES_INGESTED_GT_0 = PENDING_EXTERNAL_NETWORK_SMOKE
```

## Explicitly deferred

- crawling/full scans;
- broad company discovery;
- retry/backoff/rate-limit policy;
- source redundancy;
- company normalization;
- company entity resolution;
- canonical fact selection/fusion;
- contacts and Person extraction;
- contact validation;
- ICP and qualification.

## Next work unit

Per the staged roadmap, the next technical unit after the external live-smoke gate is `COMPANY_NORMALIZATION_V1`.
