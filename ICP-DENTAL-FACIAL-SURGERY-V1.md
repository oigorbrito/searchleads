# ICP V1 — Educação em Cirurgia Facial para Dentistas

## Status

```text
ICP_DEFINED = YES
DECISION_BASIS = BUSINESS_REQUIREMENT
PRIMARY_COMMERCIAL_ENTITY = PERSON
COUNTRY = BR
DEFAULT_OFFER_TRACK = CEOF_SPECIALIZATION
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

## 2026 CEOF regulatory campaign split

The Conselho Federal de Odontologia regulated `Cirurgia Estética Orofacial (CEOF)` as a specialty through CFO-SEC-286/2026. The MVP therefore does not treat every educational format as the same campaign.

### `CEOF_SPECIALIZATION`

This is the safe default MVP campaign. General dentists and dentists with other specialties remain prospect candidates for the formal specialization/formation path, subject to the educational institution's admission rules and current CRO/CFO verification.

### `COMPLEMENTARY_EXCLUSIVE_CEOF`

Complementary theoretical-practical courses outside the specialization path — including formats such as aperfeiçoamento, atualização, extensão, fellowship, imersão or mentoria — that teach procedures exclusive to CEOF require CEOF-specialist eligibility under the current CFO rule. For this campaign SearchLeads therefore requires explicit CEOF-specialist evidence. Missing CEOF evidence becomes `UNKNOWN/REVIEW`; known non-CEOF title evidence becomes `NOT_QUALIFIED/EXCLUDE` for that offer track only.

This gate is a campaign-safety representation, not legal advice, and should be rechecked if CFO rules change.

Current references:

- https://website.cfo.org.br/cirurgia-estetica-orofacial-e-oficialmente-regulamentada/
- https://busca-profissionais.cfo.org.br/

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
REVIEW = insufficient evidence under an active filter or regulatory gate
EXCLUDE = explicit filter/regulatory mismatch / LOW FIT
```

For the MVP, explicit INTENT is a priority boost rather than a hard eligibility requirement.

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
metadata.offer_track
metadata.regulatory_eligibility
```

This avoids pretending that clinic qualification and person qualification are the same thing while preserving compatibility with the current export pipeline.

## Real MVP cohort signal

A first bounded smoke cohort contains 10 real public professional profiles, two per Brazilian macro-region.

```text
COHORT_SIZE = 10
MACRO_REGIONS = 5 / 5
PUBLIC_PROFESSION_OR_TITLE_EVIDENCE = 10 / 10
PUBLIC_CRO_NUMBER_EVIDENCE = 10 / 10
PUBLIC_PROFESSIONAL_CONTACT_CHANNEL = 10 / 10
FIT_HIGH = 9
FIT_MEDIUM = 1
INTENT_MEDIUM = 3
INTENT_UNKNOWN = 7
P1 = 0
P2 = 9
P3 = 1
DIRECT_CFO_VERIFICATION_COMPLETE = 0 / 10
```

The important product finding is that public FIT evidence is common while explicit learning intent is uncommon. Therefore the first outreach MVP should allow `HIGH FIT + UNKNOWN INTENT` and use intent only to rank stronger opportunities.

See `MVP-DENTAL-COHORT-V1.md` for the cohort and evidence links.

## MVP testing policy

To accelerate the MVP, this vertical does not aim for exhaustive edge-case coverage. The focused suite contains only eight tests protecting high-cost errors:

- Brazil-wide/core ICP definition;
- general dentist eligibility without invented intent;
- facial relevance increasing FIT;
- Bucomax + explicit learning intent reaching top priority;
- geography filtering and missing-geography review;
- title filtering;
- evidence bridge not inventing intent;
- offer-track regulatory gating plus Person-centered Lead materialization.

Current focused CI result:

```text
8 / 8 PASS
```

Broader edge-case and production accuracy testing is deferred until repeatable real dental discovery is running.
