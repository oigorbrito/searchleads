# Governance Intake Runbook V1

Status: engineering boundary for human-governance intake. This runbook does **not** grant send authority.

## Purpose

Provide one bounded operational path for externally supplied human decisions:

1. validate the decision payload;
2. bind it to an exact campaign/person scope;
3. persist it immutably with storage-integrity protection;
4. reconstruct `CampaignPreflightInputs` from persisted governance state;
5. evaluate `evaluate_campaign_preflight`;
6. emit an auditable receipt.

No step dispatches, schedules, sends, or otherwise executes outreach.

## Supported decision kinds

- `compliance-signoff`
- `professional-verification`
- `campaign-authorization`

The decision payloads use the same canonical contracts already enforced by `governance_decision_io.py` and `professional_verification_io.py`.

## Scope document

The scope JSON must contain:

```json
{
  "campaign_id": "campaign-1",
  "policy_id": "policy-1",
  "policy_version": "v1",
  "jurisdiction": "BR-RS",
  "channel": "email",
  "brasilapi_fresh": false,
  "professional_verification_required": true,
  "person_id": "person-1",
  "council": "CRO-RS"
}
```

`person_id` is mandatory when `professional_verification_required=true`. `council` is optional, but when provided it narrows professional verification lookup and intake binding.

## Command

```bash
python scripts/process_governance_intake.py \
  compliance-signoff decision.json \
  --scope scope.json \
  --db governance.sqlite \
  --now 2026-09-12T03:00:00+00:00
```

The command exits `0` when the human record was validly ingested, even if campaign preflight remains blocked. A blocked preflight is an operational state, not an intake failure. Invalid payloads, invalid scope, cross-scope authority mismatches, or persistence conflicts exit `2`.

## Receipt semantics

A successful receipt contains:

- decision kind and immutable decision ID;
- storage action (`INSERTED` or `ALREADY_PRESENT`);
- SHA-256 digest of the canonical human decision payload;
- evaluation timestamp;
- preflight state and blockers;
- `send_authorized: false` unconditionally.

`READY_FOR_AUTHORIZED_EXECUTION` means only that the existing preflight contract found no blockers for the supplied scope at the evaluation time. It is not a send authorization and triggers no dispatch.

## Fail-closed behavior

- A decision whose campaign/policy/person scope does not exactly match the requested preflight scope is rejected before persistence.
- Replaying the exact same immutable decision is idempotent.
- Reusing an immutable ID with different content remains a persistence conflict.
- Negative, revoked, expired, or otherwise invalid decisions are persisted as supplied and evaluated by the existing preflight rules; they are not silently skipped in favor of older approvals.
- Human governance intake cannot satisfy `EXT-BRASILAPI-001`. When `brasilapi_fresh=false`, preflight remains blocked regardless of human decision state.

## Operational invariants

- `REAL_SEND = NOT_AUTHORIZED`
- `SEND_READY_OPERATIONAL_STATE` is not changed by this command.
- `LIVE_CERTIFICATION` is not changed by this command.
- No SERPRO, DNS/HTTP, CFO, or CRO scraping adapter is introduced.
- No external human approval is invented by the software.
