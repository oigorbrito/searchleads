# Discovery Coverage Measurement v1

## Work unit

`DISCOVERY_COVERAGE_MEASUREMENT_V1`

This unit implements the scientific-foundation requirement that:

```text
DISCOVERY SUCCESS != DISCOVERY COVERAGE
```

It measures one explicit bounded discovery objective. It does **not** claim market-wide, B2B-wide, web-wide, or production discovery recall.

## Bounded evaluation scope

The evaluated source is the existing WU10 known-source recipe:

```text
recipe = serpro_office_directory_v1
url = https://www.serpro.gov.br/menu/institucional/quem-somos/encontre-o-serpro
```

The reference population is:

> Every visible headquarters/regional block on that exact known page that explicitly publishes a `CNPJ:` label.

The source page currently states that SERPRO has 28 localities overall. That prose count is **not** the denominator for this recipe, because WU10's identity-seed objective requires an explicit labelled CNPJ and does not promise to identify locations that do not publish one.

The manually enumerated and cross-checked current reference therefore contains 12 unique CNPJ-labelled identity blocks.

## Reference construction

The current reference was checked on 2026-08-25 against the public source page, which reports an update date of 2026-01-22, and cross-checked against the WU10 calibration set.

Reference CNPJs are stored as sorted WU3-compatible 14-character routing keys. The deterministic HTML fixture is a minimal calibration representation of those source blocks, not a byte-for-byte live capture.

The reference contract rejects:

- another source URL;
- another recipe ID;
- blank scope/reference descriptions;
- empty reference populations;
- duplicate reference IDs;
- unsorted reference tuples at the immutable model boundary;
- identifiers outside the 14-character routing contract.

`reference_from_mapping()` sorts fixture inputs deterministically before building that immutable reference.

## Measurement semantics

`measure_discovery_coverage()` compares emitted `DiscoveredCompanySeed` observations to the explicit reference set.

Reported values:

- unique discovered CNPJs;
- duplicate observation count;
- true positives;
- unexpected discovered CNPJs / false positives;
- missed reference CNPJs / false negatives;
- precision when at least one unique seed is emitted;
- recall, used here as bounded source-page coverage.

Duplicate observations never increase true-positive support.

A zero-discovery run has `precision = null` rather than an invented perfect precision, and `recall = 0` for the non-empty reference population.

Seeds produced by a different recipe are rejected rather than mixed into this denominator.

## Current measured result

For the 2026-08-25 reference snapshot:

```text
REFERENCE_CNPJ_BLOCKS = 12
DISCOVERED_UNIQUE_CNPJ_SEEDS = 12
DUPLICATE_OBSERVATIONS = 0
TRUE_POSITIVE = 12
FALSE_POSITIVE = 0
FALSE_NEGATIVE = 0
PRECISION = 100.0%
BOUNDED_SOURCE_PAGE_COVERAGE = 100.0%
```

This means the current WU10 recipe recovers every identity seed in this explicitly bounded reference snapshot.

It does **not** mean:

- 100% of SERPRO's 28 localities are identified;
- 100% of companies on the web are discovered;
- 100% B2B-market recall;
- the live page will never change;
- structured acquisition succeeds for every discovered seed.

## Discovery vs acquisition

This coverage metric ends at `DiscoveredCompanySeed`.

```text
reference source blocks
→ WU10 discovery recipe
→ discovered seeds
→ coverage measurement
```

BrasilAPI acquisition, source HTTP accessibility, and downstream extraction success are separate gates. A network outage therefore cannot silently become a discovery false negative in this deterministic measurement.

Live source accessibility remains tracked separately by issue #60.

## Miss/extra/duplicate diagnostics

The tests explicitly exercise:

- one missing reference CNPJ → one false negative;
- one unexpected CNPJ → one false positive;
- repeated observation of one CNPJ → duplicate count increments but unique/TP counts do not;
- zero discoveries → recall zero, precision undefined;
- recipe mismatch → rejected.

These diagnostics make the denominator and error classes auditable instead of reducing discovery quality to a single success flag.

## Verification

```text
FOCUSED_TESTS = 17/17 PASS
MODULE_LINE_COVERAGE = 100%
MEASURED_STATEMENTS = 70
MEASURED_BRANCHES = 20
CURRENT_REFERENCE = 12
CURRENT_DISCOVERED = 12
CURRENT_FALSE_POSITIVE = 0
CURRENT_FALSE_NEGATIVE = 0
CURRENT_BOUNDED_COVERAGE = 100.0%
```

These are deterministic regression/calibration measurements for one named source-page population.

## Gates

```text
EXPLICIT_BOUNDED_SCOPE = YES
REFERENCE_METHOD_DOCUMENTED = YES
DEFENSIBLE_DENOMINATOR = 12_CNPJ_LABELLED_BLOCKS
SOURCE_REPORTED_LOCALITIES = 28_CONTEXT_ONLY
DISCOVERY_SUCCESS_SEPARATE_FROM_COVERAGE = PASS
DUPLICATE_INFLATION = BLOCKED
MISSED_REFERENCE_REPORTED = YES
UNEXPECTED_SEED_REPORTED = YES
ACQUISITION_FAILURE_COUNTED_AS_DISCOVERY_MISS = NO
LIVE_SOURCE_ACCESSIBILITY_MEASURED_HERE = NO
MARKET_WIDE_COVERAGE_CLAIM = NO
GENERIC_CRAWLER = NO
BROAD_WEB_DISCOVERY = NO
ICP_DEFINED = NO
B2B_ASSUMPTION = PROVISIONAL
```
