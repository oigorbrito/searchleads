# Dental CFO Verification Workflow — MVP

This is the operational bridge between public lead discovery and `READY/REVIEW/EXCLUDE`.

## Inputs

Use `DENTAL-CFO-VERIFICATION-BATCH-20.csv` as the working sheet.

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

## Campaign legal gate

Default:

```text
campaign_legal_status = PENDING_REVIEW
```

As of 2026-08-21, the TRF1 8th Panel had concluded judgment in case `1003948-83.2019.4.01.3400` against CFO Resolution 198/2019, while publication/procedural developments and possible appeal remained relevant. The MVP therefore keeps outreach blocked until an explicit current legal/compliance review sets:

```text
CONFIRMED_FOR_OUTREACH
```

`PAUSED` explicitly excludes outreach.

This is a campaign-level gate and is separate from an individual dentist's active registration.

## Evaluate the sheet

```bash
python scripts/evaluate_dental_verification_batch.py \
  DENTAL-CFO-VERIFICATION-BATCH-20.csv \
  --output DENTAL-CFO-VERIFICATION-BATCH-20-EVALUATED.csv
```

The command prints a summary such as:

```text
ROWS=20 READY=0 REVIEW=20 EXCLUDE=0
```

and adds:

```text
fit
intent
qualification_status
regulatory_eligibility
outreach_readiness
priority
decision_reason
```

## MVP invariants

- no name-only identity matching;
- public CRO claim != CFO verified CRO;
- public HOF/CEOF claim != official specialty;
- `INTENT=UNKNOWN` does not block the default specialization path;
- complementary exclusive CEOF campaigns require CEOF in official specialty evidence;
- no row can become `READY` while `campaign_legal_status=PENDING_REVIEW`;
- this workflow does not scrape or automate the CFO portal.
