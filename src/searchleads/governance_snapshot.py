from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from .campaign_preflight import (
    CampaignAuthorizationRecord,
    ComplianceSignoffRecord,
    ProfessionalVerificationRecord,
    evaluate_campaign_preflight,
)
from .governance_persistence import GovernanceDecisionRepository
from .governance_preflight import CampaignPreflightScope, build_campaign_preflight_inputs
from .pilot_release import ActionOwner, evaluate_pilot_release


class GateSnapshotStatus(StrEnum):
    SATISFIED = "SATISFIED"
    BLOCKED = "BLOCKED"
    NOT_REQUIRED = "NOT_REQUIRED"


@dataclass(frozen=True, slots=True)
class GateSnapshot:
    gate_id: str
    status: GateSnapshotStatus
    owner: ActionOwner
    reason: str
    decision_id: str | None = None
    authority_reference: str | None = None
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GovernanceOperationalSnapshot:
    generated_at: datetime
    campaign_id: str
    policy_id: str
    policy_version: str
    jurisdiction: str
    channel: str
    preflight_state: str
    pilot_release_state: str
    gates: tuple[GateSnapshot, ...]
    send_authorized: bool = False

    def __post_init__(self) -> None:
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware")
        if self.send_authorized:
            raise ValueError("governance snapshot cannot authorize send")

    @property
    def blockers(self) -> tuple[str, ...]:
        return tuple(gate.gate_id for gate in self.gates if gate.status is GateSnapshotStatus.BLOCKED)


def _legal_gate(record: ComplianceSignoffRecord | None, *, valid: bool) -> GateSnapshot:
    if record is None:
        return GateSnapshot(
            gate_id="LEGAL-001",
            status=GateSnapshotStatus.BLOCKED,
            owner=ActionOwner.LEGAL_COMPLIANCE,
            reason="no scoped legal/compliance decision is persisted",
        )
    return GateSnapshot(
        gate_id="LEGAL-001",
        status=GateSnapshotStatus.SATISFIED if valid else GateSnapshotStatus.BLOCKED,
        owner=ActionOwner.LEGAL_COMPLIANCE,
        reason=(
            "latest scoped legal/compliance decision is currently valid"
            if valid
            else "latest scoped legal/compliance decision is not currently valid"
        ),
        decision_id=record.signoff_id,
        authority_reference=record.reviewer_reference,
        evidence_refs=record.authority_evidence_refs,
    )


def _professional_gate(
    record: ProfessionalVerificationRecord | None,
    *,
    required: bool,
    valid: bool,
) -> GateSnapshot:
    if not required:
        return GateSnapshot(
            gate_id="EXT-CFO-001",
            status=GateSnapshotStatus.NOT_REQUIRED,
            owner=ActionOwner.PROFESSIONAL_REVIEWER,
            reason="approved campaign policy does not require professional-status verification",
        )
    if record is None:
        return GateSnapshot(
            gate_id="EXT-CFO-001",
            status=GateSnapshotStatus.BLOCKED,
            owner=ActionOwner.PROFESSIONAL_REVIEWER,
            reason="no person-specific professional verification is persisted for this scope",
        )
    return GateSnapshot(
        gate_id="EXT-CFO-001",
        status=GateSnapshotStatus.SATISFIED if valid else GateSnapshotStatus.BLOCKED,
        owner=ActionOwner.PROFESSIONAL_REVIEWER,
        reason=(
            "latest person-specific professional verification is current and active"
            if valid
            else "latest person-specific professional verification is not current and active"
        ),
        decision_id=record.verification_id,
        authority_reference=record.reviewer_reference,
        evidence_refs=record.evidence_refs,
    )


def _authorization_gate(
    record: CampaignAuthorizationRecord | None,
    *,
    valid: bool,
) -> GateSnapshot:
    if record is None:
        return GateSnapshot(
            gate_id="AUTH-CAMPAIGN-001",
            status=GateSnapshotStatus.BLOCKED,
            owner=ActionOwner.CAMPAIGN_OWNER,
            reason="no scoped campaign authorization is persisted",
        )
    return GateSnapshot(
        gate_id="AUTH-CAMPAIGN-001",
        status=GateSnapshotStatus.SATISFIED if valid else GateSnapshotStatus.BLOCKED,
        owner=ActionOwner.CAMPAIGN_OWNER,
        reason=(
            "latest scoped campaign authorization is currently valid"
            if valid
            else "latest scoped campaign authorization is not currently valid"
        ),
        decision_id=record.authorization_id,
        authority_reference=record.authorizer_reference,
    )


