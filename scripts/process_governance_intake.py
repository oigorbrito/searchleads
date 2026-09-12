from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from searchleads.governance_intake import (  # noqa: E402
    GovernanceDecisionKind,
    governance_intake_receipt_to_mapping,
    process_governance_intake,
)
from searchleads.governance_persistence import GovernanceDecisionRepository  # noqa: E402
from searchleads.governance_preflight import CampaignPreflightScope  # noqa: E402


def _required_text(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"scope.{field} must be a non-blank string")
    return value.strip()


def _optional_text(payload: Mapping[str, Any], field: str) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"scope.{field} must be a non-blank string when provided")
    return value.strip()


def _required_bool(payload: Mapping[str, Any], field: str) -> bool:
    value = payload.get(field)
    if type(value) is not bool:
        raise ValueError(f"scope.{field} must be a boolean")
    return value


def _scope_from_mapping(payload: Mapping[str, Any]) -> CampaignPreflightScope:
    if not isinstance(payload, Mapping):
        raise ValueError("scope payload must be an object")
    professional_required = payload.get("professional_verification_required", False)
    if type(professional_required) is not bool:
        raise ValueError("scope.professional_verification_required must be a boolean")
    return CampaignPreflightScope(
        campaign_id=_required_text(payload, "campaign_id"),
        policy_id=_required_text(payload, "policy_id"),
        policy_version=_required_text(payload, "policy_version"),
        jurisdiction=_required_text(payload, "jurisdiction"),
        channel=_required_text(payload, "channel"),
        brasilapi_fresh=_required_bool(payload, "brasilapi_fresh"),
        professional_verification_required=professional_required,
        person_id=_optional_text(payload, "person_id"),
        council=_optional_text(payload, "council"),
    )


def _parse_now(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("--now must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("--now must be timezone-aware")
    return parsed


def _read_json_object(path: Path, label: str) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read {label}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must contain valid JSON") from exc
    if not isinstance(payload, Mapping):
        raise ValueError(f"{label} must contain a JSON object")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate, persist and evaluate one human governance decision. "
            "This command never sends or dispatches a campaign."
        )
    )
    parser.add_argument("kind", choices=tuple(item.value for item in GovernanceDecisionKind))
    parser.add_argument("decision", type=Path, help="JSON file containing the human decision")
    parser.add_argument("--scope", required=True, type=Path, help="JSON file containing exact preflight scope")
    parser.add_argument("--db", required=True, type=Path, help="SQLite governance decision database")
    parser.add_argument("--now", required=True, help="timezone-aware ISO-8601 evaluation timestamp")
    args = parser.parse_args(argv)

    try:
        decision_payload = _read_json_object(args.decision, "decision")
        scope_payload = _read_json_object(args.scope, "scope")
        scope = _scope_from_mapping(scope_payload)
        now = _parse_now(args.now)
        with GovernanceDecisionRepository(args.db) as repository:
            receipt = process_governance_intake(
                repository=repository,
                kind=args.kind,
                payload=decision_payload,
                scope=scope,
                now=now,
            )
    except (ValueError, RuntimeError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            governance_intake_receipt_to_mapping(receipt),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
