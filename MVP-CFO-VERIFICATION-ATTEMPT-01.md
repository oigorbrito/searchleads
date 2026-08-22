# MVP CFO Verification Attempt 01

**Date:** 2026-08-21  
**Batch:** `DENTAL-CFO-VERIFICATION-BATCH-20.csv`  
**Purpose:** avoid silently promoting public CRO claims to official current registration facts.

## Method

For each of the 20 batch candidates, an exact-name/CRO web search was attempted with preference for current CFO/CRO official domains and official/public institutional evidence.

The CFO professional-search portal itself is available and current, but the accessible web interface does not expose a reusable result URL/API that can be safely consumed by SearchLeads without interactive/manual submission. The MVP therefore does not scrape or reverse-engineer that portal.

## Result

```text
BATCH_ROWS = 20
INDEXED_OFFICIAL_SOURCE_ATTEMPTS = 20
CURRENT_OFFICIAL_ACTIVE_CONFIRMATIONS = 0
PUBLIC_CRO_CLAIMS_PROMOTED_TO_VERIFIED = 0
CFO_VERIFIED_ACTIVE = 0/20
PREPARATION_READY = 0/20
```

Public profile pages repeatedly corroborated the claimed CRO numbers and professional roles, but those pages are not official registration sources and were deliberately not used to set `VERIFIED_ACTIVE`.

One candidate (Bruno Andrade Cantharino de Carvalho, claimed CRO-BA 7532) also appears in public judicial material describing him historically as a credentialed Bucomax professional. That is useful provenance but is not a substitute for a current CFO/CRO registration check, so the row remains pending.

## Decision

No candidate is promoted from `PENDING` on the basis of this attempt.

The correct next step remains interactive CFO/CRO verification using the official professional-search service or another official current registration source. Once those fields are recorded in the CSV, `scripts/evaluate_dental_verification_batch.py` can emit `PREPARATION_READY` independently from the campaign send-compliance gate.

## Invariant confirmed

```text
PUBLIC CLAIM != OFFICIAL CURRENT VERIFICATION
```
