from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from searchleads.campaign_preflight import CampaignPreflightResult, CampaignPreflightState


class PilotReleaseState(StrEnum):
    BLOCKED_EXTERNAL_DECISION = "BLOCKED_EXTERNAL_DECISION"
    READY_FOR_AUTHORIZED_EXECUTION = "READY_FOR_AUTHORIZED_EXECUTION"


class ActionOwner(StrEnum):
    LEGAL_COMPLIANCE = "LEGAL_COMPLIANCE"
    PROFESSIONAL_REVIEWER = "PROFESSIONAL_REVIEWER"
    CAMPAIGN_OWNER = "CAMPAIGN_OWNER"
    SOURCE_OPERATOR = "SOURCE_OPERATOR"
    NONE = "NONE"


@dataclass(frozen=True, slots=True)
class RequiredExternalAction:
    gate_id: str
    owner: ActionOwner
    action: str


@dataclass(frozen=True, slots=True)
class PilotReleaseDecision:
    state: PilotReleaseState
    required_actions: tuple[RequiredExternalAction, ...]
    send_authorized: bool = False

    @property
    def ready(self) -> bool:
        return self.state is PilotReleaseState.READY_FOR_AUTHORIZED_EXECUTION


_ACTIONS: dict[str, tuple[ActionOwner, str]] = {
    "LEGAL-001": (
        ActionOwner.LEGAL_COMPLIANCE,
        "record a scoped legal/compliance decision for the exact campaign policy, jurisdiction, channel and campaign",
    ),
    "EXT-CFO-001": (
        ActionOwner.PROFESSIONAL_REVIEWER,
        "perform and record a person-specific current CFO/CRO verification with evidence when policy requires it",
    ),
    "AUTH-CAMPAIGN-001": (
        ActionOwner.CAMPAIGN_OWNER,
        "record campaign-specific authorization after all prerequisite gates are satisfied",
    ),
    "EXT-BRASILAPI-001": (
        ActionOwner.SOURCE_OPERATOR,
        "repeat the bounded read-only BrasilAPI revalidation immediately before approved use",
    ),
}


def evaluate_pilot_release(preflight: CampaignPreflightResult) -> PilotReleaseDecision:
    if preflight.state is CampaignPreflightState.READY_FOR_AUTHORIZED_EXECUTION:
        # A green preflight means the recorded authority chain is valid. It does
        # not itself execute or dispatch a campaign.
        return PilotReleaseDecision(
            PilotReleaseState.READY_FOR_AUTHORIZED_EXECUTION,
            (),
            send_authorized=True,
        )

    actions: list[RequiredExternalAction] = []
    for gate_id in preflight.blockers:
        owner, action = _ACTIONS.get(
            gate_id,
            (ActionOwner.NONE, "resolve the explicitly reported external gate before execution"),
        )
        actions.append(RequiredExternalAction(gate_id, owner, action))
    return PilotReleaseDecision(
        PilotReleaseState.BLOCKED_EXTERNAL_DECISION,
        tuple(actions),
        send_authorized=False,
    )


__all__ = [
    "ActionOwner",
    "PilotReleaseDecision",
    "PilotReleaseState",
    "RequiredExternalAction",
    "evaluate_pilot_release",
]
