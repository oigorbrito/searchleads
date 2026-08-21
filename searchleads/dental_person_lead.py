"""Bridge person-centered dental ICP qualification into the existing Lead schema."""
from __future__ import annotations

from .domain import Lead
from .dental_facial_surgery_icp import DentalPersonQualificationResult


def lead_from_dental_person_qualification(result: DentalPersonQualificationResult) -> Lead:
    """Materialize a Company-linked Lead while keeping Person as commercial target.

    The current core Lead schema is Company-linked. This bridge therefore requires
    company context, but records the target Person explicitly instead of silently
    replacing person qualification with company qualification.
    """
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
