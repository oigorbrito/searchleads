# External API Providers V1

## Goal

SearchLeads keeps the existing evidence-preserving pipeline while allowing selected external APIs to accelerate discovery, enrichment and validation.

```text
ICP / explicit requirements
→ deterministic acquisition request
→ external API provider adapter
→ RAW PROVIDER RESPONSE AS EVIDENCE
→ structured observation
→ normalization / entity resolution
→ enrichment / validation
→ qualification
→ review / export
```

External APIs do **not** bypass provenance, entity resolution, professional verification, contact validation or qualification.

## Non-negotiable provider rule

```text
THIRD_PARTY_API_RESULT != VERIFIED_FACT
THIRD_PARTY_CRO_CLAIM != CFO_VERIFIED_CREDENTIAL
THIRD_PARTY_EMAIL != VALIDATED_CONTACT
SEARCH_RESULT != PERSON_IDENTITY
```

A provider response is evidence from that provider. It can support discovery and later corroboration, but authority is evaluated separately.

## First implemented provider — Apify

V1 implements Apify through the REST Actor API using the maintained Google Search Results Scraper by default:

```text
Actor = apify/google-search-scraper
API = https://api.apify.com/v2
Auth = APIFY_API_TOKEN environment variable
Mode = run-sync-get-dataset-items
```

The token is sent in the `Authorization: Bearer ...` header and is never embedded in persisted URLs or committed to the repository.

The adapter:

1. receives the existing deterministic dental query plan;
2. sends a bounded group of queries to the configured Actor;
3. persists every raw dataset page as immutable Evidence;
4. projects only organic results into the generic `WebSearchHit` contract;
5. feeds those hits into the existing `PublicSearchObservation` / dental candidate pipeline;
6. leaves CFO verification `PENDING`.

No learning intent is inferred from Apify output.

## Provider-neutral contract

`searchleads/external_api.py` defines a minimal `WebSearchProvider` boundary.

This means the dental business logic does not need to know whether search results came from Apify, Brave Search, SerpAPI or another future provider.

```text
WebSearchQuery
→ WebSearchProvider
→ WebSearchBatch
   ├── raw persisted Evidence
   └── WebSearchHit[]
→ existing dental discovery
```

## Shortlist researched for this use case

### 1. Apify — IMPLEMENTED V1

Best initial role:

- flexible web discovery;
- Google SERP extraction through maintained Actor;
- optional Google Maps / website-contact Actors later;
- useful for sites that do not expose direct APIs.

Use as discovery/enrichment evidence, not authoritative credential verification.

Official documentation:

- https://docs.apify.com/api
- https://apify.com/apify/google-search-scraper/api
- https://apify.com/compass/crawler-google-places/api

### 2. Brave Search API — RECOMMENDED FALLBACK WEB SEARCH

Best role:

- direct structured web-search API;
- independent search index;
- simple API contract without browser automation;
- provider redundancy if Apify/Google SERP becomes unavailable or expensive.

Potential SearchLeads role: second `WebSearchProvider` implementation.

Documentation:

- https://api-dashboard.search.brave.com/api-reference/web/search/get

### 3. SerpAPI — OPTIONAL GOOGLE-SERP ALTERNATIVE

Best role:

- structured Google search results;
- geographic search controls;
- useful as an alternate provider when Google-like SERP fidelity matters.

Potential SearchLeads role: alternative `WebSearchProvider`, not a new business layer.

Documentation:

- https://serpapi.com/search-api

### 4. Google Places API — RECOMMENDED FOR CLINIC/LOCATION CONTEXT

Best role:

- clinic/business discovery by text or proximity;
- address, place identity, phone and website context;
- location-based expansion by region/state/city.

This API identifies places/businesses, not dentist professional credentials. A clinic returned by Places remains `Company/context`, not automatically a `Person` lead.

Documentation:

- https://developers.google.com/maps/documentation/places/web-service/text-search
- https://developers.google.com/maps/documentation/places/web-service/place-details

### 5. Hunter API — RECOMMENDED LATER FOR EMAIL FINDING/DELIVERABILITY

Best role:

- domain-based email discovery;
- email finder;
- email verifier / deliverability signal;
- source URLs when Hunter found an address publicly.

Hunter's deliverability result should become a contact-validation signal with its own provenance. It must not be confused with CFO verification or identity resolution.

Documentation:

- https://hunter.io/api-documentation/v2
- https://hunter.io/api/email-verifier

## MVP provider order

Recommended implementation order:

```text
1. Apify Google Search                 IMPLEMENTED
2. Brave Search                        fallback web discovery
3. Google Places                       clinic/location enrichment
4. Hunter                              contact discovery/validation
5. SerpAPI                             optional Google-SERP redundancy
```

Do not integrate all providers at once. Each new provider must demonstrate a concrete gap it closes and preserve raw evidence.

## Dental MVP with external APIs

```text
Dental ICP
→ deterministic region/title queries
→ Apify or another WebSearchProvider
→ raw provider Evidence
→ public dentist candidate
→ exact CRO / URL conservative dedupe
→ official CFO/CRO verification
→ FIT / INTENT
→ contact discovery / validation
→ PREPARATION_READY
→ campaign compliance
→ SEND_READY
```

The official CFO/CRO verification boundary is unchanged.

## Runtime configuration

No API secrets are stored in Git.

Current environment variable:

```text
APIFY_API_TOKEN
```

Dry query-plan smoke without credentials:

```bash
PYTHONPATH=. python scripts/run_apify_dental_discovery.py --dry-run --max-queries 4
```

Live bounded discovery:

```bash
APIFY_API_TOKEN=... PYTHONPATH=. python scripts/run_apify_dental_discovery.py \
  --max-queries 4 \
  --db searchleads-apify.db \
  --output apify-dental-candidates.json
```

Regional example:

```bash
APIFY_API_TOKEN=... PYTHONPATH=. python scripts/run_apify_dental_discovery.py \
  --region SOUTHEAST \
  --max-queries 8
```

## Scope deliberately deferred

V1 does not add:

- automatic mass scraping;
- automatic outreach;
- API-key storage;
- a generic workflow engine;
- a claim that Apify/Google/Brave/Hunter is authoritative for professional licensure;
- automatic intent inference from third-party data;
- automatic person merge from names.
