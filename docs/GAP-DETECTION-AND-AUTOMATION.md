# Gap Detection and Automation v1

## Work unit

`GAP_DETECTION_AND_AUTOMATION_V1`

This unit detects **only caller-requested gaps** and produces a deterministic bounded action plan over capabilities that already exist in the clean SearchLeads stack.

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

`GapRequirements` can request:

- named canonical Company fields;
- at least one validated **company-owned** contact;
- at least one evidence-backed Person role/title observation;
- resolved qualification state.

Fields/capabilities not requested by the caller are never silently added to the plan.

Duplicate requested field names are deduplicated deterministically.

## Gap semantics

### Company field

A requested company field is present only when a `CanonicalFact` for the target Company has that `field_name`.

A source `CandidateFact` alone does not close a canonical-field requirement.

### Validated company contact

The requirement is satisfied only by `ContactPoint(status=VALIDATED)` whose `owner_id` is the Company itself.

A validated Person contact does not silently satisfy a company-contact requirement.

### Person role

The requirement is satisfied only when:

- an exported/observed `Person` belongs to the Company; and
- a `CandidateFact(field_name=professional_role_title)` exists for that Person.

A Person name without a role fact, or a role fact for an unrelated Person, does not close the gap.

### Qualification

The requirement is satisfied only when a `Lead` for the Company exists with qualification status different from `UNKNOWN`.

The clean stack still has no qualification engine/ICP policy, so an unresolved qualification gap is detected but cannot be automatically planned into a qualification evaluation.

## Implemented action mappings

### BrasilAPI point lookup

Current WU3 supports these company predicates:

- `business_registry_id`;
- `legal_name`;
- `trade_name`;
- `registration_status`;
- `primary_cnae_code`;
- `primary_cnae_description`;
- `city`;
- `state`.

A missing requested field in that set can map to `BRASILAPI_POINT_LOOKUP` **only when the caller supplies an explicit known CNPJ**.

The input uses the current WU3 14-character `0-9A-Z` routing contract.

This action is `PREREQUISITE`, not direct gap closure: WU3 produces Evidence/CandidateFacts; normalization/fusion/canonicalization remain separate.

### Company contact page ingestion

A validated-company-contact gap can map to one or more `COMPANY_CONTACT_PAGE_INGEST` actions only when explicit company contact-page URLs are supplied.

Each page ingest is a `PREREQUISITE`: WU7 can produce discovery Evidence/ContactPoints, but WU9 still requires independent publication corroboration before `VALIDATED`.

### Contact publication validation

When the caller already supplies at least two persisted contact observation IDs, the planner can emit `CONTACT_PUBLICATION_VALIDATION` using the existing WU9 method.

This is a local `DIRECT` action candidate: WU9 itself decides whether the evidence actually satisfies its validation rules.

### Person/role page ingestion

A missing Person-role requirement maps to `PERSON_ROLE_PAGE_INGEST` only when the caller supplies an explicit people/leadership page URL.

It is `PREREQUISITE`: WU8 may create evidence-backed Person/role observations; it does not prove cross-snapshot Person identity or current employment indefinitely.

## Deliberately blocked mappings

The planner does **not** claim capabilities that are absent from the clean stack.

Examples currently blocked:

- `employee_count`;
- `postal_code`;
- `street_address`;
- `activity_start_date`;
- any other unknown company predicate;
- qualification evaluation while no clean qualification engine/ICP exists.

This differs deliberately from the legacy stack, which had an official-location enrichment source and qualification engine that have not been introduced into the clean stack.

## Execution metadata

Every `READY` action is finite and content-addressed.

Network actions:

```text
retry_max_attempts = 3
min_interval_seconds = 60
cache_key = deterministic
```

Local contact-validation action:

```text
retry_max_attempts = 1
min_interval_seconds = 0
cache_key = deterministic
```

Every `BLOCKED` action has:

```text
retry_max_attempts = 0
cache_key = null
min_interval_seconds = 0
```

Blocked work therefore cannot accidentally become a blind retry loop.

URL inputs are validated as absolute HTTP(S), credentials are rejected, host/scheme/default port are normalized, fragments are removed, and duplicate normalized page URLs collapse into one planned action.

## Curated benchmark

The deterministic benchmark contains 18 scenarios covering:

- already-present canonical fields;
- supported BrasilAPI fields with/without explicit CNPJ;
- alphanumeric CNPJ routing;
- unsupported fields;
- validated company contact present/missing;
- explicit validation-observation IDs;
- explicit contact page URLs;
- Person role present/missing;
- explicit people page URL;
- qualified/unknown/missing Lead;
- mixed requirements;
- duplicate requirements.

Measured contract:

```text
SCENARIOS = 18
GAP_TRUE_POSITIVE = 18
GAP_FALSE_POSITIVE = 0
GAP_FALSE_NEGATIVE = 0
GAP_PRECISION = 100.0%
GAP_RECALL = 100.0%
READY_ACTION_ROUTING_EXACT = 18/18
BLOCKED_ACTION_ROUTING_EXACT = 18/18
```

These are deterministic regression metrics for the curated contract, not production gap prevalence, source success rate, or business coverage.

## Verification

```text
WU13_FOCUSED_TESTS = 37/37 PASS
WU13_MODULE_LINE_COVERAGE = 100%
WU13_MEASURED_STATEMENTS = 207
WU13_BRANCHES = 82
GAP_AUTOMATION_BENCHMARK = PASS
PYTHON_MODULE_COMPILE = PASS
```

## Gates

```text
GAP_DETECTION = PASS
EXPLICIT_REQUIREMENTS_ONLY = YES
CANONICAL_FIELD_REQUIREMENT = YES
KNOWN_SOURCE_SELECTION = PASS
MISSING_ACTION_INPUTS = BLOCKED
UNKNOWN_SOURCE_NOT_INVENTED = PASS
BRASILAPI_REQUIRES_KNOWN_CNPJ = YES
CURRENT_ALPHANUMERIC_CNPJ_ROUTING = PASS
CONTACT_DISCOVERY_REQUIRES_EXPLICIT_URL = YES
PERSON_DISCOVERY_REQUIRES_EXPLICIT_URL = YES
QUALIFICATION_WITHOUT_ENGINE_ICP = BLOCKED
NETWORK_RETRY_FINITE = YES
NETWORK_MIN_INTERVAL_REPRESENTED = YES
DETERMINISTIC_CACHE_KEY = YES
BLOCKED_ACTION_RETRY = 0
BACKGROUND_EXECUTION = NO
GENERIC_SCHEDULER = NO
GENERIC_CRAWLER = NO
UNIVERSAL_ENRICHMENT_FRAMEWORK = NO
FOCUSED_TESTS = 37/37 PASS
LINE_COVERAGE_NEW_MODULE = 100%
ICP_DEFINED = NO
B2B_ASSUMPTION = PROVISIONAL
```

## Next work unit

Per the original handoff: `END_TO_END_ACCEPTANCE_V1`.
