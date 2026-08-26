# Gap Detection and Automation v1

## Work unit

`GAP_DETECTION_AND_AUTOMATION_V1`, reconciled by `GAP_CAPABILITY_RECONCILIATION_V1` after WU15 multi-source company enrichment and by `DENTAL_COMMERCIAL_QUALIFICATION_V1` after the first approved qualification engine.

This planner detects **only caller-requested gaps** and produces a deterministic bounded action plan over capabilities that actually exist in the clean SearchLeads stack.

It does not execute work, run a scheduler, start background jobs, crawl the web, invent a source, infer business requirements, or turn a prerequisite acquisition into a verified fact.

## Separation of concerns

```text
explicit requirement
→ detect whether requirement is currently satisfied
→ gap if not satisfied
→ inspect explicit action inputs
→ READY action using an implemented capability
   OR
   BLOCKED with explicit reason
```

`GAP EXISTS` and `ACTION IS SAFE/AVAILABLE` are separate facts.

## Explicit requirements

`GapRequirements` can request named canonical Company fields, a validated company-owned contact, an evidence-backed Person role/title observation, or resolved qualification state. Fields/capabilities not requested by the caller are never silently added. Duplicate requested field names are deduplicated deterministically.

A requested company field is present only when a target-company `CanonicalFact` has that `field_name`; a source `CandidateFact` alone does not close the requirement. A validated Person contact does not close a company-contact requirement. A Person role requires both a Person belonging to the Company and a `professional_role_title` CandidateFact for that Person. Qualification is satisfied only by a target-company Lead whose qualification status is not `UNKNOWN`.

## Implemented company-field action mappings

### BrasilAPI point lookup

WU3 supports:

- `business_registry_id`
- `legal_name`
- `trade_name`
- `registration_status`
- `primary_cnae_code`
- `primary_cnae_description`
- `city`
- `state`

A missing requested field in that set maps to `BRASILAPI_POINT_LOOKUP` **only when an explicit known CNPJ is supplied**. It is `PREREQUISITE`: acquisition creates source Evidence/CandidateFacts; normalization/fusion/canonicalization remain separate.

### Official company-location ingestion

WU15 adds a second narrow company source: the exact official SERPRO transparency address page. It covers:

- `street_address`
- `postal_code`
- `activity_start_date`

A missing requested field in that set maps to `OFFICIAL_COMPANY_LOCATION_INGEST` **only when the caller supplies an explicit known CNPJ**. The action uses the fixed WU15 locator:

`https://www.transparencia.serpro.gov.br/acesso-a-informacao/institucional/enderecos`

The CNPJ is included as an explicit action input ID after the same 14-character `0-9A-Z` routing-key normalization used by WU3/WU15. The action is network `PREREQUISITE` work with bounded retries; WU15 still decides whether the page contains exactly one safe matching block, and canonicalization remains separate.

The planner deliberately continues to map `city` and `state` to the existing BrasilAPI point lookup rather than automatically launching both company sources. Multi-source fan-out is a separate policy decision and has not been justified by a measured acquisition-cost/benefit policy.

## Contact and Person mappings

A validated-company-contact gap can map to explicit `COMPANY_CONTACT_PAGE_INGEST` prerequisites when company contact-page URLs are supplied. When at least two persisted contact observation IDs are already supplied, it can map to local `CONTACT_PUBLICATION_VALIDATION`; WU9 itself decides whether independent corroboration is sufficient.

A missing Person-role requirement maps to `PERSON_ROLE_PAGE_INGEST` only when an explicit people/leadership URL is supplied. It remains a prerequisite observation, not a cross-snapshot identity claim.

## Qualification mapping

After WU19/WU20, a qualification gap may map to local `DENTAL_QUALIFICATION_EVALUATION` only when the caller supplies an explicit target Person ID and exactly the approved `dental-facial-surgery-education-br-v1` policy ID. The action is `DIRECT`, has one local attempt and no network interval. Missing Person ID, missing policy ID, or any other policy ID remains `BLOCKED`. Planning does not execute qualification or infer Person/company ownership.

