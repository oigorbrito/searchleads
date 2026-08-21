"""Bridge person-centered dental ICP qualification into the existing Lead schema."""
from __future__ import annotations

from .domain import Lead
from .dental_facial_surgery_icp import DentalPersonQualificationResult
from .dental_regulatory import DentalOfferQualificationResult


def lead_from_dental_person_qualification(result: DentalPersonQualificationResult) -> Lead:
    """Materialize a Company-linked Lead while keeping Person as commercial target."""
    if result.company_id is None:
        raise ValueError("company_id is required to materialize the current Lead schema")
    return Lead(
        lead_id=f"lead:dental-icp:{result.person_id}:{result.company_id}",
        company_id=result.company_id,
        status=result.status,
        reasons=result.reasons,
        qualification_facts=(),
        metadata={
            "qualification_policy_id": result.policy_id,
            "primary_commercial_entity": "PERSON",
            "person_id": result.person_id,
            "fit": result.fit.value,
            "intent": result.intent.value,
            "priority": result.priority.value,
            "signal_ids": result.signal_ids,
            "evidence_ids": result.evidence_ids,
        },
    )


def lead_from_dental_offer_qualification(result: DentalOfferQualificationResult) -> Lead:
    """Materialize the final campaign-specific result after the offer-track gate."""
    base = result.base
    if base.company_id is None:
        raise ValueError("company_id is required to materialize the current Lead schema")
    reasons = tuple(dict.fromkeys(base.reasons + result.regulatory_reasons))
    return Lead(
        lead_id=f"lead:dental-offer:{base.person_id}:{base.company_id}:{result.offer_track.value}",
        company_id=base.company_id,
        status=result.status,
        reasons=reasons,
        qualification_facts=(),
        metadata={
            "qualification_policy_id": base.policy_id,
            "primary_commercial_entity": "PERSON",
            "person_id": base.person_id,
            "fit": base.fit.value,
            "intent": base.intent.value,
            "priority": result.priority.value,
            "offer_track": result.offer_track.value,
            "regulatory_eligibility": result.regulatory_eligibility.value,
            "signal_ids": base.signal_ids,
            "evidence_ids": base.evidence_ids,
        },
    )
