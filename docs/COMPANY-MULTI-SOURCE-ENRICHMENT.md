# MULTI_SOURCE_COMPANY_ENRICHMENT_V1

## Scope

This post-handoff clean-stack extension closes the technical blocker that the accepted pipeline still had only one company-data source.

The new adapter is intentionally narrow. It consumes the known SERPRO transparency address page for an already-identified Company/CNPJ. It does not crawl, discover arbitrary sources, rank sources, or infer truth from source authority.

Source 1 remains the existing WU3 BrasilAPI CNPJ point lookup.

Source 2 is the official SERPRO transparency address page:

`https://www.transparencia.serpro.gov.br/acesso-a-informacao/institucional/enderecos`

The official page was checked on 2026-08-25 and reports itself updated on 2026-01-19. Its current content exposes the SERPRO headquarters plus eleven regional CNPJ/location blocks, including Brasília CNPJ `33.683.111/0002-80`, its address, city/state, postal code, and activity-start date.

The deterministic test fixture is calibrated to those current published values. It is not represented as a byte-for-byte live capture of the current page.

## Evidence boundary

The adapter follows the existing evidence-first pattern:

1. require the Company to already exist;
2. constrain acquisition to the exact known official HTTPS page;
3. persist Source and complete raw HTML Evidence;
4. reject non-200 responses only after Evidence is persisted;
5. locate exactly one visible block containing the expected CNPJ;
6. reject absent or ambiguous repeated CNPJ blocks;
7. create per-field Provenance and CandidateFact records.

`script`, `style`, `noscript`, and `template` content is ignored for extraction but remains inside the preserved raw page Evidence.

## Extracted fields

The source may emit:

- `business_registry_id`
- `street_address`
- `city`
- `state`
- `postal_code`
- `activity_start_date`

For `business_registry_id`, the displayed formatted CNPJ remains in `raw_value`. Only punctuation compaction is placed in `normalized_value`, matching the existing 14-character WU3 routing-key contract. This does not introduce a general registry normalization rule.

Other values remain raw source observations. In particular, the adapter does not map full state names to abbreviations and does not remove accents/case from city values.

## Multi-source behavior measured on Brasília

The deterministic integration uses the same real company identity as the accepted stack:

- CNPJ: `33.683.111/0002-80`
- clean Company: `company:brasilapi-cnpj:33683111000280`

The two sources are distinct Source/Evidence records. Company ER over their registry observations returns `AUTO_MATCH` from exact CNPJ equality after routing-key formatting normalization.

There are three overlapping company predicates:

- `business_registry_id`
- `city`
- `state`

Measured fusion behavior:

- `business_registry_id`: canonical agreement = **1**
- `city`: explicit conflict = **1** (`BRASILIA` vs `Brasília`)
- `state`: explicit conflict = **1** (`DF` vs `Distrito Federal`)

The official source adds three fields not currently emitted by the WU3 BrasilAPI adapter:

- `street_address`
- `postal_code`
- `activity_start_date`

No source is declared more authoritative. The two representation conflicts are retained so a future normalization/truth policy can be measured rather than assumed.

## Source-independence boundary

This work unit uses two distinct acquisition sources/publishers: BrasilAPI and the official SERPRO transparency site. That is sufficient to exercise multi-source provenance and conflict behavior.

It is **not** evidence that the sources are statistically independent. BrasilAPI may ultimately derive some registry data from public official registries, while SERPRO publishes its own institutional data. This unit therefore does not assign probabilistic independence or source reliability weights.

## Current calibration

The deterministic current-page fixture contains the twelve CNPJ blocks verified on the official page:

- headquarters: 1
- regional/location blocks: 11
- extraction exact: **12/12**

Curated adversarial extraction benchmark:

- valid cases: **5/5 exact**
- expected rejection cases: **4/4 rejected**

Rejected conditions include:

- requested CNPJ absent;
- requested CNPJ present only inside ignored script content;
- same requested CNPJ repeated in multiple visible blocks;
- same requested CNPJ repeated twice in one block.

## Verification

Focused WU15 suite:

- **25/25 PASS**
- **100% line coverage across 273 statements** including package init
- **100% branch coverage across 82 branches**

Reconstructed WU14 acceptance + WU15 integration:

- **43/43 PASS**

Benchmark script:

`PYTHONPATH=src python scripts/evaluate_company_enrichment.py`

Measured output:

```text
current_calibration=12/12
curated_valid_exact=5/5
curated_reject_exact=4/4
source_count=2
overlap_fields=3 fields=business_registry_id,city,state
canonical_agreements=1
explicit_conflicts=2
enrichment_only_fields=3 fields=activity_start_date,postal_code,street_address
company_er=AUTO_MATCH
```

## Gates

- `SECOND_COMPANY_SOURCE = YES`
- `SAME_COMPANY_MULTI_SOURCE = YES`
- `RAW_EVIDENCE_PER_SOURCE = PASS`
- `MULTI_SOURCE_PROVENANCE = PASS`
- `COMPANY_ER_ACROSS_SOURCES = AUTO_MATCH`
- `OVERLAP_FIELDS = 3`
- `CANONICAL_AGREEMENTS = 1`
- `EXPLICIT_CONFLICTS = 2`
- `NEW_ENRICHMENT_FIELDS = 3`
- `SOURCE_AUTHORITY_WEIGHTS = NO`
- `GENERIC_CRAWLER = NO`
- `LIVE_SOURCE_HTTP_IN_EXECUTION_CONTAINER = NOT_CERTIFIED`
- `ICP_DEFINED = NO`
- `COMMERCIAL_QUALIFICATION = BLOCKED`

## Next integration correction

WU13 was intentionally written before this source existed and therefore still blocks `street_address`, `postal_code`, and `activity_start_date`. The next bounded change is to reconcile the gap planner so these three requirements can select this newly implemented source when an explicit CNPJ is available.
