# GOVERNANCE SNAPSHOT RUNBOOK V1

## Purpose

Produce one read-only, auditable operational view of the persisted governance state for an exact campaign scope.

The snapshot explains which gates are satisfied, blocked, or not required; which persisted human decisions support those states; and why the system remains blocked when any gate is open.

It never dispatches, sends, schedules, authorizes, or mutates a campaign.

## Command

```bash
python scripts/show_governance_snapshot.py \
  --scope path/to/scope.json \
  --db path/to/governance.sqlite \
  --now 2026-09-12T02:45:00+00:00
```

## Scope payload

Required fields:

- `campaign_id`
- `policy_id`
- `policy_version`
- `jurisdiction`
- `channel`
- `brasilapi_fresh` (boolean)

Optional policy fields:

- `professional_verification_required` (boolean, default `false`)
- `person_id`
- `council`

When `professional_verification_required=true`, `person_id` is mandatory.

## Snapshot contract

The JSON output contains:

- exact campaign/policy/jurisdiction/channel scope
- evaluation timestamp
- `preflight_state`
- `pilot_release_state`
- ordered `blockers`
- one gate entry for each operational gate
- persisted decision ID, authority reference and evidence references where applicable
- `send_authorized: false`

Operational gates:

1. `EXT-BRASILAPI-001`
2. `LEGAL-001`
3. `EXT-CFO-001`
4. `AUTH-CAMPAIGN-001`

Possible gate statuses:

- `SATISFIED`
- `BLOCKED`
- `NOT_REQUIRED`

`EXT-CFO-001` is `NOT_REQUIRED` when the exact campaign policy does not require professional-status verification.

## Fail-closed semantics

The snapshot reads the latest exact-scope records from `GovernanceDecisionRepository` and delegates validity to the existing record/preflight contracts.

Therefore:

- missing legal signoff blocks `LEGAL-001`
- expired, revoked, rejected or otherwise invalid legal signoff blocks `LEGAL-001`
- missing or non-active current professional verification blocks `EXT-CFO-001` when required
- the latest negative professional record is reported instead of bypassing it with an older approval
- missing, expired or revoked campaign authorization blocks `AUTH-CAMPAIGN-001`
- `brasilapi_fresh=false` blocks `EXT-BRASILAPI-001` regardless of human approvals
- naive timestamps are rejected

## Interpretation

`READY_FOR_AUTHORIZED_EXECUTION` means only that the recorded preflight authority chain is valid for the evaluated scope at the evaluated time.

It does **not** mean:

- send authorization
- campaign dispatch
- live certification
- commercial pilot authorization
- permission to bypass legal/compliance policy

The snapshot deliberately emits `send_authorized: false` in all cases.

## Mutation boundary

This command is read-only. Human decisions must enter through the bounded governance intake path documented in `GOVERNANCE_INTAKE_RUNBOOK_V1.md`.

No provider scraping or external network call is performed by the snapshot command.
