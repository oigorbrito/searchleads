from __future__ import annotations

import hashlib
import json

from .domain import ContactValidation, ContactValidationStatus, ReviewCase, ReviewReason
from .entity_resolution import ResolutionDecision, ResolutionResult


def review_for_resolution(
    *, left_company_id: str, right_company_id: str, result: ResolutionResult
) -> ReviewCase | None:
    if result.decision not in {
        ResolutionDecision.UNRESOLVED,
        ResolutionDecision.POSSIBLY_DIFFERENT,
    }:
        return None

    details = {
        "left_company_id": left_company_id,
        "right_company_id": right_company_id,
        "decision": result.decision.value,
        "reasons": list(result.reasons),
    }
    return ReviewCase(
        id=_review_id("CompanyPair", f"{left_company_id}|{right_company_id}", details),
        reason=ReviewReason.ENTITY_AMBIGUITY,
        subject_type="CompanyPair",
        subject_id=f"{left_company_id}|{right_company_id}",
        details=details,
    )


def review_for_contact_validation(validation: ContactValidation) -> ReviewCase | None:
    if validation.status is not ContactValidationStatus.UNKNOWN:
        return None

    details = {
        "contact_validation_id": validation.id,
        "status": validation.status.value,
        "rule": validation.rule,
    }
    return ReviewCase(
        id=_review_id("ContactPoint", validation.contact_point_id, details),
        reason=ReviewReason.CONTACT_VALIDATION_UNKNOWN,
        subject_type="ContactPoint",
        subject_id=validation.contact_point_id,
        details=details,
    )


def _review_id(subject_type: str, subject_id: str, details: dict[str, object]) -> str:
    payload = {
        "subject_type": subject_type,
        "subject_id": subject_id,
        "details": details,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"review:sha256:{digest}"
