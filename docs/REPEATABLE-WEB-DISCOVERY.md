# Repeatable Web Discovery v1

## Work unit

`REPEATABLE_WEB_DISCOVERY_V1`

This unit implements the project principle:

```text
KNOWN SOURCE → DISCOVER EXTRACTION → REUSE
```

for exactly one source-specific recipe: repeated office blocks on the official SERPRO office directory.

It is **not** a generic crawler, agent framework, browser orchestration layer, or LLM-per-page extraction loop.

## Recipe

```text
RECIPE_ID = serpro_office_directory_v1
URL = https://www.serpro.gov.br/menu/institucional/quem-somos/encontre-o-serpro
```

The recipe accepts only that known HTTPS SERPRO path. Query strings/fragments are discarded for Evidence identity; another host/path, credentials, HTTP scheme, or non-default port is rejected.

## Pipeline

```text
preserved SERPRO office-directory HTML snapshot
→ source-specific visible-text block parser
→ explicit CNPJ-labelled block extraction
→ WU3-compatible 14-character CNPJ routing seeds
→ Evidence-linked DiscoveredCompanySeed records
→ optional structured acquisition callback
```

The discovery step does not itself create a Company or claim that a seed is a verified company record. Structured source acquisition remains a separate downstream operation.

## Extraction boundary

The parser deliberately uses the known repeated block structure rather than generic page understanding:

- `<h2>` / `<h3>` boundaries delimit source blocks;
- `script`, `style`, `template`, and `noscript` text is ignored;
- a seed requires an explicit `CNPJ:` label;
- current numeric and future alphanumeric formatted CNPJ representations are accepted and compacted to the WU3 `0-9A-Z` 14-character routing key;
- duplicate CNPJ observations are emitted once per snapshot;
- a block with multiple different CNPJs is ambiguous and emits no seed;
- city/state text is preserved when the source explicitly exposes `city/state`; no state-code taxonomy is invented;
- a valid labelled CNPJ may still be emitted when optional location text is missing.

## Raw discovery Evidence

The complete supplied HTML snapshot is preserved as `Evidence` before discovered seeds are returned.

Evidence metadata records:

```text
recipe_id = serpro_office_directory_v1
agent = searchleads.repeatable_discovery.serpro_offices.v1
content_type = text/html
```

Evidence identity includes recipe + normalized source URL + exact HTML. Reprocessing the same snapshot reuses the original immutable Evidence; a changed page snapshot creates new Evidence and the same recipe is replayed without code changes.

Every returned seed carries `discovery_evidence_id` pointing to that snapshot.

## WU3 compatibility

WU3's current BrasilAPI routing contract accepts exactly 14 characters from `0-9A-Z` after transport-format removal.

WU10 emits that same representation. It does not add business-field normalization or claim registry validity beyond the source observation.

`acquire_discovered_seeds()` is intentionally protocol-driven: callers may feed each emitted `seed.cnpj` into the existing structured point-lookup path, for example a `BrasilAPISource.ingest(...)` call. Failures are recorded per seed and do not prevent later seeds from being attempted.

This boundary preserves the distinction:

```text
discovery Evidence != structured acquisition Evidence
```

## Curated recipe benchmark

The deterministic fixture has 10 adversarial scenarios covering:

- repeated valid office blocks;
- duplicate CNPJ in one block;
- duplicate CNPJ across blocks;
- malformed CNPJ;
- hidden/script/template distractors;
- unlabelled CNPJ-like text;
- ambiguous blocks with two different CNPJs;
- alphanumeric CNPJ representation;
- missing optional location;
- source noise outside named office blocks.

Measured result:

```text
SCENARIOS = 10
EXPECTED_SEEDS = 11
TRUE_POSITIVE = 11
FALSE_POSITIVE = 0
FALSE_NEGATIVE = 0
PRECISION = 100.0%
RECALL = 100.0%
F1 = 100.0%
```

These are local curated-contract metrics, not production web-discovery accuracy or B2B-market coverage estimates.

## Current SERPRO calibration — checked 2026-08-25

The official page currently reports `Atualizado em 22 de janeiro de 2026` and exposes CNPJ-bearing blocks for the headquarters plus eleven regional entries used by the calibration fixture.

Current calibration:

```text
UNIQUE_CNPJ_SEEDS = 12
HEADQUARTERS = 33.683.111/0001-07
FORTALEZA = 33.683.111/0004-41
PORTO_ALEGRE = 33.683.111/0011-70
RECIFE = 33.683.111/0005-22
BRASILIA_REGIONAL = 33.683.111/0002-80
SAO_PAULO = 33.683.111/0009-56
```

The fixture is a minimal representation of currently verified source blocks; it is not represented as a byte-for-byte live page capture. The execution container still cannot perform direct GitHub/network cloning, so current public source verification was done separately from the deterministic local recipe run.

## Verification

```text
WU10_FOCUSED_TESTS = 26/26 PASS
WU10_MODULE_LINE_COVERAGE = 100%
WU10_MEASURED_STATEMENTS = 200
RECIPE_BENCHMARK = PASS
CURRENT_CALIBRATION_UNIQUE_SEEDS = 12
PYTHON_MODULE_COMPILE = PASS
```

The WU10 runtime validation shell uses the exact current `Source`/`Evidence` constructor contract read from PR #50 and a repository protocol for deterministic unit testing. The published module imports `searchleads.domain` from the real clean stack and does not ship the local validation shell.

## Gates

```text
KNOWN_SOURCE_RECIPE = PASS
RECIPE_VERSIONED = YES
KNOWN_URL_BOUNDARY = PASS
RAW_DISCOVERY_PAGE_PRESERVED = YES
DISCOVERY_SEEDS_HAVE_EVIDENCE_LINK = YES
RECIPE_REPLAYS_ON_CHANGED_SNAPSHOT = PASS
DUPLICATE_SEED_INFLATION = BLOCKED
AMBIGUOUS_BLOCK_AUTO_SEED = NO
WU3_ROUTING_KEY_COMPATIBLE = YES
DISCOVERY_TO_STRUCTURED_ACQUISITION_BOUNDARY = PASS
LLM_PER_PAGE = NO
GENERIC_CRAWLER = NO
BROAD_WEB_COVERAGE_CLAIM = NO
CURATED_PRECISION = 100.0%
CURATED_RECALL = 100.0%
FOCUSED_TESTS = 26/26 PASS
LINE_COVERAGE_NEW_MODULE = 100%
ICP_DEFINED = NO
B2B_ASSUMPTION = PROVISIONAL
```

## Next work unit

Per the original handoff sequence after repeatable web discovery: `SELECTIVE_REVIEW_V1`.