def build_governance_operational_snapshot(
    *,
    repository: GovernanceDecisionRepository,
    scope: CampaignPreflightScope,
    now: datetime,
) -> GovernanceOperationalSnapshot:
    """Build one read-only, auditable view of all operational governance gates.

    This function never persists, dispatches, sends, schedules, or promotes a campaign.
    It reads the latest exact-scope governance records, delegates validity to the
    existing record contracts/preflight, and reports why each gate is or is not open.
    """

    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    inputs = build_campaign_preflight_inputs(repository=repository, scope=scope)
    preflight = evaluate_campaign_preflight(inputs=inputs, now=now)
    release = evaluate_pilot_release(preflight)

    signoff = inputs.compliance_signoff
    legal_valid = signoff is not None and signoff.is_valid_for(
        now=now,
        policy_id=scope.policy_id,
        policy_version=scope.policy_version,
        jurisdiction=scope.jurisdiction,
        channel=scope.channel,
        campaign_id=scope.campaign_id,
    )

    verification = inputs.professional_verification
    professional_valid = (
        scope.professional_verification_required
        and scope.person_id is not None
        and verification is not None
        and verification.is_current_active(now=now, person_id=scope.person_id)
    )

    authorization = inputs.campaign_authorization
    authorization_valid = authorization is not None and authorization.is_valid_for(
        now=now,
        campaign_id=scope.campaign_id,
        policy_id=scope.policy_id,
        policy_version=scope.policy_version,
    )

    gates = (
        GateSnapshot(
            gate_id="EXT-BRASILAPI-001",
            status=(GateSnapshotStatus.SATISFIED if scope.brasilapi_fresh else GateSnapshotStatus.BLOCKED),
            owner=ActionOwner.SOURCE_OPERATOR,
            reason=(
                "bounded BrasilAPI source revalidation is marked fresh for this evaluation"
                if scope.brasilapi_fresh
                else "bounded BrasilAPI source revalidation is not fresh for this evaluation"
            ),
        ),
        _legal_gate(signoff, valid=legal_valid),
        _professional_gate(
            verification,
            required=scope.professional_verification_required,
            valid=professional_valid,
        ),
        _authorization_gate(authorization, valid=authorization_valid),
    )

    return GovernanceOperationalSnapshot(
        generated_at=now,
        campaign_id=scope.campaign_id,
        policy_id=scope.policy_id,
        policy_version=scope.policy_version,
        jurisdiction=scope.jurisdiction,
        channel=scope.channel,
        preflight_state=preflight.state.value,
        pilot_release_state=release.state.value,
        gates=gates,
        send_authorized=False,
    )


def governance_operational_snapshot_to_mapping(
    snapshot: GovernanceOperationalSnapshot,
) -> dict[str, Any]:
    return {
        "generated_at": snapshot.generated_at.isoformat(),
        "campaign_id": snapshot.campaign_id,
        "policy_id": snapshot.policy_id,
        "policy_version": snapshot.policy_version,
        "jurisdiction": snapshot.jurisdiction,
        "channel": snapshot.channel,
        "preflight_state": snapshot.preflight_state,
        "pilot_release_state": snapshot.pilot_release_state,
        "blockers": list(snapshot.blockers),
        "send_authorized": False,
        "gates": [
            {
                "gate_id": gate.gate_id,
                "status": gate.status.value,
                "owner": gate.owner.value,
                "reason": gate.reason,
                "decision_id": gate.decision_id,
                "authority_reference": gate.authority_reference,
                "evidence_refs": list(gate.evidence_refs),
            }
            for gate in snapshot.gates
        ],
    }


__all__ = [
    "GateSnapshot",
    "GateSnapshotStatus",
    "GovernanceOperationalSnapshot",
    "build_governance_operational_snapshot",
    "governance_operational_snapshot_to_mapping",
]
