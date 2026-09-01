from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ReviewDecision(StrEnum):
    APPROVED = "APPROVED"
    APPROVED_WITH_CONDITIONS = "APPROVED_WITH_CONDITIONS"
    REJECTED = "REJECTED"
    MORE_REVIEW_REQUIRED = "MORE_REVIEW_REQUIRED"


class VerificationDecision(StrEnum):
    VERIFIED_ACTIVE = "VERIFIED_ACTIVE"
    VERIFIED_INACTIVE = "VERIFIED_INACTIVE"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"


class CampaignPreflightState(StrEnum):
    READY_FOR_AUTHORIZED_EXECUTION = "READY_FOR_AUTHORIZED_EXECUTION"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class ComplianceSignoffRecord:
    signoff_id: str
    reviewer_reference: str
    policy_id: str
    policy_version: str
    jurisdiction: str
    channel: str
    campaign_id: str
    decision: ReviewDecision
    decided_at: datetime
    expires_at: datetime | None = None
    conditions: tuple[str, ...] = ()
    authority_evidence_refs: tuple[str, ...] = ()
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        required = (
            self.signoff_id,
            self.reviewer_reference,
            self.policy_id,
            self.policy_version,
            self.jurisdiction,
            self.channel,
            self.campaign_id,
        )
        if any(not value.strip() for value in required):
            raise ValueError("compliance signoff fields must not be blank")
        if self.decided_at.tzinfo is None:
            raise ValueError("decided_at must be timezone-aware")
        if self.expires_at is not None and self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")
        if self.revoked_at is not None and self.revoked_at.tzinfo is None:
            raise ValueError("revoked_at must be timezone-aware")
        if self.decision is ReviewDecision.APPROVED_WITH_CONDITIONS and not self.conditions:
            raise ValueError("conditional approval requires explicit conditions")

    def is_valid_for(
        self,
        *,
        now: datetime,
        policy_id: str,
        policy_version: str,
        jurisdiction: str,
        channel: str,
        campaign_id: str,
    ) -> bool:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        if self.decision not in {ReviewDecision.APPROVED, ReviewDecision.APPROVED_WITH_CONDITIONS}:
            return False
        if self.revoked_at is not None and self.revoked_at <= now:
            return False
        if self.expires_at is not None and self.expires_at <= now:
            return False
        return (
            self.policy_id == policy_id
            and self.policy_version == policy_version
            and self.jurisdiction == jurisdiction
            and self.channel == channel
            and self.campaign_id == campaign_id
        )


@dataclass(frozen=True, slots=True)
class ProfessionalVerificationRecord:
    verification_id: str
    person_id: str
    council: str
    registration_number: str
    decision: VerificationDecision
    verified_at: datetime
    evidence_refs: tuple[str, ...]
    reviewer_reference: str
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        required = (
            self.verification_id,
            self.person_id,
            self.council,
            self.registration_number,
            self.reviewer_reference,
        )
        if any(not value.strip() for value in required):
            raise ValueError("professional verification fields must not be blank")
        if self.verified_at.tzinfo is None:
            raise ValueError("verified_at must be timezone-aware")
        if self.expires_at is not None and self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")
        if not self.evidence_refs or any(not item.strip() for item in self.evidence_refs):
            raise ValueError("professional verification requires evidence refs")

    def is_current_active(self, *, now: datetime, person_id: str) -> bool:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        if self.person_id != person_id or self.decision is not VerificationDecision.VERIFIED_ACTIVE:
            return False
        return self.expires_at is None or self.expires_at > now


@dataclass(frozen=True, slots=True)
class CampaignAuthorizationRecord:
    authorization_id: str
    campaign_id: str
    policy_id: str
    policy_version: str
    authorizer_reference: str
    authorized_at: datetime
    valid_until: datetime | None = None
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        required = (
            self.authorization_id,
            self.campaign_id,
            self.policy_id,
            self.policy_version,
            self.authorizer_reference,
        )
        if any(not value.strip() for value in required):
            raise ValueError("campaign authorization fields must not be blank")
        for value in (self.authorized_at, self.valid_until, self.revoked_at):
            if value is not None and value.tzinfo is None:
                raise ValueError("authorization timestamps must be timezone-aware")

    def is_valid_for(self, *, now: datetime, campaign_id: str, policy_id: str, policy_version: str) -> bool:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        if self.revoked_at is not None and self.revoked_at <= now:
            return False
        if self.valid_until is not None and self.valid_until <= now:
            return False
        return (
            self.campaign_id == campaign_id
            and self.policy_id == policy_id
            and self.policy_version == policy_version
        )


@dataclass(frozen=True, slots=True)
class CampaignPreflightInputs:
    campaign_id: str
    policy_id: str
    policy_version: str
    jurisdiction: str
    channel: str
    brasilapi_fresh: bool
    professional_verification_required: bool = False
    person_id: str | None = None
    compliance_signoff: ComplianceSignoffRecord | None = None
    professional_verification: ProfessionalVerificationRecord | None = None
    campaign_authorization: CampaignAuthorizationRecord | None = None


@dataclass(frozen=True, slots=True)
class CampaignPreflightResult:
    state: CampaignPreflightState
    blockers: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return self.state is CampaignPreflightState.READY_FOR_AUTHORIZED_EXECUTION


def evaluate_campaign_preflight(*, inputs: CampaignPreflightInputs, now: datetime) -> CampaignPreflightResult:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    blockers: list[str] = []
    if not inputs.brasilapi_fresh:
        blockers.append("EXT-BRASILAPI-001")
    signoff = inputs.compliance_signoff
    if signoff is None or not signoff.is_valid_for(
        now=now,
        policy_id=inputs.policy_id,
        policy_version=inputs.policy_version,
        jurisdiction=inputs.jurisdiction,
        channel=inputs.channel,
        campaign_id=inputs.campaign_id,
    ):
        blockers.append("LEGAL-001")
    if inputs.professional_verification_required:
        verification = inputs.professional_verification
        if (
            not inputs.person_id
            or verification is None
            or not verification.is_current_active(now=now, person_id=inputs.person_id)
        ):
            blockers.append("EXT-CFO-001")
    authorization = inputs.campaign_authorization
    if authorization is None or not authorization.is_valid_for(
        now=now,
        campaign_id=inputs.campaign_id,
        policy_id=inputs.policy_id,
        policy_version=inputs.policy_version,
    ):
        blockers.append("AUTH-CAMPAIGN-001")
    if blockers:
        return CampaignPreflightResult(CampaignPreflightState.BLOCKED, tuple(blockers))
    return CampaignPreflightResult(CampaignPreflightState.READY_FOR_AUTHORIZED_EXECUTION, ())


__all__ = [
    "CampaignAuthorizationRecord",
    "CampaignPreflightInputs",
    "CampaignPreflightResult",
    "CampaignPreflightState",
    "ComplianceSignoffRecord",
    "ProfessionalVerificationRecord",
    "ReviewDecision",
    "VerificationDecision",
    "evaluate_campaign_preflight",
]
