# SearchLeads Architecture Principles v1

## Scope

The scientific/domain foundation is followed by evidence-preserving persistence. Acquisition, source-specific extraction, normalization rules, entity-resolution algorithms, contact-validation methodology, and qualification criteria remain outside these first two work units.

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
13. **Raw evidence is persisted independently from interpretation.** Storage of candidate/canonical facts never rewrites the captured raw payload.
14. **Stable IDs do not silently overwrite history.** Exact repeated writes are idempotent; different content under the same immutable ID is a persistence conflict.
15. **Persistence checks directional references.** Evidence requires its Source; provenance/facts require their evidence and derivation records; Person/ContactPoint/Lead require their owning records. `Company` aggregate reference snapshots are not rigid foreign keys in v1 because enforcing them would create insertion cycles with immutable child records.
16. **Reprocessing starts from verified stored evidence.** Evidence can be replayed in deterministic capture order and raw payload integrity is checked before it is returned.
17. **Storage technology remains replaceable.** SQLite is an `ENGINEERING_CHOICE` for v1 persistence, not a permanent production-database mandate.

## Engineering choices in v1-v2

- Python 3.11+.
- Standard-library dataclasses and enums for the runtime domain model.
- Immutable (`frozen`) value objects with validation in `__post_init__`.
- String IDs so persistence/ID-generation strategy remains decoupled from the domain.
- Pytest for executable invariants.
- SQLite via Python stdlib `sqlite3` for the first persistence boundary.
- Deterministic tagged JSON for domain envelopes and raw textual Evidence in UTF-8 BLOB storage.
- Internal SHA-256 only for storage-integrity verification; source `content_digest` semantics are preserved as supplied.

These are `ENGINEERING_CHOICE`, not evidence-backed claims.

## Deferred decisions

- Production persistence engine and scale strategy.
- Schema migrations after v1.
- Real source selection.
- Binary/non-text acquisition artifacts.
- Normalization rules.
- Company entity-resolution blocking/matching algorithms and weights.
- Contact validation methodology.
- Qualification criteria/ICP.
- Export format and public API.

## First real source — Work Unit 3

18. **One source before many sources.** `LEADS_FIRST_REAL_SOURCE_V1` integrates only BrasilAPI CNPJ v1; it does not create a generic source/plugin framework.
19. **Point lookup only.** BrasilAPI is used only for a CNPJ already known by the caller. Current service terms explicitly discourage crawling/full scans.
20. **HTTP evidence precedes payload interpretation.** A response body is persisted before JSON validation, identity checks, or field extraction. Network failures with no response remain acquisition errors rather than invented Evidence.
21. **Source data remains candidate evidence.** BrasilAPI values become `CandidateFact`, not canonical/verified truth. No source-authority ranking is introduced.
22. **Current CNPJ transport contract is alphanumeric.** The adapter routing key follows the currently documented 14-character `0-9A-Z` contract and does not preserve the obsolete digits-only assumption from the legacy implementation.
23. **Anti-abuse behavior is explicit.** The transport sends an identifying User-Agent and represents non-200 response bodies as Evidence before returning an operational error. Retry/backoff policy remains deferred.
24. **Source extraction is bounded.** Only the explicitly documented company predicates in `docs/FIRST-REAL-SOURCE.md` are mapped. Contact, QSA/Person, canonicalization, normalization, and qualification remain later work units.
