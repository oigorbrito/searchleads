# Contact Validation v1

## Work unit

`CONTACT_VALIDATION_V1`

This unit promotes a previously `DISCOVERED` contact into a **new immutable `VALIDATED` snapshot** only when its published owner/contact association is corroborated by independent persisted page observations.

`VALIDATED` in this work unit has a deliberately narrow meaning:

> SearchLeads has at least two qualifying page observations supporting the same owner + contact kind + equivalent value.

It does **not** mean the mailbox accepts delivery, a telephone call succeeds, a WhatsApp account responds, a social account is controlled by the person/company today, or the contact is fresh indefinitely.

## Pipeline

```text
persisted DISCOVERED ContactPoint
+ optional corroborating DISCOVERED ContactPoints
→ require same owner
→ require same ContactKind
→ compare kind-specific structural equivalence
→ require qualifying page Evidence for each observation
→ require two independent Evidence observations
→ insufficient evidence OR new VALIDATED ContactPoint snapshot
```

## Equivalence rules

- `EMAIL`: conservative structural validation + case-insensitive comparison;
- `PHONE` / `WHATSAPP`: punctuation is ignored; digits must match exactly (no country code is invented);
- URL-like channels (`CONTACT_FORM`, `LINKEDIN`, `INSTAGRAM`, `PROFESSIONAL_PROFILE`): HTTP(S) scheme/host are normalized, default ports and fragments are removed, and non-root trailing slash is ignored;
- `OTHER`: not auto-validatable in V1.

Kind must match exactly. A phone does not corroborate WhatsApp merely because the digits happen to match.

## Qualifying page Evidence

A discovery observation contributes to validation only when every referenced Evidence record:

- exists;
- has an existing `Source`;
- comes from `company-web-page` or `company-people-page`;
- represents HTTP status `200`;
- preserves a textual raw page payload.

This keeps V1 validation aligned with WU7/WU8's explicit page-observation boundaries. Future directories/registries may introduce separate validation methods rather than inheriting authority silently.

## Independence rule

Two observations are independent enough for this V1 method when their qualifying Evidence has either:

1. different page locators; or
2. the same locator at different capture times.

The following do **not** add support:

- duplicate contact IDs in the request;
- two contacts referencing the same Evidence ID;
- two same-page Evidence objects with the same capture time;
- corroborating observations for another owner;
- same owner but different kind/value;
- non-page source records;
- failed/non-text page Evidence.

## Immutable validated snapshot

On success, a deterministic new `ContactPoint` is produced:

```text
status = VALIDATED
discovery_evidence_ids = original discovery evidence
validation_evidence_ids = all qualifying corroborating page evidence
validated_at = max(validation Evidence captured_at)
```

The original `DISCOVERED` contact is never overwritten. The validated ID is content-addressed from validation method + owner + kind + equivalence key + validation Evidence IDs, so rerunning the same validation is idempotent.

## No negative overclaim

If evidence is insufficient, WU9 returns `INSUFFICIENT_EVIDENCE` and does not create an assessed contact snapshot.

If the kind/value is structurally outside the V1 method, WU9 returns `NOT_VALIDATABLE`.

WU9 deliberately does not create `STALE` or `INVALID` contacts from absence, HTTP failure, or syntax alone. Those statuses require stronger validation semantics/evidence.

## Curated validation benchmark

A deterministic 12-scenario fixture covers:

- distinct-page e-mail corroboration;
- e-mail case equivalence;
- phone/WhatsApp punctuation equivalence;
- profile URL representation equivalence;
- later snapshot of the same page;
- one observation only;
- same page at the same timestamp;
- different owner;
- different value;
- different kind;
- non-page source evidence.

Measured local contract:

```text
SCENARIOS = 12
TRUE_VALIDATIONS = 6
TRUE_POSITIVE = 6
FALSE_POSITIVE = 0
TRUE_NEGATIVE = 6
FALSE_NEGATIVE = 0
AUTO_VALIDATION_PRECISION = 100.0%
AUTO_VALIDATION_RECALL = 100.0%
FALSE_VALIDATION_RATE = 0.0%
```

These are curated deterministic regression metrics, not production prevalence or accuracy estimates.

## Current SERPRO publication calibration — checked 2026-08-25

Current official SERPRO pages independently publish the Central de Serviços contact values `css.serpro@serpro.gov.br` and `0800 728 2323`. At least these distinct current pages expose both channels:

- `https://www.serpro.gov.br/menu/suporte/ajuda-ao-cliente`
- `https://www.serpro.gov.br/menu/contato/cliente/perguntas-frequentes/suporte/suporte-perguntas-frequentes`
- `https://www.serpro.gov.br/menu/suporte/css`

This demonstrates that the WU9 two-page corroboration criterion can be satisfied by current public observations for a real company contact. The local benchmark does not claim to be a byte-for-byte live capture of those pages.

## Verification

```text
WU9_FOCUSED_TESTS = 34/34 PASS
WU9_MODULE_LINE_COVERAGE = 100%
WU9_MEASURED_STATEMENTS = 148
VALIDATION_BENCHMARK = PASS
PYTHON_MODULE_COMPILE = PASS
```

The clean base PR #49 remains separately validated at its published snapshot. The current runtime did not reconstruct the complete historical stack or rerun all prior units; instead, the current SQLite contact-reference contract was audited directly and requires existing owner plus both discovery and validation Evidence references, matching the WU9 output shape.

## Gate

```text
ORIGINAL_CONTACT_MUST_BE_DISCOVERED = YES
SAME_OWNER_REQUIRED = YES
SAME_KIND_REQUIRED = YES
VALUE_EQUIVALENCE_REQUIRED = YES
INDEPENDENT_PAGE_OBSERVATIONS_REQUIRED = 2
DUPLICATE_SUPPORT_INFLATION = BLOCKED
VALIDATED_CONTACT_IS_NEW_SNAPSHOT = YES
DISCOVERY_EVIDENCE_PRESERVED = YES
VALIDATION_EVIDENCE_PRESERVED = YES
VALIDATED_AT_FROM_EVIDENCE = YES
DELIVERABILITY_VERIFIED = NO
REACHABILITY_VERIFIED = NO
ABSENCE_IMPLIES_STALE = NO
SYNTAX_ALONE_IMPLIES_INVALID = NO
CURATED_AUTO_VALIDATION_PRECISION = 100.0%
CURATED_FALSE_VALIDATION_RATE = 0.0%
FOCUSED_TESTS = 34/34 PASS
LINE_COVERAGE_NEW_MODULE = 100%
ICP_DEFINED = NO
B2B_ASSUMPTION = PROVISIONAL
```

## Next work unit

Per the supplied roadmap: `REPEATABLE_WEB_DISCOVERY_V1`.
