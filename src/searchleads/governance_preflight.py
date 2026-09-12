from __future__ import annotations

from dataclasses import dataclass

from .campaign_preflight import CampaignPreflightInputs
from .governance_persistence import GovernanceDecisionRepository


@dataclass(frozen=True, slots=True)
class CampaignPreflightScope:
    """Exact non-authority inputs needed to recover persisted governance decisions."""

    campaign_id: str
    policy_id: str
    policy_version: str
    jurisdiction: str
    channel: str
    brasilapi_fresh: bool
    professional_verification_required: bool = False
    person_id: str | None = None
    council: str | None = None

    def __post_init__(self) -> None:
        required = (
            self.campaign_id,
            self.policy_id,
            self.policy_version,
            self.jurisdiction,
            self.channel,
        )
        if any(not value.strip() for value in required):
            raise ValueError("campaign preflight scope fields must not be blank")
        if self.professional_verification_required and (
            self.person_id is None or not self.person_id.strip()
        ):
            raise ValueError(
                "person_id is required when professional verification is required"
            )
        if self.person_id is not None and not self.person_id.strip():
            raise ValueError("person_id must not be blank when provided")
        if self.council is not None and not self.council.strip():
            raise ValueError("council must not be blank when provided")


def build_campaign_preflight_inputs(
    *,
    repository: GovernanceDecisionRepository,
    scope: CampaignPreflightScope,
) -> CampaignPreflightInputs:
    """Recover exact-scope governance decisions and construct preflight inputs.

    This function deliberately does not decide whether recovered records are valid,
    expired, revoked, rejected, or otherwise sufficient. That authority remains in
    ``evaluate_campaign_preflight``. The latest persisted candidate record is passed
    through unchanged so newer negative/revoked decisions cannot be bypassed by an
    older approval.
    """

    compliance_signoff = repository.latest_compliance_signoff(
        campaign_id=scope.campaign_id,
        policy_id=scope.policy_id,
        policy_version=scope.policy_version,
        jurisdiction=scope.jurisdiction,
        channel=scope.channel,
    )

    professional_verification = None
    if scope.professional_verification_required and scope.person_id is not None:
        professional_verification = repository.latest_professional_verification(
            person_id=scope.person_id,
            council=scope.council,
        )

    campaign_authorization = repository.latest_campaign_authorization(
        campaign_id=scope.campaign_id,
        policy_id=scope.policy_id,
        policy_version=scope.policy_version,
    )

    return CampaignPreflightInputs(
        campaign_id=scope.campaign_id,
        policy_id=scope.policy_id,
        policy_version=scope.policy_version,
        jurisdiction=scope.jurisdiction,
        channel=scope.channel,
        brasilapi_fresh=scope.brasilapi_fresh,
        professional_verification_required=scope.professional_verification_required,
        person_id=scope.person_id,
        compliance_signoff=compliance_signoff,
        professional_verification=professional_verification,
        campaign_authorization=campaign_authorization,
    )


__all__ = [
    "CampaignPreflightScope",
    "build_campaign_preflight_inputs",
]
