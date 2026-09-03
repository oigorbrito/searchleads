from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .campaign_preflight import CampaignAuthorizationRecord, ComplianceSignoffRecord, ReviewDecision


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


def _string_tuple(payload: Mapping[str, Any], field: str) -> tuple[str, ...]:
    value = payload.get(field, [])
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be a list of strings")
    items = tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
    if len(items) != len(value):
        raise ValueError(f"{field} must contain only non-blank strings")
    return items


def compliance_signoff_from_mapping(payload: Mapping[str, Any]) -> ComplianceSignoffRecord:
    if not isinstance(payload, Mapping):
        raise ValueError("compliance signoff payload must be an object")

    decision_text = _required_text(payload, "decision")
    try:
        decision = ReviewDecision(decision_text)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ReviewDecision)
        raise ValueError(f"decision must be one of: {allowed}") from exc

    conditions = _string_tuple(payload, "conditions")
    authority_evidence_refs = _string_tuple(payload, "authority_evidence_refs")

    return ComplianceSignoffRecord(
        signoff_id=_required_text(payload, "signoff_id"),
        reviewer_reference=_required_text(payload, "reviewer_reference"),
        policy_id=_required_text(payload, "policy_id"),
        policy_version=_required_text(payload, "policy_version"),
        jurisdiction=_required_text(payload, "jurisdiction"),
        channel=_required_text(payload, "channel"),
        campaign_id=_required_text(payload, "campaign_id"),
        decision=decision,
        decided_at=_timestamp(payload, "decided_at", required=True),
        expires_at=_timestamp(payload, "expires_at", required=False),
        conditions=conditions,
        authority_evidence_refs=authority_evidence_refs,
        revoked_at=_timestamp(payload, "revoked_at", required=False),
    )


def compliance_signoff_to_mapping(record: ComplianceSignoffRecord) -> dict[str, Any]:
    return {
        "signoff_id": record.signoff_id,
        "reviewer_reference": record.reviewer_reference,
        "policy_id": record.policy_id,
        "policy_version": record.policy_version,
        "jurisdiction": record.jurisdiction,
        "channel": record.channel,
        "campaign_id": record.campaign_id,
        "decision": record.decision.value,
        "decided_at": record.decided_at.isoformat(),
        "expires_at": record.expires_at.isoformat() if record.expires_at is not None else None,
        "conditions": list(record.conditions),
        "authority_evidence_refs": list(record.authority_evidence_refs),
        "revoked_at": record.revoked_at.isoformat() if record.revoked_at is not None else None,
    }


def campaign_authorization_from_mapping(payload: Mapping[str, Any]) -> CampaignAuthorizationRecord:
    if not isinstance(payload, Mapping):
        raise ValueError("campaign authorization payload must be an object")

    return CampaignAuthorizationRecord(
        authorization_id=_required_text(payload, "authorization_id"),
        campaign_id=_required_text(payload, "campaign_id"),
        policy_id=_required_text(payload, "policy_id"),
        policy_version=_required_text(payload, "policy_version"),
        authorizer_reference=_required_text(payload, "authorizer_reference"),
        authorized_at=_timestamp(payload, "authorized_at", required=True),
        valid_until=_timestamp(payload, "valid_until", required=False),
        revoked_at=_timestamp(payload, "revoked_at", required=False),
    )


def campaign_authorization_to_mapping(record: CampaignAuthorizationRecord) -> dict[str, Any]:
    return {
        "authorization_id": record.authorization_id,
        "campaign_id": record.campaign_id,
        "policy_id": record.policy_id,
        "policy_version": record.policy_version,
        "authorizer_reference": record.authorizer_reference,
        "authorized_at": record.authorized_at.isoformat(),
        "valid_until": record.valid_until.isoformat() if record.valid_until is not None else None,
        "revoked_at": record.revoked_at.isoformat() if record.revoked_at is not None else None,
    }


__all__ = [
    "campaign_authorization_from_mapping",
    "campaign_authorization_to_mapping",
    "compliance_signoff_from_mapping",
    "compliance_signoff_to_mapping",
]
