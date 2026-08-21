# Work Unit 14 Report — GAP_DETECTION_AND_AUTOMATION_V1

## Scope

Adds bounded gap detection and planning over capabilities already implemented in SearchLeads. It does not create a generic scheduler, crawler, or universal enrichment framework.

Requirements are explicit caller inputs. The planner never silently decides that a business field is required.

## Known action mapping

Missing canonical registry fields already covered by the structured CNPJ adapter map to `BRASILAPI_LOOKUP`.

Missing `street_address`, `postal_code`, or `activity_start_date` map to the known official-location enrichment capability.

Missing validated company contact maps to the known official contact discovery/corroboration capability.

Missing person/company role maps to the known official people-page capability.

Missing qualification maps to qualification evaluation only when an explicit policy ID exists.

An unknown requested field such as `employee_count` is `BLOCKED`; no new source is invented.

## Operational representation

Ready network actions carry:

- finite `retry_max_attempts = 3`;
- deterministic cache key;
- minimum interval metadata (`60` seconds in V1).

Blocked actions carry no network action and do not retry blindly.

These are planning/configuration semantics. This work unit does not launch background execution.

## Validation

`python -m unittest discover -s tests -v`

- `TESTS_DISCOVERED = 156`
- `TESTS_EXECUTED = 156`
- `TESTS_PASSED = 156`

## Gates

- `GAP_DETECTION = PASS`
- `EXPLICIT_REQUIREMENTS = PASS`
- `KNOWN_SOURCE_SELECTION = PASS`
- `UNKNOWN_SOURCE_NOT_INVENTED = PASS`
- `BOUNDED_RETRY = PASS`
- `CACHE_KEY_REPRESENTABLE = YES`
- `RATE_LIMIT_INTERVAL_REPRESENTABLE = YES`
- `QUALIFICATION_WITHOUT_ICP = BLOCKED`
- `GENERIC_SCHEDULER = NO`
- `UNIVERSAL_FRAMEWORK = NO`

## Classification

Gap/action schemas, retry count and interval are `ENGINEERING_CHOICE`. Blocking qualification without a policy follows the supplied handoff's `QUALIFICATION CRITERIA = NOT YET DEFINED` constraint. Source mappings use only locally implemented known capabilities.
