# ICP V1 — Educação em Cirurgia Facial para Dentistas

## Status

```text
ICP_DEFINED = YES
DECISION_BASIS = BUSINESS_REQUIREMENT
PRIMARY_COMMERCIAL_ENTITY = PERSON
COUNTRY = BR
```

This vertical ICP records the business requirements supplied on 2026-08-21. It is deliberately separate from generic SearchLeads architecture.

## Target

Eligible professionals:

- general dentists;
- dentists with specialty/title;
- oral and maxillofacial surgeons (`Bucomaxilofacial`);
- professionals with evidence-backed activity in HOF / facial aesthetics / facial surgery.

General dentists are explicitly eligible. A specialty/title filter may be enabled at runtime when a narrower campaign is desired.

## Offer fit

Core educational topics:

- Blepharoplasty (`Blefaroplastia`);
- Lip Lift;
- Facial lifting (`Lifting facial`);
- Forehead surgery (`Frontoplastia`);
- closely related facial surgical/aesthetic procedures when evidence explicitly supports the relationship.

Offer format is a combination of:

- in-person;
- immersion;
- mentoring;
- longer training/formations;
- online/hybrid.

## Geography

Default scope is Brazil-wide.

Runtime campaign filters may select:

- Brazil-wide;
- macro-region: North, Northeast, Central-West, Southeast or South;
- one or more states;
- title/specialty groups or explicit title terms.

Missing geography under an active geographic filter produces `UNKNOWN/REVIEW`, not an automatic exclusion. Known out-of-scope geography produces `NOT_QUALIFIED/EXCLUDE`.

## FIT and INTENT are separate

FIT answers whether the professional matches the target profile.

```text
HIGH
MEDIUM
LOW
UNKNOWN
```

Examples:

- Bucomax or HOF with evidence-backed title -> HIGH FIT;
- general dentist with evidence of facial procedures/aesthetics -> HIGH FIT;
- general dentist without observed facial relevance yet -> MEDIUM FIT;
- missing professional evidence -> UNKNOWN;
- explicit campaign filter mismatch -> LOW.

INTENT answers whether there is evidence of learning/training interest.

```text
HIGH
MEDIUM
LOW
UNKNOWN
```

High-intent evidence may include explicit course/procedure-learning interest. Continuing-education or training participation may support MEDIUM intent.

**Absence of an intent signal is always `UNKNOWN`, never `LOW`.** SearchLeads does not infer that someone wants a course merely because they are a dentist or perform facial procedures.

## Priority

```text
P1 = HIGH FIT + HIGH INTENT
P2 = HIGH FIT + MEDIUM/UNKNOWN INTENT, or MEDIUM FIT + HIGH INTENT
P3 = eligible lower-priority combinations
REVIEW = insufficient evidence under an active filter
EXCLUDE = explicit filter mismatch / LOW FIT
```

## Contactability

Professional contact is useful for outreach but is not required by the default ICP. A campaign may set `require_validated_contact = true` when only immediately contactable leads are desired.

Existing SearchLeads contact semantics remain unchanged: `VALIDATED` means evidence-backed publication/corroboration, not guaranteed deliverability/reachability.

## Entity model

The commercial target is the professional (`Person`). Company/clinic remains context and a source of evidence.

The current core `Lead` schema is company-linked, so the MVP bridge materializes a Lead with:

```text
company_id = clinic/company context
metadata.primary_commercial_entity = PERSON
metadata.person_id = target professional
metadata.fit
metadata.intent
metadata.priority
```

This avoids pretending that clinic qualification and person qualification are the same thing while preserving compatibility with the current export pipeline.

## MVP testing policy

To accelerate the MVP, this vertical does not aim for exhaustive edge-case coverage. Focused tests protect only high-cost mistakes:

- general dentist eligibility;
- facial relevance increasing FIT;
- Bucomax + explicit learning intent reaching top priority;
- geography filters;
- title filters;
- evidence bridge not inventing intent;
- Person-centered qualification surviving Lead materialization.

Broader edge-case and production accuracy testing is deferred until a real dental cohort exists.
