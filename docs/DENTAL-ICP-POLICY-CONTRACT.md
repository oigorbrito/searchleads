# Dental ICP Policy Contract V1

## Work unit

`DENTAL_ICP_POLICY_CONTRACT_V1`

This work unit resolves the clean-stack ICP decision boundary by **reusing, not redefining**, the business requirements already documented in `ICP-DENTAL-FACIAL-SURGERY-V1.md` on the dental MVP branch.

It does not implement qualification. It creates a versioned policy contract that a later qualification engine can consume.

## Scope decision

The scientific foundation originally classified generic `B2B` as a provisional `HYPOTHESIS` and explicitly said that its first work unit did not define a final ICP. That remains true for the generic SearchLeads core.

The repository later records a business-defined first vertical ICP:

```text
POLICY_ID = dental-facial-surgery-education-br-v1
ICP_DEFINED_FOR_VERTICAL = YES
PRIMARY_COMMERCIAL_ENTITY = PERSON
TARGET_PROFESSION = DENTISTRY
COUNTRY = BR
DEFAULT_OFFER_TRACK = CEOF_SPECIALIZATION
GENERIC_CORE_B2B = PROVISIONAL/HYPOTHESIS
```

Therefore this contract does **not** promote a universal company-centered B2B ICP. It says that SearchLeads has one approved vertical policy while the reusable core remains domain-generic.

## Business-requirement fields preserved exactly

The contract preserves the documented vertical decisions:

- commercial target: `Person`;
- profession: dentistry;
- eligible groups: general dentists, dentists with specialty/title, Bucomaxilofacial, and evidence-backed HOF/facial activity;
- Brazil-wide default geography with optional macro-region/state filters;
- core topics: Blefaroplastia, Lip Lift, Lifting facial, Frontoplastia;
- offer formats: in-person, immersion, mentoring, long-form training, online/hybrid;
- default offer track: `CEOF_SPECIALIZATION`;
- complementary exclusive CEOF track requires explicit CEOF-specialist evidence;
- FIT and INTENT remain separate;
- absence of intent evidence remains `UNKNOWN`;
- professional contact is not a default ICP eligibility requirement; a campaign may explicitly require validated contact.

## Company size

`company_size_applicable = false`.

This is not a newly invented size cutoff. The approved commercial entity is the professional (`Person`), with company/clinic retained as evidence/context. The source ICP does not use company size as an eligibility criterion, so V1 marks that dimension non-applicable rather than manufacturing a threshold.

## Missing/conflicting evidence

The contract preserves clean-stack evidence semantics:

- missing evidence for an active required filter → `UNKNOWN/REVIEW`;
- missing learning-intent evidence → `UNKNOWN`;
- unresolved conflict affecting a required criterion → `UNKNOWN/REVIEW`;
- missing CEOF evidence on `COMPLEMENTARY_EXCLUSIVE_CEOF` → `UNKNOWN/REVIEW`;
- known non-CEOF title evidence on that complementary-exclusive track → `NOT_QUALIFIED/EXCLUDE` for that track only.

An unresolved conflict is never coerced into a positive or negative commercial decision merely to complete qualification.

## Decision classification

- Generic core B2B assumption: `HYPOTHESIS`.
- Dental vertical policy contents: explicit business requirement already recorded by the project; not presented as a scientific fact.
- Real-cohort measurements already recorded for the dental MVP: `LOCALLY_VERIFIED` calibration signals only, not market-wide accuracy.
- Regulatory/source facts: must remain `EVIDENCE_BACKED` by their cited official sources when used.
- Missing/conflicting qualification evidence: `UNKNOWN` until resolved under policy.
- Serialization/runtime representation in this work unit: `ENGINEERING_CHOICE`.

## Machine contract

`src/searchleads/qualification_policy/dental_v1.py` exports:

```python
APPROVED_DENTAL_ICP_POLICY_V1
```

The object is immutable and serializes deterministically. Its invariants reject changes that would contradict the documented V1, including:

- switching the commercial target from Person to Company;
- changing Brazil scope;
- turning company size into a criterion;
- requiring contactability by default;
- converting missing intent to LOW;
- converting unresolved required conflicts into a forced qualification.

## Boundaries

This work unit does not:

- implement the qualification engine;
- alter existing Lead records;
- infer current CFO registration;
- change campaign legal/compliance status;
- invent weights or score thresholds;
- claim a universal SearchLeads ICP;
- change Company/Person ER semantics.

Until the qualification engine consumes this contract, existing clean-stack Leads remain `qualification_status = UNKNOWN`.

## Verification

```text
FOCUSED_TESTS = 15/15 PASS
LINE_COVERAGE = 100% / 52 statements
BRANCH_COVERAGE = 100% / 16 branches
COMPILEALL = PASS
```

## Documentation basis

- `ICP-DENTAL-FACIAL-SURGERY-V1.md` (`feat/dental-facial-surgery-icp-v1` / PR #36)
- `docs/SCIENTIFIC-FOUNDATION.md`
- `docs/ARCHITECTURE-PRINCIPLES.md`
- issue #61