## Deliberately blocked mappings

The planner does not claim capabilities that remain absent. Examples:

- `employee_count`
- any other unknown company predicate
- qualification evaluation without an explicit target Person ID and the exact approved dental policy ID

For WU15-supported location fields, absence of `known_cnpj` is also explicitly `BLOCKED`; the planner does not attempt to infer a CNPJ from a company name.

## Execution metadata

Every `READY` network action has:

```text
retry_max_attempts = 3
min_interval_seconds = 60
cache_key = deterministic
```

Local direct actions (contact validation and dental qualification) have one attempt, zero network interval, and deterministic cache keys. Every `BLOCKED` action has zero retries, null cache key and zero interval, preventing blind retry loops.

URL inputs are validated as absolute HTTP(S), credentials are rejected, host/scheme/default port are normalized, fragments are removed, and duplicate normalized page URLs collapse into one action where the action type accepts caller-supplied URLs.

## Reconciled curated benchmark

The reconciled benchmark contains **23 scenarios**, retaining the WU16 planning contract and adding explicit qualification-capability cases:

- `postal_code` without CNPJ → BLOCKED
- `postal_code` with CNPJ → READY official-location ingestion
- `street_address` with CNPJ → READY official-location ingestion
- `activity_start_date` with CNPJ → READY official-location ingestion
- `employee_count` remains BLOCKED
- qualification without explicit Person/policy inputs remains BLOCKED
- qualification with explicit Person + approved policy becomes READY local evaluation
- qualification with an unapproved policy remains BLOCKED

Measured contract:

```text
SCENARIOS = 23
GAP_TRUE_POSITIVE = 23
GAP_FALSE_POSITIVE = 0
GAP_FALSE_NEGATIVE = 0
GAP_PRECISION = 100.0%
GAP_RECALL = 100.0%
READY_ACTION_ROUTING_EXACT = 23/23
BLOCKED_ACTION_ROUTING_EXACT = 23/23
```

These are deterministic regression metrics for the curated contract, not production gap prevalence, source success rate, or business coverage.

## Verification

```text
RECONCILED_GAP_TESTS = 36/36 PASS
GAP_MODULE_LINE_COVERAGE = 100%
GAP_MEASURED_STATEMENTS = 227
GAP_BRANCHES = 94
GAP_AUTOMATION_BENCHMARK = PASS
PYTHON_MODULE_COMPILE = PASS
```

## Gates

```text
GAP_DETECTION = PASS
EXPLICIT_REQUIREMENTS_ONLY = YES
KNOWN_SOURCE_SELECTION = PASS
BRASILAPI_REQUIRES_KNOWN_CNPJ = YES
OFFICIAL_LOCATION_REQUIRES_KNOWN_CNPJ = YES
OFFICIAL_LOCATION_FIELDS_READY_WITH_CNPJ = PASS
EMPLOYEE_COUNT = BLOCKED_NO_SOURCE
QUALIFICATION_EXPLICIT_APPROVED_POLICY_AND_PERSON = READY
QUALIFICATION_MISSING_OR_WRONG_POLICY_INPUT = BLOCKED
NETWORK_RETRY_FINITE = YES
NETWORK_MIN_INTERVAL_REPRESENTED = YES
DETERMINISTIC_CACHE_KEY = YES
BLOCKED_ACTION_RETRY = 0
BACKGROUND_EXECUTION = NO
GENERIC_SCHEDULER = NO
GENERIC_CRAWLER = NO
UNIVERSAL_ENRICHMENT_FRAMEWORK = NO
APPROVED_VERTICAL_ICP = dental-facial-surgery-education-br-v1
GENERIC_CORE_B2B_ASSUMPTION = PROVISIONAL
```
