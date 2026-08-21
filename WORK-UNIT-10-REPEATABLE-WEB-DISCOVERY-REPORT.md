# Work Unit 10 Report — REPEATABLE_WEB_DISCOVERY_V1

## Scope

Implements the handoff principle `KNOWN SOURCE → DISCOVER EXTRACTION → REUSE` for one known source only: the repeated office blocks on the official Serpro location directory.

No generic crawler, agent framework, or LLM-per-page extraction loop is introduced.

## Recipe

`serpro_office_directory_v1`

Input: one preserved HTML snapshot of the known office directory.

Output: deterministic CNPJ seeds with city/state and discovery-evidence linkage.

The recipe identifies repeated CNPJ office blocks and delegates block interpretation to the bounded official-location extractor already exercised in `COMPANY_ENRICHMENT_V1`.

## Reuse test

A deterministic fixture reflecting four currently published Serpro regional entries is parsed without page-specific manual seed enumeration:

- Fortaleza — `33.683.111/0004-41`
- Porto Alegre — `33.683.111/0011-70`
- Recife — `33.683.111/0005-22`
- Brasília — `33.683.111/0002-80`

A later fixture snapshot containing a fifth office is processed by the same recipe without code changes.

The four discovered seeds are then fed into the existing structured BrasilAPI acquisition path:

- unique discovered seeds: 4
- companies ingested: 4
- failures: 0
- evidence rows: 5 (one discovery-page evidence + four acquisition evidence records)

## Validation

`python -m unittest discover -s tests -v`

- `TESTS_DISCOVERED = 132`
- `TESTS_EXECUTED = 132`
- `TESTS_PASSED = 132`

## Gates

- `KNOWN_SOURCE_RECIPE = PASS`
- `DISCOVER_ONCE_REUSE = PASS`
- `RAW_DISCOVERY_PAGE_PRESERVED = YES`
- `DISCOVERY_SEEDS_HAVE_EVIDENCE_LINK = YES`
- `RECIPE_REPLAYS_ON_LATER_SNAPSHOT = PASS`
- `DISCOVERY_TO_STRUCTURED_ACQUISITION = PASS`
- `LLM_PER_PAGE = NO`
- `GENERIC_CRAWLER = NO`

## Classification

- Source-specific reusable recipe: `ENGINEERING_CHOICE` aligned with WebLists/SODIUM direction in the handoff.
- Four office facts used in the fixture: `LOCALLY_VERIFIED` against the current official Serpro page on 2026-08-21.
- Discovery coverage of the wider B2B universe: `UNKNOWN` and not claimed.
