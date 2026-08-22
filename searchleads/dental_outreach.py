"""Minimal outreach-readiness gate for the dental MVP.

The gate intentionally accepts CFO verification as an explicit external/manual
input. It does not scrape or infer official registry status.
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


def _fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value)).casefold()
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _official_ceof(specialties: tuple[str, ...]) -> bool:
    return any("cirurgia estetica orofacial" in _fold(item) or "ceof" in _fold(item) for item in specialties)


def evaluate_dental_outreach_readiness(
    qualification: DentalOfferQualificationResult,
    verification: CFOProfessionalVerification,
) -> DentalOutreachDecision:
    base = qualification.base
    if verification.person_id != base.person_id:
        raise ValueError("CFO verification person_id must match qualification person_id")

    if qualification.status is LeadStatus.NOT_QUALIFIED or qualification.regulatory_eligibility is RegulatoryEligibility.INELIGIBLE:
        return DentalOutreachDecision(
            base.person_id,
            OutreachReadiness.EXCLUDE,
            qualification.priority.value,
            ("profile or offer track is not eligible",),
            verification.evidence_id,
        )

    if verification.registration_state in {CFORegistrationState.INACTIVE, CFORegistrationState.NOT_FOUND}:
        return DentalOutreachDecision(
            base.person_id,
            OutreachReadiness.EXCLUDE,
            qualification.priority.value,
            ("official CFO verification does not show an active registration",),
            verification.evidence_id,
        )

    if verification.registration_state is not CFORegistrationState.VERIFIED_ACTIVE:
        return DentalOutreachDecision(
            base.person_id,
            OutreachReadiness.REVIEW,
            qualification.priority.value,
            ("official CFO verification is still pending",),
            verification.evidence_id,
        )

    if qualification.offer_track is DentalOfferTrack.COMPLEMENTARY_EXCLUSIVE_CEOF and not _official_ceof(verification.specialty_names):
        return DentalOutreachDecision(
            base.person_id,
            OutreachReadiness.EXCLUDE,
            qualification.priority.value,
            ("official CFO specialties do not verify CEOF for the complementary exclusive-procedure track",),
            verification.evidence_id,
        )

    if not base.has_professional_contact:
        return DentalOutreachDecision(
            base.person_id,
            OutreachReadiness.REVIEW,
            qualification.priority.value,
            ("no public professional contact channel is available",),
            verification.evidence_id,
        )

    if qualification.regulatory_eligibility is not RegulatoryEligibility.ELIGIBLE:
        return DentalOutreachDecision(
            base.person_id,
            OutreachReadiness.REVIEW,
            qualification.priority.value,
            ("offer-track regulatory eligibility is not yet confirmed",),
            verification.evidence_id,
        )

    return DentalOutreachDecision(
        base.person_id,
        OutreachReadiness.READY,
        qualification.priority.value,
        ("active CFO registration, eligible offer track, ICP fit and public professional contact are present",),
        verification.evidence_id,
    )
