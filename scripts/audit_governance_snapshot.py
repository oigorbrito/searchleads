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

from searchleads.governance_audit import (  # noqa: E402
    GovernanceAuditRepository,
    governance_audit_entry_to_mapping,
)
from searchleads.governance_persistence import GovernanceDecisionRepository  # noqa: E402
from searchleads.governance_preflight import CampaignPreflightScope  # noqa: E402
from searchleads.governance_snapshot import build_governance_operational_snapshot  # noqa: E402


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


def _record(args: argparse.Namespace) -> dict[str, Any]:
    raw_scope = json.loads(args.scope.read_text(encoding="utf-8"))
    if not isinstance(raw_scope, Mapping):
        raise ValueError("scope must contain a JSON object")
    scope = _scope_from_mapping(raw_scope)
    now = _parse_now(args.now)
    with GovernanceDecisionRepository(args.db) as governance_repository:
        snapshot = build_governance_operational_snapshot(
            repository=governance_repository,
            scope=scope,
            now=now,
        )
    with GovernanceAuditRepository(args.db) as audit_repository:
        entry = audit_repository.append_snapshot(audit_id=args.audit_id, snapshot=snapshot)
    return governance_audit_entry_to_mapping(entry)


def _verify(args: argparse.Namespace) -> dict[str, Any]:
    with GovernanceAuditRepository(args.db) as repository:
        count = repository.verify_chain()
    return {"audit_entries": count, "chain_valid": True, "send_authorized": False}


def _list(args: argparse.Namespace) -> dict[str, Any]:
    with GovernanceAuditRepository(args.db) as repository:
        entries = repository.list_entries()
    return {
        "audit_entries": [governance_audit_entry_to_mapping(entry) for entry in entries],
        "chain_valid": True,
        "send_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Record or verify append-only governance snapshot audit entries. "
            "This command never authorizes, sends or dispatches a campaign."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record")
    record.add_argument("--scope", required=True, type=Path)
    record.add_argument("--db", required=True, type=Path)
    record.add_argument("--now", required=True)
    record.add_argument("--audit-id", required=True)

    verify = subparsers.add_parser("verify")
    verify.add_argument("--db", required=True, type=Path)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--db", required=True, type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "record":
            result = _record(args)
        elif args.command == "verify":
            result = _verify(args)
        else:
            result = _list(args)
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
