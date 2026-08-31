# Professional registration chassis bake-off

Status: `ENGINEERING_EVIDENCE` + `LOCAL_EXPERIMENT`.

This experiment was added after re-checking issue #39. In that issue, **CFO means Conselho Federal de Odontologia**, not Chief Financial Officer. The operational requirement is current official dental-registration status through CFO/CRO evidence.

## Domain separation under test

SearchLeads should not conflate three different axes:

```text
Person identity
    |
    +-- professional/company relationships
    |
    +-- professional registrations / licenses / council status
```

A dentist may work with multiple organizations while having one CRO registration. A company relationship can change without changing the professional registration identity, and registration status can change without changing the person identity.

## External baseline: FollowTheMoney Identification

FollowTheMoney `Identification` natively provides useful generic structure:

- holder reference;
- identification number;
- type;
- issuing authority;
- country;
- start/end dates through `Interval`.

This makes it a stronger generic chassis than storing CRO merely as an unstructured string on `Person`.

However, generic `Identification` does **not** enforce the SearchLeads operational state required by issue #39:

- `VERIFIED_ACTIVE`;
- `INACTIVE`;
- `NOT_FOUND`;
- `PENDING`.

It also does not require SearchLeads raw `Evidence` for that decision.

## SearchLeads-specific candidate extension

The bake-off defines an experimental `ProfessionalRegistrationCandidate` with:

- stable registration ID;
- `person_id`;
- authority, such as `CRO-PR`;
- jurisdiction;
- registration number;
- explicit operational status;
- mandatory Evidence IDs;
- timezone-aware `checked_at`.

This is intentionally separate from the company relationship model.

## Critical no-inference rule

Absence of an `endDate` is **not** proof that a registration is currently active.

For example, a historical official record containing:

```text
CRO-PR 22606
startDate = 2015-01-01
endDate = absent
```

must not be promoted to `VERIFIED_ACTIVE` without a current official CFO/CRO check. At most, it remains `PENDING` for the issue #39 gate until current Evidence is obtained.

This matches issue #39's explicit requirement not to promote historical/public evidence to active status by inference.

## Executable probes

`tests/experimental/test_chassis_bakeoff_professional_registration_model.py` covers:

1. native FTM representation of holder/number/type/authority/country/time interval;
2. proof that generic FTM Identification is valid without SearchLeads operational status;
3. mandatory Evidence for SearchLeads registration status;
4. no inference of active status from missing `endDate`;
5. separation of person identity, company relationships and professional registration;
6. a capability scorecard classifying native versus SearchLeads-specific behavior.

## Current capability split

Expected structural classification before execution:

```text
holder reference                         FTM_NATIVE
registration number                      FTM_NATIVE
issuing authority                        FTM_NATIVE
start/end dates                          FTM_NATIVE
explicit SearchLeads activity status     SEARCHLEADS_EXTENSION
mandatory raw Evidence reference         SEARCHLEADS_EXTENSION
current verification timestamp           SEARCHLEADS_EXTENSION
```

These are architecture classifications, not runtime test results. They remain subject to the executable workflow.

## Relevance to issue #39

The model can support the exact operational statuses specified by #39, but it does **not** perform the required live CFO/CRO lookup. Issue #39 therefore remains open until official current checks are actually executed and evidenced.

A domain-model improvement is not equivalent to `PREPARATION_READY`.

## Provisional conclusion

`ENGINEERING_EVIDENCE`: professional registration should be a first-class object independent of canonical person identity and independent of company relationship.

`ENGINEERING_EVIDENCE`: FollowTheMoney `Identification` is a useful generic chassis for the structural portion of this concept.

`SEARCHLEADS_PRODUCT_REQUIREMENT`: current official registration status must be explicit, time-stamped and Evidence-backed.

`HYPOTHESIS`: a SearchLeads registration extension layered over a generic FTM-style identification model is preferable to embedding CRO/CFO state directly in `Person`.
