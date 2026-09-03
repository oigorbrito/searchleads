from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .campaign_preflight import ProfessionalVerificationRecord, VerificationDecision


def _required_text(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-blank string")
    return value.strip()


def _timestamp(payload: Mapping[str, Any], field: str, *, required: bool) -> datetime | None:
    value = payload.get(field)
    if value is None:
        if required:
            raise ValueError(f"{field} is required")
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be an ISO-8601 string")
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed


def professional_verification_from_mapping(payload: Mapping[str, Any]) -> ProfessionalVerificationRecord:
    if not isinstance(payload, Mapping):
        raise ValueError("professional verification payload must be an object")

    decision_text = _required_text(payload, "decision")
    try:
        decision = VerificationDecision(decision_text)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in VerificationDecision)
        raise ValueError(f"decision must be one of: {allowed}") from exc

    raw_evidence_refs = payload.get("evidence_refs")
    if not isinstance(raw_evidence_refs, (list, tuple)):
        raise ValueError("evidence_refs must be a non-empty list of strings")
    evidence_refs = tuple(
        item.strip() for item in raw_evidence_refs if isinstance(item, str) and item.strip()
    )
    if len(evidence_refs) != len(raw_evidence_refs) or not evidence_refs:
        raise ValueError("evidence_refs must be a non-empty list of non-blank strings")

    return ProfessionalVerificationRecord(
        verification_id=_required_text(payload, "verification_id"),
        person_id=_required_text(payload, "person_id"),
        council=_required_text(payload, "council"),
        registration_number=_required_text(payload, "registration_number"),
        decision=decision,
        verified_at=_timestamp(payload, "verified_at", required=True),
        evidence_refs=evidence_refs,
        reviewer_reference=_required_text(payload, "reviewer_reference"),
        expires_at=_timestamp(payload, "expires_at", required=False),
    )


def professional_verification_to_mapping(record: ProfessionalVerificationRecord) -> dict[str, Any]:
    return {
        "verification_id": record.verification_id,
        "person_id": record.person_id,
        "council": record.council,
        "registration_number": record.registration_number,
        "decision": record.decision.value,
        "verified_at": record.verified_at.isoformat(),
        "evidence_refs": list(record.evidence_refs),
        "reviewer_reference": record.reviewer_reference,
        "expires_at": record.expires_at.isoformat() if record.expires_at is not None else None,
    }


__all__ = [
    "professional_verification_from_mapping",
    "professional_verification_to_mapping",
]
