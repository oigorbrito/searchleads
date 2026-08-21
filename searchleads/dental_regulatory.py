"""Narrow regulatory gate for the dental facial-surgery education MVP.

This module does not provide legal advice. It encodes one current campaign-safety
constraint from CFO-SEC-286/2026: complementary courses that teach procedures
exclusive to Cirurgia Estética Orofacial (CEOF) are a different audience from the
CEOF specialization path.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import unicodedata
from typing import Iterable

from .domain import LeadStatus
from .dental_facial_surgery_icp import (
    DentalFacialSurgeryICPV1,
    DentalICPSignal,
    DentalPersonQualificationResult,
    DentalSignalKind,
    LeadPriority,
    DEFAULT_DENTAL_FACIAL_SURGERY_ICP_V1,
    qualify_dental_person,
)


class DentalOfferTrack(str, Enum):
    CEOF_SPECIALIZATION = "CEOF_SPECIALIZATION"
    COMPLEMENTARY_EXCLUSIVE_CEOF = "COMPLEMENTARY_EXCLUSIVE_CEOF"


class RegulatoryEligibility(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class DentalOfferQualificationResult:
    base: DentalPersonQualificationResult
    offer_track: DentalOfferTrack
    regulatory_eligibility: RegulatoryEligibility
    status: LeadStatus
    priority: LeadPriority
    regulatory_reasons: tuple[str, ...]


def _fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value)).casefold()
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.split())


def _is_ceof_title(value: object) -> bool:
    text = _fold(value)
    return "cirurgia estetica orofacial" in text or "ceof" in text


def qualify_dental_person_for_offer(
    person_id: str,
    signals: Iterable[DentalICPSignal],
    *,
    company_id: str | None = None,
    offer_track: DentalOfferTrack = DentalOfferTrack.CEOF_SPECIALIZATION,
    icp: DentalFacialSurgeryICPV1 = DEFAULT_DENTAL_FACIAL_SURGERY_ICP_V1,
) -> DentalOfferQualificationResult:
    items = tuple(signals)
    base = qualify_dental_person(person_id, items, company_id=company_id, icp=icp)

    if base.status is LeadStatus.NOT_QUALIFIED:
        return DentalOfferQualificationResult(
            base,
            offer_track,
            RegulatoryEligibility.INELIGIBLE,
            LeadStatus.NOT_QUALIFIED,
            LeadPriority.EXCLUDE,
            ("profile is outside the active ICP selection before offer-track gating",),
        )

    title_signals = tuple(
        signal for signal in items
        if signal.person_id == person_id
        and signal.kind in {DentalSignalKind.PROFESSIONAL_TITLE, DentalSignalKind.SPECIALTY}
    )

    if offer_track is DentalOfferTrack.CEOF_SPECIALIZATION:
        if not title_signals:
            eligibility = RegulatoryEligibility.UNKNOWN
            reasons = ("professional dental status must be verified before specialization outreach",)
        else:
            eligibility = RegulatoryEligibility.ELIGIBLE
            reasons = (
                "CEOF specialization is the formation path; the lead remains subject to institution/CRO admission verification",
            )
    else:
        if any(_is_ceof_title(signal.value) for signal in title_signals):
            eligibility = RegulatoryEligibility.ELIGIBLE
            reasons = (
                "evidence indicates registered/specialist CEOF title for a complementary exclusive-procedure campaign",
            )
        elif title_signals:
            eligibility = RegulatoryEligibility.INELIGIBLE
            reasons = (
                "complementary exclusive CEOF procedure campaigns require CEOF-specialist eligibility verification",
            )
        else:
            eligibility = RegulatoryEligibility.UNKNOWN
            reasons = (
                "CEOF specialist status is missing for a complementary exclusive-procedure campaign",
            )

    if eligibility is RegulatoryEligibility.INELIGIBLE:
        status = LeadStatus.NOT_QUALIFIED
        priority = LeadPriority.EXCLUDE
    elif eligibility is RegulatoryEligibility.UNKNOWN:
        status = LeadStatus.UNKNOWN
        priority = LeadPriority.REVIEW
    else:
        status = base.status
        priority = base.priority

    return DentalOfferQualificationResult(
        base=base,
        offer_track=offer_track,
        regulatory_eligibility=eligibility,
        status=status,
        priority=priority,
        regulatory_reasons=reasons,
    )
