# SearchLeads Company Normalization v1

## Work unit

`COMPANY_NORMALIZATION_V1`

This unit adds deterministic, non-destructive normalization over immutable `CandidateFact` records. It standardizes representation only. It does **not** decide that two records identify the same company and does not create `CanonicalFact` values.

## Gates

- `RAW_VALUE_PRESERVED = YES`
- `NORMALIZATION_REPLAYABLE = YES`
- `RULE_EXPLICIT = YES`
- `ENTITY_RESOLUTION_PERFORMED = NO`
- `SOURCE_FACTS_REWRITTEN = NO`

## Representation

The clean domain already contains `CandidateFact.raw_value` and `CandidateFact.normalized_value`. V1 therefore produces a projection rather than adding another domain fact type or mutating the persisted source record:

```text
persisted CandidateFact
  raw_value = source observation
  normalized_value = null
      ↓ deterministic normalizer
NormalizationResult
  source_fact = persisted immutable fact
  normalized_fact.normalized_value = normalized representation
  normalization_rule = versioned rule identifier
```

`normalization_rule` lives on `NormalizationResult`, not inside `CandidateFact`. This is intentional: the clean scientific/domain foundation does not contain a `normalization_rule` field, and Work Unit 4 does not change that domain contract.

The projected `CandidateFact` preserves the source fact ID, subject, field, raw value, evidence IDs, provenance ID, confidence, decision class, and observation time. The persisted raw fact remains unchanged and can be reloaded and normalized again after closing/reopening SQLite.

## Status vocabulary

- `NORMALIZED`: a supported rule produced a representation different from `raw_value`.
- `UNCHANGED`: a supported rule ran and the normalized representation equals `raw_value`.
- `UNSUPPORTED`: V1 has no rule for this field; no coercion is attempted.
- `INVALID`: the field is recognized but the supplied value cannot be normalized safely by its V1 rule.

Unsupported and invalid values never receive a projected fact or a rule ID.

## V1 rules

| Fields | Rule | V1 behavior |
| --- | --- | --- |
| `company_name`, `legal_name`, `trade_name` | `company_name_nfkc_whitespace_v1` | Unicode NFKC + whitespace collapse; preserves case and legal suffixes. |
| `domain` | `domain_lower_idna_v1` | Extract host, normalize DNS/valid IP literal representation, IDNA + lowercase; does not collapse subdomains/root domain. |
| `website`, `website_url`, `url`, social-profile URLs | `url_scheme_host_fragment_v1` | Requires explicit HTTP/HTTPS; lowercases scheme/host, IDNA-normalizes host, removes default port and fragment; preserves path/query. |
| `phone`, `company_phone` | `phone_punctuation_only_v1` | Removes non-digits while preserving an explicit leading `+`; does not infer country code. |
| `state` | `state_two_letter_upper_v1` or text rule | Two-letter alphabetic state codes uppercase; longer text is only NFKC/whitespace normalized. |
| `primary_cnae_code`, `cnae_code` | `cnae_digits7_v1` | String/integer input becomes exactly seven digits after punctuation removal. |
| address/location/industry/status/description fields | `text_nfkc_whitespace_v1` | Unicode NFKC + whitespace collapse only. |

DNS-like hosts with invalid numeric IP literals, underscore labels, leading/trailing hyphens, invalid ports, malformed bracket notation, oversized hosts, or credential-bearing URLs are rejected rather than silently coerced.

## Conservative non-goals

V1 intentionally does **not**:

- remove `Ltda.`, `S.A.`, `Inc.`, or other legal suffixes;
- lowercase company names;
- infer `+55` or any other phone country code;
- infer `https://` for a scheme-less website URL;
- collapse `www.example.com` or another subdomain to `example.com`;
- geocode or canonicalize street addresses;
- translate city/state/country names;
- map free-text industries to a taxonomy;
- treat equal normalized values as an entity match;
- fuse multiple candidate facts;
- rewrite source evidence or source-derived candidate records.

Those decisions can change meaning and belong to later evidence-backed/local-validation work units.

## BrasilAPI integration boundary

The current WU3 adapter emits eight bounded company fields. WU4 handles them as follows:

| BrasilAPI-derived field | WU4 result |
| --- | --- |
| `business_registry_id` | `UNSUPPORTED` in generic normalization V1 |
| `legal_name` | supported |
| `trade_name` | supported |
| `registration_status` | supported |
| `primary_cnae_code` | supported |
| `primary_cnae_description` | supported |
| `city` | supported |
| `state` | supported |

`business_registry_id` remains unsupported deliberately. The predicate is generic; hard-coding CNPJ semantics into it would incorrectly assume every future registry identifier follows the Brazilian CNPJ representation. The BrasilAPI adapter already has a source-specific CNPJ routing-key normalizer for acquisition identity. Cross-source registry-identifier semantics belong to the entity-resolution design.

## Replay

`normalize_persisted_candidate(repository, fact_id)` reloads a persisted `CandidateFact` through `SQLiteRepository` and reruns the current V1 rule from `raw_value`. The stored fact is not updated.

This makes rule changes measurable: a later version can replay the same raw facts and compare outputs without losing the source observation.

## Verification

Final local verification for the clean stack:

- 172 pre-WU4 tests retained and passing;
- 81 focused normalization tests passing;
- 253 total tests passing;
- 100% line coverage across 832 measured package statements;
- `python -m compileall -q src tests`: PASS;
- `ResourceWarning` treated as error during pytest runs.

The tests include names/text, Unicode NFKC, domains, IDNA, IPv4/IPv6, malformed hosts, URL safety, ports/fragments, phones, states, CNAE, social URLs, unsupported/invalid states, projection invariants, batch ordering, SQLite reopen/replay, and the WU3 BrasilAPI-to-normalization boundary.

## Decision classification

### EVIDENCE_BACKED direction

- raw and normalized representations remain distinguishable;
- normalization remains separate from entity matching/fusion;
- raw source facts remain replayable.

### ENGINEERING_CHOICE

- NFKC + whitespace collapse;
- DNS/IDNA host representation;
- explicit HTTP/HTTPS URL rule;
- punctuation-only phone rule;
- uppercase two-letter state representation;
- seven-digit CNAE representation;
- `NormalizationResult` as the audit envelope rather than changing `CandidateFact`.

### LOCALLY_VERIFIED

- 81/81 focused normalization tests pass;
- 253/253 full clean-stack tests pass;
- 100% measured line coverage.

### UNKNOWN / deferred

- production impact of each normalization rule on ER precision/recall;
- cross-source registry-identifier normalization;
- authoritative address/industry taxonomies;
- entity-resolution weights/thresholds;
- ICP/qualification policy.

## Dependency note

The WU3 live BrasilAPI HTTP smoke remains separately blocked by the execution environment's DNS. WU4 is source-independent after candidate facts exist and does not relabel that external WU3 gate as passed.

## Next work unit

Per the staged roadmap: `COMPANY_ENTITY_RESOLUTION_V1`.
