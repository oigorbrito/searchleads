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
- Production validation/calibration of normalization rules.
- Production calibration/generalization of company entity-resolution blocking and review policy.
- Persisted merge/split mechanics after an ER decision.
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

## Company normalization — Work Unit 4

25. **Normalization is non-destructive.** `COMPANY_NORMALIZATION_V1` projects a normalized representation from immutable `CandidateFact.raw_value`; it does not update the persisted source candidate.
26. **Rule identity is explicit.** Every successful/unchanged supported normalization returns a versioned rule ID in `NormalizationResult`. `UNSUPPORTED` and `INVALID` never silently coerce values.
27. **Normalization does not equal entity resolution.** Equal normalized representations are inputs to later ER; WU4 never auto-matches, fuses, canonicalizes, or changes company identity.
28. **Conservative transformations avoid invented semantics.** V1 preserves legal suffixes/case, does not infer phone country codes or URL schemes, does not collapse root domains, and does not geocode/map industries.
29. **Host normalization is strict.** DNS labels/IDNA, valid IP literals, explicit HTTP/HTTPS ports, and credential-bearing URLs are validated so malformed network identifiers do not become normalized matching signals.
30. **Generic registry identifiers remain generic.** WU4 does not hard-code CNPJ normalization into the generic `business_registry_id` predicate. Source-specific CNPJ routing normalization remains in the BrasilAPI adapter until cross-source identifier semantics are designed.


## Company entity resolution — Work Unit 5

31. **Entity resolution is measured, not assumed.** `COMPANY_ENTITY_RESOLUTION_V1` separates blocking, pairwise features, experimental strategies, operational triage, and evaluation against an explicit labeled benchmark.
32. **Registry identity is namespaced.** A registry identifier is a hard signal only when both observations declare a supported compatible namespace. V1 supports `br:cnpj`; generic/unknown registry IDs are not silently treated as equivalent.
33. **Conflicting supported full registry IDs veto same-registered-entity matching.** This V1 target is the same registered/operational entity, not a corporate group, franchise, brand, or parent/subsidiary relationship. Different CNPJs may still be related organizations but are not auto-merged as one registered entity.
34. **Blocking must preserve duplicate recall.** Candidate generation uses transparent keys (namespaced registry, WU4 domain/phone, and name-prefix keys) and is evaluated over the full benchmark observation corpus before pair classification.
35. **Fuzzy/weighted scores are evaluation instruments, not automatic merge authority.** The benchmark shows materially non-zero false-merge rates even at high thresholds, so V1 does not use weighted score for `AUTO_MATCH`.
36. **Operational triage is asymmetric toward false-merge avoidance.** Exact supported namespaced registry equality may `AUTO_MATCH`; conflicting supported registry IDs are `DISTINCT`; strong multi-signal evidence becomes `REVIEW`; remaining cases are `INSUFFICIENT_EVIDENCE`.
37. **ER decisions do not mutate persistence in V1.** The unit produces comparison/triage decisions only. Persisted Company merge/split/canonicalization mechanics remain later work.

## Company field fusion — Work Unit 6

38. **Fusion happens only inside one subject + field.** Mixing companies or predicates is rejected.
39. **Effective value uses normalized representation when available, otherwise raw source value.** Raw candidates remain immutable.
40. **Unanimity may canonicalize; disagreement remains conflict.** V1 creates a `CanonicalFact` only when every distinct candidate observation has the same effective value.
41. **Majority is diagnostic, not truth.** Support counts and ratios may be reported, but they do not select a canonical value.
42. **Duplicate candidate IDs cannot inflate support.** Repeated use of the same fact ID is rejected before support aggregation.
43. **Derived canonical provenance is explicit.** Fusion creates a new `Provenance` that unions supporting evidence and lists every parent candidate fact ID in `derived_from_fact_ids`.
44. **Persistence order preserves referential integrity.** Fusion Provenance is persisted before the `CanonicalFact` that references it; conflicts reference the existing candidates directly.
45. **No source-authority model is invented.** Correlated sources, freshness, temporal truth decay, learned truth discovery, and source dependence remain future work.

## Company contact discovery — Work Unit 7

46. **Discovery never implies validation.** Every new company contact observation remains `DISCOVERED`; deliverability, reachability, ownership, freshness, and control remain unknown until a later validation unit.
47. **A known Company owns WU7 contacts.** Contact discovery does not create Person records and does not promote LinkedIn personal profiles; person-associated channels remain a later concern.
48. **Raw page evidence precedes extraction.** An HTTP response body is persisted before non-200 rejection or contact parsing. Network failure without a response produces no fabricated Evidence.
49. **Phone extraction is label/link constrained.** Arbitrary digit strings, CNPJ, CEP, and dates do not become phones; V1 accepts explicit `tel:` URIs or phone-labeled visible text.
50. **Hidden/non-rendered text is excluded.** Script, style, template, and noscript content do not generate contacts.
51. **Company social discovery is narrow.** LinkedIn requires `/company/<slug>` and Instagram requires a single profile-path segment; content/post/person subroutes are not promoted into company contacts.
52. **A contact form is represented by the page containing the form.** The form submission endpoint is not treated as a contact channel because it may be internal or third-party infrastructure.
53. **Contact observations are snapshot-scoped and evidence-linked.** Contact IDs include the Evidence snapshot, allowing changed pages to create new immutable observations without rewriting prior discovery history.
