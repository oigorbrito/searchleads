# AGENTS.md

## Start here

Before making project-state assertions or code changes in this repository, read:

- `HANDOFF-CURRENT-DENTAL-MVP.md`

Treat that handoff as the current continuity source for the dental MVP unless a newer committed handoff explicitly supersedes it.

## Project safety

Preserve these principles:

```text
COMPANY ≠ LEAD
FOUND ≠ VALID
NAME MATCH ≠ ENTITY MATCH
CONTACT FOUND ≠ CONTACT VALID
VALUE WITHOUT EVIDENCE ≠ VERIFIED FACT
DISCOVERY SUCCESS ≠ DISCOVERY COVERAGE
```

Also preserve:

- provenance is mandatory;
- UNKNOWN must remain representable;
- public CRO/title claims are not official CFO verification;
- profession/profile FIT does not imply learning INTENT;
- company/clinic is context for the dental ICP; the commercial object is Person;
- do not invent sources, business requirements, legal status, or qualification evidence.

## Testing

For MVP development, keep new tests focused on expensive business failures.

Before declaring the working branch stable, run the complete regression defined in `.github/workflows/dental-mvp.yml`.

If a check fails:

```text
run → inspect → fix → rerun
```

Do not present a final successful status while a known test is failing.

The latest committed handoff records the most recent verified test counts and acceptance outputs.

## Git / PR rules

Unless explicitly authorized by the user:

- do not merge PRs;
- do not retarget PRs;
- do not mark draft PRs ready;
- do not enable auto-merge;
- do not push directly to `main`.

For the current dental MVP, continue on the existing draft PR/branch described in `HANDOFF-CURRENT-DENTAL-MVP.md`.
