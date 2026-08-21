# Architecture Principles — Leads V1

## Scope boundary

The repository is implemented incrementally by work unit. Through Work Unit 4 it includes the scientific/domain foundation, evidence-preserving persistence, exactly one narrow real-source adapter, and deterministic company normalization. It still intentionally does **not** implement broad crawling, entity-resolution scoring, contact discovery/validation, person discovery, qualification scoring, exports, retries/scheduling, or a universal framework.

## Principles

### P1 — Company and Lead are distinct

`EVIDENCE_BACKED` at the logical/domain level from the supplied handoff.

A `Company` is a discovered business entity. A `Lead` is a separate commercial-pipeline entity linked to a company. Creating a company never automatically creates a lead.

### P2 — Provenance is per fact

`EVIDENCE_BACKED` from the supplied handoff and W3C PROV direction.

`CandidateFact` and `CanonicalFact` each carry a `Provenance` object containing evidence identifiers and generation activity. A single company can therefore have facts from different sources.

### P3 — Raw observation is preserved

`EVIDENCE_BACKED` architectural direction from the supplied handoff.

`Evidence.payload` preserves the source observation. `CandidateFact` separately stores `raw_value` and optional `normalized_value` plus `normalization_rule`.

### P4 — Candidate fact is not canonical fact

`EVIDENCE_BACKED` direction from the data-integration baseline.

Source-derived assertions are modeled as `CandidateFact`. Selection/fusion produces `CanonicalFact`, which references one or more candidate facts.

### P5 — Conflicts are first-class

`EVIDENCE_BACKED` direction from MaDI-Bench and the handoff.

A `Conflict` contains at least two competing candidate fact IDs for a single subject/predicate and can remain open or resolve to a canonical fact.

### P6 — Contacts are evidence-bearing entities

`EVIDENCE_BACKED` from the handoff.

A `ContactPoint` has its own identity, owner, kind, value, provenance, and state. Discovery is not validation.

### P7 — Person/company relationship requires evidence

`EVIDENCE_BACKED` from the handoff's person-and-role rule.

`ProfessionalRole` explicitly links person and company and requires provenance. The core `Person` object intentionally does not infer employer from a name.

### P8 — No entity-resolution weights yet

`UNKNOWN` / not yet locally validated.

The model exposes identity-bearing facts but defines no similarity weights, thresholds, merge rules, or blocking strategy. Those belong to `COMPANY_ENTITY_RESOLUTION_V1`.

### P9 — No ICP or opaque scoring

ICP is `UNKNOWN`; B2B is `HYPOTHESIS` / `PROVISIONAL`.

The `Lead` model can represent a qualification status and explicit reasons, but this work unit contains no qualification algorithm or weights.

## Engineering choices in the domain foundation

The following are `ENGINEERING_CHOICE`, not scientific conclusions:

- Python 3.11+ as the implementation language.
- Standard-library `dataclasses` and `Enum`; no third-party runtime dependencies.
- Opaque string identifiers rather than prescribing UUIDs/database keys.
- Immutable (`frozen`) value objects for the initial domain representation.
- Timezone-aware timestamps are required for evidence/provenance.
- Confidence, when present, is constrained to `[0, 1]` but no calibration semantics are claimed.
- `ContactStatus.VALIDATED` is used for the initial contact state vocabulary from the handoff; the validation technique is deliberately unspecified.
- A qualified `Lead` requires at least one human-readable reason so the model cannot represent a reasonless opaque positive decision.

## Persistence principles — Work Unit 2

### P10 — Persistence preserves evidence before interpretation

`EVIDENCE_BACKED` architectural direction from the supplied handoff.

`Evidence.payload` is stored independently from candidate/canonical facts. Persisting a normalized or canonical value never rewrites the raw observation.

### P11 — Persisted evidence is reprocessable

`EVIDENCE_BACKED` requirement from the supplied Work Unit 2 gate.

The persistence boundary can enumerate previously stored evidence, including after the database is closed and reopened, so future extraction/normalization logic can be rerun from stored observations.

### P12 — Stable IDs cannot silently rewrite immutable records

`ENGINEERING_CHOICE` supporting provenance integrity.

An exact repeated write is idempotent. Reusing an existing stable ID for different stored content raises an `IdentityCollisionError`; the store does not silently overwrite evidence or fact history.

### P13 — Referential existence is checked at the persistence boundary

