from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from .campaign_preflight import CampaignPreflightResult, evaluate_campaign_preflight
from .governance_decision_io import (
    campaign_authorization_from_mapping,
    campaign_authorization_to_mapping,
    compliance_signoff_from_mapping,
    compliance_signoff_to_mapping,
)
from .governance_persistence import GovernanceDecisionRepository
from .governance_preflight import CampaignPreflightScope, build_campaign_preflight_inputs
from .professional_verification_io import (
    professional_verification_from_mapping,
    professional_verification_to_mapping,
)


class GovernanceDecisionKind(StrEnum):
    COMPLIANCE_SIGNOFF = "compliance-signoff"
    PROFESSIONAL_VERIFICATION = "professional-verification"
    CAMPAIGN_AUTHORIZATION = "campaign-authorization"


class GovernanceStorageAction(StrEnum):
    INSERTED = "INSERTED"
    ALREADY_PRESENT = "ALREADY_PRESENT"


@dataclass(frozen=True, slots=True)
class GovernanceIntakeReceipt:
    """Auditable result of one bounded human-governance intake operation."""

    kind: GovernanceDecisionKind
    decision_id: str
    storage_action: GovernanceStorageAction
    payload_sha256: str
    evaluated_at: datetime
    preflight: CampaignPreflightResult

    def __post_init__(self) -> None:
        if not self.decision_id.strip():
            raise ValueError("decision_id must not be blank")
        if self.evaluated_at.tzinfo is None:
            raise ValueError("evaluated_at must be timezone-aware")
        if len(self.payload_sha256) != 64:
            raise ValueError("payload_sha256 must be a SHA-256 hex digest")


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_exact(value: str, expected: str, field: str) -> None:
    if value != expected:
        raise ValueError(
            f"{field} does not match preflight scope: {value!r} != {expected!r}"
        )


def _ingest_compliance_signoff(
    *,
    repository: GovernanceDecisionRepository,
    payload: Mapping[str, Any],
    scope: CampaignPreflightScope,
) -> tuple[str, bool, dict[str, Any]]:
    record = compliance_signoff_from_mapping(payload)
    _require_exact(record.campaign_id, scope.campaign_id, "campaign_id")
    _require_exact(record.policy_id, scope.policy_id, "policy_id")
    _require_exact(record.policy_version, scope.policy_version, "policy_version")
    _require_exact(record.jurisdiction, scope.jurisdiction, "jurisdiction")
    _require_exact(record.channel, scope.channel, "channel")
    canonical = compliance_signoff_to_mapping(record)
    return record.signoff_id, repository.save_compliance_signoff(record), canonical


def _ingest_professional_verification(
    *,
    repository: GovernanceDecisionRepository,
    payload: Mapping[str, Any],
    scope: CampaignPreflightScope,
) -> tuple[str, bool, dict[str, Any]]:
    record = professional_verification_from_mapping(payload)
    if scope.person_id is None:
        raise ValueError("person_id is required in scope for professional verification intake")
    _require_exact(record.person_id, scope.person_id, "person_id")
    if scope.council is not None:
        _require_exact(record.council, scope.council, "council")
    canonical = professional_verification_to_mapping(record)
    return (
        record.verification_id,
        repository.save_professional_verification(record),
        canonical,
    )


def _ingest_campaign_authorization(
    *,
    repository: GovernanceDecisionRepository,
    payload: Mapping[str, Any],
    scope: CampaignPreflightScope,
) -> tuple[str, bool, dict[str, Any]]:
    record = campaign_authorization_from_mapping(payload)
    _require_exact(record.campaign_id, scope.campaign_id, "campaign_id")
    _require_exact(record.policy_id, scope.policy_id, "policy_id")
    _require_exact(record.policy_version, scope.policy_version, "policy_version")
    canonical = campaign_authorization_to_mapping(record)
    return (
        record.authorization_id,
        repository.save_campaign_authorization(record),
        canonical,
    )


def process_governance_intake(
    *,
    repository: GovernanceDecisionRepository,
    kind: GovernanceDecisionKind | str,
    payload: Mapping[str, Any],
    scope: CampaignPreflightScope,
    now: datetime,
) -> GovernanceIntakeReceipt:
    """Validate, scope-bind, persist and evaluate one human decision.

    The operation is intentionally bounded to governance state. It never dispatches,
    sends, schedules, or otherwise executes a campaign. Incoming records must match
    the exact preflight scope before they are persisted, preventing accidental
    cross-campaign or cross-person authority leakage.
    """

    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    try:
        normalized_kind = GovernanceDecisionKind(kind)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in GovernanceDecisionKind)
        raise ValueError(f"kind must be one of: {allowed}") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("governance payload must be an object")

    if normalized_kind is GovernanceDecisionKind.COMPLIANCE_SIGNOFF:
        decision_id, inserted, canonical = _ingest_compliance_signoff(
            repository=repository,
            payload=payload,
            scope=scope,
        )
    elif normalized_kind is GovernanceDecisionKind.PROFESSIONAL_VERIFICATION:
        decision_id, inserted, canonical = _ingest_professional_verification(
            repository=repository,
            payload=payload,
            scope=scope,
        )
    else:
        decision_id, inserted, canonical = _ingest_campaign_authorization(
            repository=repository,
            payload=payload,
            scope=scope,
        )

    inputs = build_campaign_preflight_inputs(repository=repository, scope=scope)
    preflight = evaluate_campaign_preflight(inputs=inputs, now=now)
    return GovernanceIntakeReceipt(
        kind=normalized_kind,
        decision_id=decision_id,
        storage_action=(
            GovernanceStorageAction.INSERTED
            if inserted
            else GovernanceStorageAction.ALREADY_PRESENT
        ),
        payload_sha256=_canonical_digest(canonical),
        evaluated_at=now,
        preflight=preflight,
    )


def governance_intake_receipt_to_mapping(
    receipt: GovernanceIntakeReceipt,
) -> dict[str, Any]:
    return {
        "kind": receipt.kind.value,
        "decision_id": receipt.decision_id,
        "storage_action": receipt.storage_action.value,
        "payload_sha256": receipt.payload_sha256,
        "evaluated_at": receipt.evaluated_at.isoformat(),
        "preflight_state": receipt.preflight.state.value,
        "blockers": list(receipt.preflight.blockers),
        "send_authorized": False,
    }


__all__ = [
    "GovernanceDecisionKind",
    "GovernanceIntakeReceipt",
    "GovernanceStorageAction",
    "governance_intake_receipt_to_mapping",
    "process_governance_intake",
]
