# searchleads

B2B lead discovery and enrichment with fact-level provenance and explicit validation boundaries.

## Architecture

DISCOVERY → ACQUISITION → EVIDENCE → STRUCTURED EXTRACTION → NORMALIZATION → ENTITY RESOLUTION → ENRICHMENT/FUSION → QUALIFICATION → EXPORT

Cross-cutting concerns: PROVENANCE / VALIDATION / CONFIDENCE / REVIEW.

## Scientific invariants

- Company is not a Lead.
- Found is not Valid.
- Name match is not entity match.
- Contact found is not contact valid.
- A value without Evidence is not a verified fact.
- Discovery success is not coverage.
- Provenance is fact-level.
- ICP, score, geography, company size, job titles and qualification criteria must not be invented.

## Persistence boundary

SQLite is the local/reference persistence boundary. Schema evolution uses `PRAGMA user_version` plus additive `PRAGMA table_info` repair for historical databases whose version does not fully describe their shape. Raw evidence is stored as immutable BLOB content and must survive migration byte-for-byte.

## Known real source

The first real acquisition source is the SEC EDGAR `company_tickers_exchange.json` dataset. Acquisition requires an explicit User-Agent, raw response bytes become immutable Evidence, and parsing rejects schema drift instead of silently guessing a new mapping. The default bounded ingestion selects at most 25 company records and emits fact-level CandidateFact provenance for CIK, legal name, ticker and exchange.

## Normalization boundary

Company-name normalization is deterministic and auditable but does not resolve identity. V1 applies Unicode NFKC, whitespace collapse and casefold only. It deliberately preserves punctuation and legal suffixes so normalization cannot silently erase distinctions needed by entity resolution.

## Work units

- `LEADS_SCIENTIFIC_FOUNDATION_AND_DOMAIN_V1`: immutable domain values and core scientific invariants.
- `LEADS_PERSISTENCE_AND_EVIDENCE_V1`: versioned SQLite schema, additive migrations, legacy repair and immutable evidence storage.
- `LEADS_FIRST_REAL_SOURCE_V1`: bounded SEC EDGAR acquisition and deterministic extraction with raw Evidence and fact-level provenance.
- `COMPANY_NORMALIZATION_V1`: deterministic, auditable company-name representation normalization without entity matching.

Qualification remains blocked while ICP is undefined.
