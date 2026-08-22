# Dental CFO Verification Workflow — MVP

This is the operational bridge between public lead discovery and outreach preparation/sending.

## Active input

Use `DENTAL-CFO-VERIFICATION-BATCH-50.csv` as the current working sheet. The earlier 20-row file is retained as the first historical smoke batch.

The active sheet has 50 public candidates, balanced at 10 per Brazilian macro-region.

Public discovery columns are intentionally separate from official verification columns:

```text
public claim: claimed_cro_state / claimed_cro_number / professional_title / public_evidence_url
official review: cfo_registration_state / verified_cro_state / verified_cro_number / verified_specialties / cfo_source_url
campaign gate: campaign_legal_status
```

A public CRO claim is never treated as official verification.

## Verification rule

For each candidate, use the CFO professional search or an official CRO source and record only what that official source supports.

Allowed registration states:

```text
PENDING
VERIFIED_ACTIVE
INACTIVE
NOT_FOUND
```

When `VERIFIED_ACTIVE`, fill `verified_cro_state`, `verified_cro_number` and `cfo_source_url`. Fill `verified_specialties` only with specialties supported by the official source, separated by semicolons.

Do not copy a specialty from Doctoralia, a clinic site or social profile into `verified_specialties`.

## Current regulatory context — 2026-08-21

SearchLeads keeps two different legal/regulatory questions separate.

### HOF litigation

The TRF1 8th Panel concluded judgment on 2026-08-19 in case `1003948-83.2019.4.01.3400`, concerning CFO Resolution 198/2019 (Harmonização Orofacial). Current reporting indicates a majority decision against that 2019 resolution, with publication/procedural developments and appeal still relevant.

### CEOF rules

The dental surgical offer in this MVP is separately modeled around the 2026 CFO acts, especially:

- CFO-SEC-285/2026, which amended the earlier facial-surgery prohibition framework;
- CFO-SEC-286/2026, which recognizes Cirurgia Estética Orofacial (CEOF) and defines its procedures and formation requirements;
- CFO Technical Note 001/2026, which emphasizes that procedures must follow the specific competence rules of each specialty rather than being extended by analogy.

The CEOF resolution has also been challenged politically through PDL 177/2026, which was still pending on 2026-08-21. SearchLeads does not infer from a pending challenge that the resolution is suspended, nor does it provide legal advice.

## Two readiness layers

The evaluator preserves useful lead work even while campaign-level compliance is under review.

```text
PREPARATION_READY
= active official CFO registration
+ eligible ICP / offer track
+ public professional contact

SEND_READY
= PREPARATION_READY
+ explicit current campaign legal/compliance confirmation
```

Default campaign state remains:

```text
campaign_legal_status = PENDING_REVIEW
```

This is a conservative operational control, not a claim that CFO-SEC-285/286 are invalid or suspended.

`CONFIRMED_FOR_OUTREACH` allows sending after an explicit current review. `PAUSED` blocks sending.

## Evaluate the active sheet

```bash
PYTHONPATH=. python scripts/evaluate_dental_verification_batch.py \
  DENTAL-CFO-VERIFICATION-BATCH-50.csv \
  --output DENTAL-CFO-VERIFICATION-BATCH-50-EVALUATED.csv
```

The untouched 50-row sheet currently produces:

```text
ROWS=50 PREP_READY=0 SEND_READY=0 REVIEW=50 EXCLUDE=0
```

After official CFO verification, rows may become `PREP_READY=READY` even while `SEND_READY` remains under campaign review.

The output adds:

```text
fit
intent
qualification_status
regulatory_eligibility
preparation_readiness
outreach_readiness
priority
decision_reason
```

## Official-source attempt

`MVP-CFO-VERIFICATION-ATTEMPT-01.md` records the first indexed official-source attempt on the original 20 rows. It produced zero safe current active confirmations; no public CRO claim was promoted.

The remaining verification boundary is therefore interactive/manual CFO/CRO review, not more internal qualification code.

## MVP invariants

- no name-only identity matching;
- public CRO claim != CFO verified CRO;
- public HOF/CEOF claim != official specialty;
- `INTENT=UNKNOWN` does not block the default specialization path;
- complementary exclusive CEOF courses require CEOF in official specialty evidence;
- CEOF-specific procedure competence is not inferred from HOF/CTBMF by analogy;
- campaign compliance is separate from professional verification;
- this workflow does not scrape or automate the CFO portal.
