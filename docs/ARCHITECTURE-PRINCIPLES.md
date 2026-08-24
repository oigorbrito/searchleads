# SearchLeads Architecture Principles v1

## Scope

This work unit implements only the scientific/domain foundation needed before a real source is introduced.

## Principles

1. **Specialized lead system, not a universal framework.** The domain is Company, Person, ContactPoint, Lead, facts, evidence, provenance, and conflicts.
2. **Facts are evidence-backed.** A `CandidateFact` cannot exist without at least one evidence reference.
3. **Provenance is per fact.** A derivation record names the subject, field, evidence, activity, and optional agent/parents.
4. **Raw and normalized values are separate.** Candidate facts retain both representations so later normalization can be audited.
5. **Canonicalization never erases candidates.** `CanonicalFact` references one or more candidate facts and records a resolution method.
6. **Conflict is first-class.** An unresolved disagreement can remain open; the system does not force a value.
7. **Company identity is multi-signal.** This model deliberately does not encode company-matching weights before local evaluation.
8. **Person identity is separate from company identity.** A person requires a company relationship with evidence in v1.
9. **Contact discovery is separate from validation.** Contacts default to `DISCOVERED`; validated/invalid/stale states require validation evidence and time.
10. **Company is not Lead.** `Lead` wraps a `Company` for commercial pipeline use. Qualification defaults to `UNKNOWN` while ICP is undefined.
11. **Decision classification is explicit.** Important decisions can be tagged `EVIDENCE_BACKED`, `HYPOTHESIS`, `ENGINEERING_CHOICE`, `LOCALLY_VERIFIED`, or `UNKNOWN`.
12. **No LLM-per-page default.** Reusable extraction is preferred where a source pattern proves repeatable, but no crawler/extractor is implemented here.

## Engineering choices in v1

- Python 3.11+.
- Standard-library dataclasses and enums for the runtime domain model.
- Immutable (`frozen`) value objects with validation in `__post_init__`.
- String IDs so persistence/ID-generation strategy remains decoupled from the domain.
- Pytest for executable invariants.

These are `ENGINEERING_CHOICE`, not evidence-backed claims.

## Deferred decisions

- Persistence engine and schema.
- Real source selection.
- Normalization rules.
- Company entity-resolution blocking/matching algorithms and weights.
- Contact validation methodology.
- Qualification criteria/ICP.
- Export format and public API.
