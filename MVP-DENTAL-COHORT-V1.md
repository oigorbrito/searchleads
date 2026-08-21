# MVP Dental Cohort V1 — Real Professional Smoke

**Date:** 2026-08-21  
**Campaign track evaluated:** `CEOF_SPECIALIZATION`  
**Purpose:** validate that the MVP can find and classify real professionals before building broader automated discovery.

This is a deliberately small smoke cohort, not a production benchmark and not an accuracy/coverage claim.

## Important regulatory split

Current CFO rules introduced `Cirurgia Estética Orofacial (CEOF)` as a specialty in 2026. The MVP therefore separates two commercial tracks:

- `CEOF_SPECIALIZATION`: formation/specialization campaign. General dentists and dentists with existing specialties remain candidates, subject to institution/CRO admission verification.
- `COMPLEMENTARY_EXCLUSIVE_CEOF`: complementary courses such as immersion/mentoring for procedures exclusive to CEOF. The MVP requires evidence of CEOF-specialist status before qualifying this campaign.

Regulatory references:

- https://website.cfo.org.br/cirurgia-estetica-orofacial-e-oficialmente-regulamentada/
- https://busca-profissionais.cfo.org.br/

The CFO professional-search page was updated on 2026-08-21 and supports CRO/UF, category, registration number, specialty, habilitation and name searches. Direct CFO verification of each cohort member is still a pre-outreach gate rather than being silently inferred from third-party pages.

## Cohort

| Region | Professional | Public credential evidence | Facial fit evidence | Public professional contact | FIT | INTENT | Specialization priority | CFO direct verification | Buyer caveat | Primary evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| North | Dra. Gabriella Hübner | CRO-AM 4055; dentist; HOF specialist | HOF / facial aesthetics | booking/contact channel on professional profile | HIGH | UNKNOWN | P2 | PENDING | advanced HOF practitioner | https://www.doctoralia.com.br/gabriella-hubner/dentista/manaus |
| North | Dra. Glaucia Medeiros Montenegro de Cantai | CRO-AM 8474; general dentist | no facial-specific evidence in source | clinic phone | MEDIUM | UNKNOWN | P3 | PENDING | generalist control case | https://www.clinicaebenezer.com/equipe |
| Northeast | Dra. Rafaella Guimarães | CRO-PE 14123; dentist; HOF specialist | HOF | booking/contact via clinic/profile | HIGH | MEDIUM | P2 | PENDING | currently in further specialization; good continuing-education signal but not facial-course intent | https://www.doctoralia.com.br/rafaella-guimaraes/especialista-em-harmonizacao-orofacial-dentista-ortodontista/recife |
| Northeast | Prof. Dr. José Romar | CRO-PE 8620; Bucomaxilofacial specialist | facial/maxillofacial surgery | clinic contact channel | HIGH | UNKNOWN | P2 | PENDING | professor/advanced specialist may be peer/instructor rather than buyer | https://clinicarealface.com.br/ |
| Central-West | Dra. Gabriella Lisboa | CRO-GO 11836; dentist; HOF specialist | HOF / facial aesthetics | site, email, phone/WhatsApp | HIGH | UNKNOWN | P2 | PENDING | very experienced practitioner | https://www.studiodental.dental/ |
| Central-West | Dra. Milena Campos | CRO-GO 13686; dentist; HOF specialist | HOF / facial aesthetics | professional site appointment channel | HIGH | MEDIUM | P2 | PENDING | mentor/speaker; buyer likelihood uncertain despite strong continuing-education evidence | https://www.dramilenacampos.com.br/ |
| Southeast | Dra. Aline Maia | CRO-MG 42023; dentist; advanced facial harmonization | 7+ years focused on facial harmonization | booking/message/WhatsApp channels | HIGH | MEDIUM | P2 | PENDING | advanced practitioner; education history supports continuing-learning signal only | https://www.doctoralia.com.br/aline-maia-4/dentista-especialista-em-harmonizacao-orofacial/belo-horizonte |
| Southeast | Dra. Natalia Messina | CRO-MG 071836; HOF specialist | HOF / facial aesthetics | professional site appointment channel | HIGH | UNKNOWN | P2 | PENDING | no explicit learning-intent evidence found | https://nataliamessina.com.br/ |
| South | Dra. Gabriela Dalaroza | CRO-PR 39995; dentist; HOF activity | HOF / facial aesthetics; also oral surgery listing in directory | site/WhatsApp/agenda | HIGH | UNKNOWN | P2 | PENDING | no explicit learning-intent evidence found | https://gabrieladalaroza.com.br/ |
| South | Dr. Leonardo Marchesini Javorsky | CRO-PR 32047; dentist; HOF specialist | HOF / facial aesthetics | consultation request channel | HIGH | UNKNOWN | P2 | PENDING | specialization completed in 2023 is historical education evidence, not current intent | https://www.ident.com.br/dr.leonardojavorsky |

## MVP metrics

```text
COHORT_SIZE = 10
MACRO_REGIONS_COVERED = 5 / 5
PUBLIC_PROFESSION_OR_TITLE_EVIDENCE = 10 / 10
PUBLIC_CRO_NUMBER_EVIDENCE = 10 / 10
PUBLIC_PROFESSIONAL_CONTACT_CHANNEL = 10 / 10

FIT_HIGH = 9
FIT_MEDIUM = 1
FIT_LOW = 0
FIT_UNKNOWN = 0

INTENT_HIGH = 0
INTENT_MEDIUM = 3
INTENT_UNKNOWN = 7
INTENT_LOW = 0

SPECIALIZATION_TRACK_P1 = 0
SPECIALIZATION_TRACK_P2 = 9
SPECIALIZATION_TRACK_P3 = 1
REVIEW = 0
EXCLUDE = 0

DIRECT_CFO_VERIFICATION_COMPLETE = 0 / 10
```

## What this tells us

1. The target profile is discoverable on the public web with explicit professional and location evidence.
2. HOF/Bucomax/facial relevance is much easier to observe than explicit purchase or training intent.
3. `INTENT = UNKNOWN` must remain eligible for outreach; requiring explicit intent would discard most plausible buyers.
4. A general dentist can be represented separately from an HOF/Bucomax specialist, so title filtering is useful without being mandatory.
5. Public professional contact channels are common enough in this smoke cohort to support an outreach MVP.
6. Several strong-fit profiles are also educators, mentors or highly experienced clinicians. The future discovery recipe should therefore add an `educator/instructor` signal so those profiles can be deprioritized rather than falsely treated as ideal buyers.
7. Before actual outreach, CRO status/specialty should be checked against the current CFO search. The MVP does not substitute website claims for official professional-registration verification.

## MVP decision

Do **not** block launch on intent discovery.

Recommended first campaign funnel:

```text
verified dentist
→ Brazil / selected geography
→ eligible title selection
→ facial/HOF/Bucomax relevance
→ public professional contact
→ CEOF specialization offer-track gate
→ FIT priority
→ optional INTENT boost
→ outreach candidate
```

For complementary immersion/mentoring in CEOF-exclusive procedures, use the separate `COMPLEMENTARY_EXCLUSIVE_CEOF` gate and require CEOF specialist evidence first.

## Next engineering step

Build one repeatable dental-professional discovery recipe around an authoritative or high-precision source, then run it on a bounded sample. CFO Search/Geolocation is the preferred verification source; discovery automation should not expand nationwide until we can measure duplicate rate, title verification and usable-contact yield on the bounded sample.
