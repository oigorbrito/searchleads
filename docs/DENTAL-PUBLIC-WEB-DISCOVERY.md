# Dental Public Web Discovery V1

## Work unit

`DENTAL_PUBLIC_WEB_DISCOVERY_V1`

This unit resolves #78 by porting the deterministic Dental public-web recipe that legacy PR #36 used before the external-provider layer. It consumes the approved clean policy `dental-facial-surgery-education-br-v1` and remains transport-neutral.

## Pipeline

```text
approved Dental policy + explicit filters
→ deterministic bounded query plan
→ already-captured public search observations (Evidence IDs required)
→ conservative Dental candidates
→ exact CRO / exact normalized URL deduplication
→ CFO verification remains PENDING
```

It is not a crawler and performs no network request.

## Query policy

Default scope is Brazil-wide. Optional state and professional-group filters are explicit caller inputs. State filters accept only Brazilian UF codes. Professional groups are limited to the groups already present in the approved policy:

- `GENERAL_DENTIST`
- `DENTAL_SPECIALIST`
- `BUCOMAXILLOFACIAL`
- `HOF_OR_FACIAL_ACTIVITY`

Query ordering follows the approved policy group order and normalized state order. `max_queries` is mandatory-bounded and must be at least 1.

## Candidate boundary

A public observation may create a candidate only when it contains at least one explicit Dental/CRO/facial relevance signal. Public text is discovery evidence only.

Supported CRO textual shapes retain the legacy conservative parser and require a valid Brazilian UF. Unknown/invalid UF text is not promoted to a CRO key.

Professional-group classification retains the previously tested Dental text groups. Facial terms include the approved core topics plus related discovery phrases used by the legacy recipe.

Every candidate is constructed with:

```text
cfo_verification_status = PENDING
```

The dataclass rejects attempts to promote that field inside this discovery layer.

## Identity / deduplication

Discovery identity is deliberately narrow:

```text
exact CRO state + number
OR
exact normalized HTTP(S) URL
```

Name similarity is never a dedupe key. Same-name observations at different URLs/CROs remain separate candidates. Exact duplicates union sorted Evidence IDs and facial signals.

URL normalization lowercases scheme/host, removes default ports, query strings and fragments, and rejects credentials/non-HTTP(S) URLs.

## Intent and authority boundaries

The recipe does not infer learning intent. It does not verify CFO/CRO registration, specialty, current activity, contact deliverability, campaign compliance, or SEND_READY.

## Verification

```text
FOCUSED_TESTS = 24/24 PASS
LINE_COVERAGE = 100%
BRANCH_COVERAGE = 100%
STATEMENTS = 179
BRANCHES = 70
```

Adversarial coverage includes all four CRO text forms, invalid states, URL safety, all approved professional groups, facial-only candidates, irrelevant observations, exact-CRO and exact-URL dedupe, same-name non-dedupe, evidence union, forged CFO-state rejection, deterministic query ordering and bounded filters.

## Gates

```text
APPROVED_POLICY_ONLY = YES
DEFAULT_SCOPE = BRAZIL_WIDE
EXPLICIT_STATE_FILTERS = YES
EXPLICIT_GROUP_FILTERS = YES
BOUNDED_QUERY_PLAN = PASS
NETWORK_REQUESTS = NO
GENERIC_CRAWLER = NO
NAME_AS_IDENTITY = NO
EXACT_CRO_DEDUPE = PASS
EXACT_URL_DEDUPE = PASS
PUBLIC_CRO_IS_OFFICIAL = NO
CFO_VERIFICATION_STATUS = PENDING_ONLY
LEARNING_INTENT_INFERENCE = NO
```

## Basis

- approved clean WU19/WU20 policy contract
- legacy PR #36 `dental_repeatable_discovery.py`
- issue #78
