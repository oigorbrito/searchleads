# External Web Discovery Provider V1

## Work unit

`EXTERNAL_WEB_DISCOVERY_PROVIDER_V1`

This unit resolves #74 by porting the already-tested provider boundary from legacy PR #37 onto the clean SearchLeads stack. Only the previously implemented Apify Google Search provider is ported. Brave Search, SerpAPI, Google Places and Hunter remain unimplemented recommendations, not approved providers.

## Pipeline

```text
approved Dental query recipe
→ provider-neutral WebSearchQuery
→ bounded Apify Actor request
→ raw provider dataset item persisted as Evidence
→ WebSearchHit projection
→ clean Dental public-web observation/candidate recipe
→ CFO verification remains PENDING
```

External provider output never bypasses Evidence, Person/Company ER, contact validation, qualification, CFO/CRO verification or campaign compliance.

## Provider-neutral contract

`WebSearchProvider` returns one `WebSearchBatch` containing projected hits and the Evidence records they reference. A batch is invalid when a hit references Evidence outside that batch.

Queries require explicit query IDs, query text, country and language. The Apify V1 adapter requires one country/language combination per Actor batch and unique query IDs.

## Apify contract

```text
API_BASE = https://api.apify.com/v2
ACTOR = apify~google-search-scraper
PROVIDER_ID = apify-google-search-v1
SYNC_ENDPOINT = /actors/{actor}/run-sync-get-dataset-items?clean=true&format=json
AUTH = Authorization: Bearer <token>
DEFAULT_COUNTRY = BR
DEFAULT_INTERFACE_LANGUAGE = pt-BR
DEFAULT_MAX_PAGES_PER_QUERY = 1
DEFAULT_MAX_QUERIES = 20
DEFAULT_MAX_DATASET_ITEMS = 200
DEFAULT_TIMEOUT_SECONDS = 120
```

All bounds are explicit and validated.

## Credential boundary

The API token is accepted only by the provider/client runtime and is sent only through the HTTP `Authorization` header. It is never appended to the request URL, Source locator, Evidence locator, Evidence metadata, dry-run output or projected search hit.

No token is committed to the repository. Live execution requires `APIFY_API_TOKEN`; credential-free `--dry-run` only emits the deterministic Dental query plan.

## Evidence-first acquisition

Each raw Apify dataset item is wrapped with non-secret provider metadata and canonicalized as JSON text. That complete text is persisted as clean-stack `Evidence.raw_payload` before `organicResults` are projected.

Evidence IDs are content-addressed from the canonical raw provider item. Replaying the identical provider item reuses the same Evidence. A content-addressed collision with differing source, locator or raw payload raises an explicit payload error.

An item with no `organicResults` is valid empty Evidence. Invalid organic result shapes raise an explicit payload error after raw acquisition.

## Dental bridge

The bridge consumes `DENTAL_PUBLIC_WEB_DISCOVERY_V1` from #78. Provider hits become `PublicSearchObservation` values with deterministic IDs and the exact provider Evidence ID. The existing conservative Dental recipe then decides whether the observation is a candidate.

Provider data cannot set CFO status to verified and cannot infer learning intent. Candidate dedupe remains exact CRO or exact URL only; names remain non-authoritative.

## Validation

Focused injected-transport suite:

```text
TESTS = 18/18 PASS
CONTRACTS_COVERAGE = 100%
DENTAL_BRIDGE_COVERAGE = 100%
APIFY_ADAPTER_COVERAGE = 99% line/branch combined
TOTAL_NEW_LOGIC_COVERAGE = 99%
STATEMENTS = 184
BRANCHES = 76
DRY_RUN = PASS
COMPILEALL = PASS
```

The only remaining uncovered branch is an internal successful-path arc in the duplicate-query guard; all lines are covered. This is not relabeled as live Apify success.

## Gates

```text
PROVIDER_NEUTRAL_BOUNDARY = PASS
APIFY_IMPLEMENTED = YES
OTHER_PROVIDERS_IMPLEMENTED = NO
BOUNDED_QUERIES = PASS
BOUNDED_PAGES = PASS
BOUNDED_DATASET_ITEMS = PASS
RAW_PROVIDER_EVIDENCE_FIRST = PASS
TOKEN_IN_AUTH_HEADER_ONLY = PASS
TOKEN_IN_PERSISTED_LOCATOR = NO
EMPTY_ORGANIC_RESULTS_VALID = YES
CFO_VERIFICATION_BYPASS = NO
LEARNING_INTENT_INFERENCE = NO
GENERIC_CRAWLER = NO
DRY_RUN_WITHOUT_CREDENTIALS = PASS
LIVE_APIFY_WITH_REAL_TOKEN = NOT_CERTIFIED
```

## Basis

- legacy PR #37 / `EXTERNAL-API-PROVIDERS-V1-REPORT.md`
- clean `DENTAL_PUBLIC_WEB_DISCOVERY_V1` (#78 / PR #80)
- clean Evidence/SQLiteRepository model
- issue #74
