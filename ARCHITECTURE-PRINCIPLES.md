# Architecture Principles — Leads V1

## Scope boundary

This work unit implements only the scientific/domain foundation. It intentionally does **not** implement crawling, real-source acquisition, persistence, normalization algorithms, entity-resolution scoring, contact validation, qualification scoring, exports, retries, scheduling, or a universal framework.

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

## Engineering choices in this implementation

The following are `ENGINEERING_CHOICE`, not scientific conclusions:

- Python 3.11+ as the implementation language.
- Standard-library `dataclasses` and `Enum`; no third-party runtime dependencies.
- Opaque string identifiers rather than prescribing UUIDs/database keys.
- Immutable (`frozen`) value objects for the initial domain representation.
- Timezone-aware timestamps are required for evidence/provenance.
- Confidence, when present, is constrained to `[0, 1]` but no calibration semantics are claimed.
- `ContactStatus.VALIDATED` is used for the initial contact state vocabulary from the handoff; the validation technique is deliberately unspecified.
- A qualified `Lead` requires at least one human-readable reason so the model cannot represent a reasonless opaque positive decision.

## Explicitly unsupported assumptions

None are intentionally introduced. In particular, this work unit does not assume:

- that company name equality identifies a company;
- that a domain always uniquely identifies a legal entity;
- any contact-validation technique;
- any ICP;
- any source authority ordering;
- any source-specific extraction strategy;
- any matching threshold or score.
