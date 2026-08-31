# Dental Commercial Qualification V1

## Work unit

`DENTAL_COMMERCIAL_QUALIFICATION_V1`

This work unit implements issue #62 by consuming exactly the approved `APPROVED_DENTAL_ICP_POLICY_V1` contract introduced by WU19. It does not decide a new ICP and does not accept substitute policy objects that merely reuse the same policy ID.

## Boundary

The approved commercial target is a `Person`. The existing core `Lead` remains company-linked, so V1 keeps two layers explicit:

1. `DentalQualificationDecision`: Person-centered, policy-versioned, evidence-linked qualification result.
2. `Lead`: deterministic commercial wrapper linked to the Person's Company and carrying status/stage plus audit reasons identifying Person, policy, offer track, FIT, INTENT and priority.

The decision object, not the Lead wrapper, carries the complete policy-relevant fact/conflict/contact/Evidence references.

## Inputs

The engine consumes existing clean-stack records only:

- `Person` and its company relationship Evidence;
- `CandidateFact` and `CanonicalFact` for professional title/specialty, practice/procedure relevance, geography and education intent;
- open `Conflict` records for policy-relevant fields;
- existing `ContactPoint` records when an explicit campaign requires a validated contact;
- the exact approved WU19 policy contract.

No raw-page reparsing, crawling, inferred specialty, inferred intent or company-size threshold is introduced.

Canonical facts take precedence over candidate observations for the same subject/field. Evidence supporting a canonical fact is traced through its parent candidate fact IDs. Open policy-relevant conflicts stay explicit.

## Policy routing

### Profession and FIT

- explicit CEOF, Bucomaxilofacial or HOF/facial title, or evidence-backed facial relevance -> `HIGH` FIT;
- eligible general/dental specialty without observed facial relevance -> `MEDIUM` FIT;
- missing professional-title evidence -> `UNKNOWN`;
- explicit non-dental professional title -> `NOT_QUALIFIED` / `LOW`.

### Geography

The approved contract is Brazil-scoped. Explicit Brazil country evidence or a recognized Brazilian state supports scope. Missing geography -> `UNKNOWN`. Explicit non-Brazil geography without a Brazilian state -> `NOT_QUALIFIED`. Contradictory country evidence -> `UNKNOWN`.

### INTENT

INTENT remains independent from FIT:

- `COURSE_INTEREST` / `PROCEDURE_LEARNING` -> `HIGH`;
- continuing education/training signals -> `MEDIUM`;
- `EXPLICIT_NO_INTEREST` -> `LOW`;
- absent intent -> `UNKNOWN`;
- contradictory/open intent evidence -> `UNKNOWN`.

Missing intent never becomes a negative qualification by itself.

### Conflicts

An open conflict in a required profession/geography field prevents forced qualification and routes to `UNKNOWN/REVIEW`. An intent-only conflict changes INTENT to `UNKNOWN` without erasing otherwise-supported FIT.

### Contactability

The approved default ICP does not require contact. When a caller explicitly activates `require_validated_contact`, only an existing `VALIDATED` contact owned by the target Person or company context satisfies it. A merely `DISCOVERED` contact does not.

### Offer tracks

`CEOF_SPECIALIZATION` is the documented default track. `COMPLEMENTARY_EXCLUSIVE_CEOF` requires explicit CEOF-specialist title evidence. Missing required evidence remains `UNKNOWN`; known non-CEOF dental title evidence is `NOT_QUALIFIED` for that complementary-exclusive track only.

## Deterministic Lead materialization

`materialize_lead()` creates a deterministic ID from Person + Company + policy + offer track unless an explicit ID is supplied.

- `QUALIFIED` -> `LeadStage.QUALIFIED`
- `NOT_QUALIFIED` -> `LeadStage.DISQUALIFIED`
- `UNKNOWN` -> `LeadStage.REVIEW`

`Company != Lead` remains unchanged. The same Company may have distinct Person-centered commercial decisions/leads.

## Gap planner reconciliation

A qualification gap can now route to local `DENTAL_QUALIFICATION_EVALUATION` only when the caller supplies both:

- an explicit target Person ID; and
- exactly `dental-facial-surgery-education-br-v1` as the approved policy ID.

The action is `DIRECT`, local, one-attempt work with deterministic cache metadata. Missing Person ID or absent/wrong policy ID remains `BLOCKED`. Planning does not itself claim that the Person belongs to the Company; the engine must validate its supplied Person/company relationship during execution.

## Benchmark

The curated V1 benchmark contains 18 labeled cases spanning high/medium FIT, multiple intent levels, missing title/geography, explicit non-dental/non-Brazil cases, complementary CEOF routing, optional validated-contact gating, and title/intent conflicts.

```text
CASES = 18
EXACT_ROUTING = 18/18
FALSE_QUALIFIED = 0
FALSE_NOT_QUALIFIED = 0
UNKNOWN_EXPECTED = 3
UNKNOWN_EXACT = 3/3
```

These are local policy-contract calibration/regression metrics, not market precision/recall.

## Commercial policy-path acceptance

A deterministic acceptance scenario evaluates the exact approved WU19 policy using evidence-backed Person role + Brazil state context, materializes the Lead, and repeats the run to prove stable IDs/output.

Expected result:

```text
policy_id = dental-facial-surgery-education-br-v1
qualification_status = QUALIFIED
fit = HIGH
intent = UNKNOWN
priority = P2
deterministic = true
technical_acceptance_gate = SEPARATE_UNCHANGED
live_cfo_gate = NOT_EVALUATED
campaign_legal_gate = NOT_EVALUATED
```

This is a deterministic policy-path acceptance fixture, not a live CFO check and not market accuracy evidence.

## External gates deliberately separate

A `QUALIFIED` result does **not** mean:

- current CFO/CRO registration is verified active;
- a contact is reachable/deliverable;
- the campaign is legally/compliance-approved for sending;
- live HTTP acquisition has been certified;
- `SEND_READY` is true.

Issues #39, #40 and #60 remain separate operational gates.

## Verification

```text
QUALIFICATION_ENGINE_TESTS = 29/29 PASS
QUALIFICATION_ENGINE_LINE_COVERAGE = 100% / 161 statements
QUALIFICATION_ENGINE_BRANCH_COVERAGE = 100% / 80 branches
GAP_PLANNER_TESTS = 36/36 PASS
GAP_PLANNER_LINE_COVERAGE = 100% / 227 statements
GAP_PLANNER_BRANCH_COVERAGE = 100% / 94 branches
COMMERCIAL_ACCEPTANCE_LINE_BRANCH_COVERAGE = 100%
QUALIFICATION_BENCHMARK = 18/18 EXACT
COMBINED_TARGETED_REGRESSION = 83/83 PASS
COMPILEALL = PASS
```

## Documentation basis

- `docs/DENTAL-ICP-POLICY-CONTRACT.md`
- `ICP-DENTAL-FACIAL-SURGERY-V1.md` from the previously documented dental MVP
- `docs/ARCHITECTURE-PRINCIPLES.md`
- `docs/GAP-DETECTION-AND-AUTOMATION.md`
- issue #62
