# WORK UNIT 04 REPORT — COMPANY_NORMALIZATION_V1

## Scope

Implements deterministic normalization for company-related candidate facts without changing entity identity or source evidence.

Supported V1 categories:

- company names (`company_name`, `legal_name`, `trade_name`)
- domains
- HTTP/HTTPS website URLs
- phone values
- addresses
- locations (`city`, `state`, `country`, `location`)
- industry labels and CNAE codes
- LinkedIn / Instagram / generic social profile URLs

## Representation

Normalization is a **projection**, not a destructive persistence update.

```text
persisted CandidateFact
  raw_value = original source value
  normalized_value = null
      ↓ replay normalization rule
projected CandidateFact
  raw_value = original source value
  normalized_value = normalized representation
  normalization_rule = versioned rule id
```

The original persisted object remains unchanged. `normalize_persisted_candidate()` can reload a candidate after database reopen and recompute its normalization.

## Conservative rules

V1 intentionally does not:

- remove `Ltda.`, `S.A.` or other legal-name suffixes;
- infer `+55` for Brazilian-looking phone numbers;
- invent `https://` for scheme-less URLs;
- collapse `www.example.com` to `example.com`;
- geocode or canonicalize street addresses;
- map industry text into a taxonomy;
- make any entity-resolution decision.

## Rule examples

```text
legal_name
  company_name_nfkc_whitespace_v1

domain
  domain_lower_idna_v1

website_url / social URLs
  url_scheme_host_fragment_v1

phone
  phone_punctuation_only_v1

state (two-letter code)
  state_two_letter_upper_v1

primary_cnae_code
  cnae_digits7_v1
```

## Validation

```text
TESTS_DISCOVERED = 46
TESTS_EXECUTED = 46
TESTS_PASSED = 46
```

Coverage includes:

- NFKC and whitespace normalization for names/text;
- preservation of legal suffixes;
- host extraction/lowercasing for domains;
- explicit-scheme URL normalization with default-port/fragment removal;
- rejection of scheme-less URLs rather than HTTPS inference;
- punctuation-only phone normalization without country inference;
- address whitespace normalization without geocoding;
- state-code uppercasing;
- seven-digit CNAE normalization;
- social URL normalization;
- explicit `UNSUPPORTED` and `INVALID` states;
- preservation of candidate ID, provenance, confidence, and raw value;
- normalization replay after SQLite close/reopen.

## Decision classification

### EVIDENCE_BACKED

- raw and normalized representations must remain distinguishable;
- normalization is separate from entity matching/fusion.

### ENGINEERING_CHOICE

- NFKC + whitespace collapse for textual representation;
- lowercase/IDNA host normalization;
- HTTP/HTTPS URL normalization rules;
- punctuation-only phone normalization;
- seven-digit CNAE representation;
- normalized values as non-persisted reproducible projections in V1.

### LOCALLY_VERIFIED

- 46/46 tests pass against the current stacked implementation.

### HYPOTHESIS

- B2B remains provisional.

### UNKNOWN

- ICP;
- matching weights/thresholds;
- whether any additional normalization increases entity-resolution precision/recall;
- authoritative address/industry taxonomies for later enrichment.

## Work Unit 3 dependency note

The Work Unit 3 production HTTP smoke remains blocked by the execution environment's lack of outbound DNS. This normalization work is source-independent and stacked on the Work Unit 3 branch; it does not relabel that external gate as passed.

## Next work unit

Per the supplied roadmap: `COMPANY_ENTITY_RESOLUTION_V1`.
