"""Minimal outreach-readiness gate for the dental MVP.

The gate intentionally accepts CFO verification as an explicit external/manual
input. It does not scrape or infer official registry status.

A separate campaign-level legal-status input is required before any profile can
become READY. This keeps individual professional verification distinct from the
current legal/regulatory ability to run the campaign.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import unicodedata

from .domain import LeadStatus
from .dental_regulatory import (
    DentalOfferQualificationResult,
    DentalOfferTrack,
    RegulatoryEligibility,
)


class CFORegistrationState(str, Enum):
    PENDING = "PENDING"
    VERIFIED_ACTIVE = "VERIFIED_ACTIVE"
    INACTIVE = "INACTIVE"
    NOT_FOUND = "NOT_FOUND"


class CampaignLegalStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    CONFIRMED_FOR_OUTREACH = "CONFIRMED_FOR_OUTREACH"
    PAUSED = "PAUSED"


class OutreachReadiness(str, Enum):
    READY = "READY"
    REVIEW = "REVIEW"
    EXCLUDE = "EXCLUDE"


@dataclass(frozen=True, slots=True)
class CFOProfessionalVerification:
    person_id: str
    registration_state: CFORegistrationState
    cro_state: str | None
    cro_number: str | None
    specialty_names: tuple[str, ...]
    evidence_id: str

    def __post_init__(self) -> None:
        if not self.person_id.strip() or not self.evidence_id.strip():
            raise ValueError("person_id and evidence_id must be non-blank")
        if self.registration_state is CFORegistrationState.VERIFIED_ACTIVE:
            if not self.cro_state or not self.cro_number:
                raise ValueError("active CFO verification requires CRO state and number")


@dataclass(frozen=True, slots=True)
class DentalOutreachDecision:
    person_id: str
    readiness: OutreachReadiness
    priority: str
    reasons: tuple[str, ...]
    cfo_evidence_id: str
    campaign_legal_status: CampaignLegalStatus


def _fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value)).casefold()
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _official_ceof(specialties: tuple[str, ...]) -> bool:
    return any("cirurgia estetica orofacial" in _fold(item) or "ceof" in _fold(item) for item in specialties)


def _decision(
    qualification: DentalOfferQualificationResult,
    verification: CFOProfessionalVerification,
    readiness: OutreachReadiness,
    reason: str,
    campaign_legal_status: CampaignLegalStatus,
) -> DentalOutreachDecision:
    return DentalOutreachDecision(
        qualification.base.person_id,
        readiness,
        qualification.priority.value,
        (reason,),
        verification.evidence_id,
        campaign_legal_status,
    )


def evaluate_dental_outreach_readiness(
    qualification: DentalOfferQualificationResult,
    verification: CFOProfessionalVerification,
    *,
    campaign_legal_status: CampaignLegalStatus = CampaignLegalStatus.PENDING_REVIEW,
) -> DentalOutreachDecision:
    base = qualification.base
    if verification.person_id != base.person_id:
        raise ValueError("CFO verification person_id must match qualification person_id")

    if qualification.status is LeadStatus.NOT_QUALIFIED or qualification.regulatory_eligibility is RegulatoryEligibility.INELIGIBLE:
        return _decision(
            qualification,
            verification,
            OutreachReadiness.EXCLUDE,
            "profile or offer track is not eligible",
            campaign_legal_status,
        )

    if verification.registration_state in {CFORegistrationState.INACTIVE, CFORegistrationState.NOT_FOUND}:
        return _decision(
            qualification,
            verification,
            OutreachReadiness.EXCLUDE,
            "official CFO verification does not show an active registration",
            campaign_legal_status,
        )

    if verification.registration_state is not CFORegistrationState.VERIFIED_ACTIVE:
        return _decision(
            qualification,
            verification,
            OutreachReadiness.REVIEW,
            "official CFO verification is still pending",
            campaign_legal_status,
        )

    if qualification.offer_track is DentalOfferTrack.COMPLEMENTARY_EXCLUSIVE_CEOF and not _official_ceof(verification.specialty_names):
        return _decision(
            qualification,
            verification,
            OutreachReadiness.EXCLUDE,
            "official CFO specialties do not verify CEOF for the complementary exclusive-procedure track",
            campaign_legal_status,
        )

    if not base.has_professional_contact:
        return _decision(
            qualification,
            verification,
            OutreachReadiness.REVIEW,
            "no public professional contact channel is available",
            campaign_legal_status,
        )

    if qualification.regulatory_eligibility is not RegulatoryEligibility.ELIGIBLE:
        return _decision(
            qualification,
            verification,
            OutreachReadiness.REVIEW,
            "offer-track regulatory eligibility is not yet confirmed",
            campaign_legal_status,
        )

    if campaign_legal_status is CampaignLegalStatus.PAUSED:
        return _decision(
            qualification,
            verification,
            OutreachReadiness.EXCLUDE,
            "campaign is paused by the current legal/compliance gate",
            campaign_legal_status,
        )

    if campaign_legal_status is not CampaignLegalStatus.CONFIRMED_FOR_OUTREACH:
        return _decision(
            qualification,
            verification,
            OutreachReadiness.REVIEW,
            "campaign-level legal status requires current review before outreach",
            campaign_legal_status,
        )

    return _decision(
        qualification,
        verification,
        OutreachReadiness.READY,
        "active CFO registration, eligible offer track, ICP fit, public professional contact and campaign legal confirmation are present",
        campaign_legal_status,
    )
