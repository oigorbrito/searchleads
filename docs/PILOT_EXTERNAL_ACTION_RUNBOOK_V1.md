# PILOT_EXTERNAL_ACTION_RUNBOOK_V1

Status: CANONICAL PRE-PILOT HANDOFF

This runbook describes the human/source actions that remain after the internal release-candidate, external-decision-intake, and bounded source-certification work. It does not authorize or execute outreach.

## Current machine state

- Internal Release Candidate: READY
- External Decision Intake: READY
- Externally Certified: READY_WITH_LIMITATIONS
- Commercial Pilot Ready: BLOCKED_LEGAL

## Ordered external actions

1. `LEGAL-001` — legal/compliance reviewer
   - review the exact campaign purpose, policy id/version, jurisdiction, channel and contact class;
   - record one of `APPROVED`, `APPROVED_WITH_CONDITIONS`, `REJECTED`, or `MORE_REVIEW_REQUIRED`;
   - include reviewer reference, decision timestamp, optional expiry, conditions, and authority evidence refs;
   - engineering must not create an approval on the reviewer's behalf.

2. `EXT-CFO-001` — professional reviewer, only when policy requires current professional status
   - perform a person-specific CFO/CRO lookup through the official consultation surface;
   - record person id, council, registration number, observed decision, timestamp and evidence refs;
   - do not infer `VERIFIED_ACTIVE` from a missing end date or from role/company data.

3. `EXT-BRASILAPI-001` — source operator
   - immediately before an otherwise approved use, repeat the bounded read-only point revalidation;
   - require HTTP 200, expected contract fields and an integrity digest;
   - do not treat an older successful probe as indefinitely fresh.

4. `AUTH-CAMPAIGN-001` — campaign owner
   - only after prerequisite gates are satisfied, record campaign-specific authorization bound to policy id/version;
   - include authorizer reference, timestamp, optional expiry and revocation state;
   - generic or unbounded authorization is not accepted.

## Machine evaluation

The canonical sequence is:

`evaluate_campaign_preflight(...)` -> `evaluate_pilot_release(...)`

A blocked preflight maps each gate to its responsible external owner. A green preflight means the recorded authority chain is valid for the exact scoped inputs. Neither function dispatches or sends a campaign.

## Stop conditions

Do not proceed when any of the following is true:

- legal signoff is absent, expired, revoked, rejected or scope-mismatched;
- professional verification is required and is absent, stale, conflicting, inactive or person-mismatched;
- BrasilAPI revalidation is not fresh under `REVALIDATE_BEFORE_USE`;
- campaign authorization is absent, expired, revoked or scope-mismatched;
- a new unknown blocker is reported.

Unknown blockers remain fail-closed and require explicit classification before execution.

## Administrative boundary

This document is an operational handoff, not legal advice, legal approval, campaign authorization, ready-for-review authorization, merge authorization, or send authorization.
