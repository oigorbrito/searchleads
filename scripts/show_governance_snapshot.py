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

from searchleads.governance_persistence import GovernanceDecisionRepository  # noqa: E402
from searchleads.governance_preflight import CampaignPreflightScope  # noqa: E402
from searchleads.governance_snapshot import (  # noqa: E402
    build_governance_operational_snapshot,
    governance_operational_snapshot_to_mapping,
)


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


def _scope_from_mapping(payload: Mapping[str, Any]) -> CampaignPreflightScope:
    professional_required = payload.get("professional_verification_required", False)
    if type(professional_required) is not bool:
        raise ValueError("scope.professional_verification_required must be a boolean")
    brasilapi_fresh = payload.get("brasilapi_fresh")
    if type(brasilapi_fresh) is not bool:
        raise ValueError("scope.brasilapi_fresh must be a boolean")
    return CampaignPreflightScope(
        campaign_id=_required_text(payload, "campaign_id"),
        policy_id=_required_text(payload, "policy_id"),
        policy_version=_required_text(payload, "policy_version"),
        jurisdiction=_required_text(payload, "jurisdiction"),
        channel=_required_text(payload, "channel"),
        brasilapi_fresh=brasilapi_fresh,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read persisted governance decisions and emit an auditable operational snapshot. "
            "This command is read-only and never sends or dispatches a campaign."
        )
    )
    parser.add_argument("--scope", required=True, type=Path)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--now", required=True)
    args = parser.parse_args(argv)

    try:
        raw_scope = json.loads(args.scope.read_text(encoding="utf-8"))
        if not isinstance(raw_scope, Mapping):
            raise ValueError("scope must contain a JSON object")
        scope = _scope_from_mapping(raw_scope)
        now = _parse_now(args.now)
        with GovernanceDecisionRepository(args.db) as repository:
            snapshot = build_governance_operational_snapshot(
                repository=repository,
                scope=scope,
                now=now,
            )
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            governance_operational_snapshot_to_mapping(snapshot),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