`ENGINEERING_CHOICE`.

Evidence requires a persisted source; contact provenance and fact provenance require persisted evidence; canonical facts require their candidate facts; resolved conflicts require the referenced canonical fact. These checks assert representational integrity only and do not claim source authority or factual correctness.

### P14 — SQLite is a replaceable persistence implementation

`ENGINEERING_CHOICE`.

SQLite was selected for Work Unit 2 because it is deterministic, transactional, file-backed, available in the Python standard library, and sufficient to validate round-trip/reprocessing gates without introducing external infrastructure. It is not treated as a permanent architectural mandate.

## Real-source principles — Work Unit 3

### P15 — One source before many sources

`ENGINEERING_CHOICE` following the staged handoff.

Work Unit 3 integrates only BrasilAPI. No source registry, plugin framework, or generic crawler is introduced.

### P16 — Acquisition precedes interpretation

`EVIDENCE_BACKED` architectural direction from the supplied handoff.

The complete JSON mapping returned by the source transport is persisted as `Evidence.payload` before derived `CandidateFact` records are saved. A change in future extraction logic can therefore be replayed from stored evidence.

### P17 — BrasilAPI data remains source evidence, not canonical truth

`LOCALLY_VERIFIED` against current documentation and issue history.

BrasilAPI documents its CNPJ endpoint as returning company-registration data and describes the endpoint as a Minha Receita-backed lookup. Recent BrasilAPI issue/discussion history contains examples of stale or divergent CNPJ data. The adapter therefore creates candidate facts, never verified/canonical facts.

### P18 — Point lookup only; no crawling/full scan

`ENGINEERING_CHOICE` aligned with current BrasilAPI terms.

Work Unit 3 uses only `GET /api/cnpj/v1/{cnpj}` for a known CNPJ. BrasilAPI terms explicitly ask consumers not to use automated crawling or full scans, so this source adapter is not treated as a broad discovery mechanism.

### P19 — Source fields are extracted, not normalized

`ENGINEERING_CHOICE` preserving roadmap boundaries.

The adapter maps a small set of raw source fields to domain predicates (`business_registry_id`, `legal_name`, `trade_name`, registration status, primary CNAE, city, state). It intentionally leaves `normalized_value` empty. `COMPANY_NORMALIZATION_V1` remains the next work unit.

### P20 — Contacts and people remain deferred

`ENGINEERING_CHOICE` preserving roadmap order.

Even if BrasilAPI returns phone, email, or QSA data, Work Unit 3 does not turn those fields into `ContactPoint`, `Person`, or `ProfessionalRole` records. Those capabilities have dedicated later work units.

## Explicitly unsupported assumptions

None are intentionally introduced. In particular, the project does not assume:

- that company name equality identifies a company;
- that a domain always uniquely identifies a legal entity;
- any contact-validation technique;
- any ICP;
- any source authority ordering;
- any matching threshold or score;
- that SQLite is the final production database;
- that BrasilAPI is authoritative or sufficient for company identity;
- that CNPJ lookup alone provides discovery coverage.

## Normalization principles — Work Unit 4

### P21 — Normalization is non-destructive

`EVIDENCE_BACKED` architectural direction from the supplied handoff.

Normalization never overwrites the persisted source-derived `CandidateFact`. A normalized projection keeps the same raw value and provenance while adding `normalized_value` and `normalization_rule`. Rules can therefore be changed and replayed from stored facts.

### P22 — Normalization does not perform entity resolution

`ENGINEERING_CHOICE` preserving roadmap boundaries.

V1 normalization standardizes representation only. It does not decide that two companies, domains, phones, addresses, or industry labels refer to the same entity. Matching remains `COMPANY_ENTITY_RESOLUTION_V1`.

### P23 — Conservative normalization avoids invented semantics

`ENGINEERING_CHOICE`.

V1 does not remove legal suffixes, infer a Brazilian country code for phones, assume HTTPS for scheme-less URLs, collapse subdomains to registrable domains, geocode addresses, or map free-text industries into a taxonomy. Those transformations can change meaning and require separate evidence or local validation.

### P24 — Rule names are part of the audit trail

`ENGINEERING_CHOICE`.

Every successful normalized projection records a versioned rule identifier such as `company_name_nfkc_whitespace_v1`, `domain_lower_idna_v1`, or `cnae_digits7_v1`. Unsupported and invalid inputs are represented explicitly rather than silently coerced.
