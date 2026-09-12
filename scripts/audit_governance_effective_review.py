from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from searchleads.governance_effective_review_audit import (  # noqa: E402
    EffectiveReviewAuditRepository,
    effective_review_audit_entry_to_mapping,
)
from searchleads.governance_effective_review_status import build_effective_evidence_review_status  # noqa: E402
from searchleads.governance_evidence_review import EvidenceReviewRepository  # noqa: E402
from searchleads.governance_evidence_review_resolution import EvidenceReviewResolutionRepository  # noqa: E402


def _json_object(path: Path, label: str) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read {label}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must contain valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return payload


def _record(args: argparse.Namespace) -> dict:
    bundle = _json_object(args.bundle, "bundle")
    with EvidenceReviewRepository(args.review_db) as reviews, EvidenceReviewResolutionRepository(args.resolution_db) as resolutions:
        status = build_effective_evidence_review_status(
            review_repository=reviews,
            resolution_repository=resolutions,
            bundle=bundle,
        )
    with EffectiveReviewAuditRepository(args.audit_db) as audit:
        entry, inserted = audit.append_status(audit_entry_id=args.audit_entry_id, status=status)
    result = effective_review_audit_entry_to_mapping(entry)
    result["storage_action"] = "INSERTED" if inserted else "ALREADY_PRESENT"
    return result


def _verify(args: argparse.Namespace) -> dict:
    with EffectiveReviewAuditRepository(args.audit_db) as audit:
        entries = audit.verify_chain()
    return {
        "valid": True,
        "entry_count": len(entries),
        "latest_entry_hash": entries[-1].entry_hash if entries else None,
        "send_authorized": False,
        "audit_is_campaign_authorization": False,
    }


def _list(args: argparse.Namespace) -> dict:
    with EffectiveReviewAuditRepository(args.audit_db) as audit:
        entries = audit.list_entries()
    return {
        "entries": [effective_review_audit_entry_to_mapping(entry) for entry in entries],
        "send_authorized": False,
        "audit_is_campaign_authorization": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append, verify, or list the tamper-evident audit trail of effective human-review status. This command never authorizes campaign dispatch or send.")
    sub = parser.add_subparsers(dest="command", required=True)

    record = sub.add_parser("record")
    record.add_argument("--bundle", required=True, type=Path)
    record.add_argument("--review-db", required=True, type=Path)
    record.add_argument("--resolution-db", required=True, type=Path)
    record.add_argument("--audit-db", required=True, type=Path)
    record.add_argument("--audit-entry-id", required=True)

    verify = sub.add_parser("verify")
    verify.add_argument("--audit-db", required=True, type=Path)

    listing = sub.add_parser("list")
    listing.add_argument("--audit-db", required=True, type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "record":
            result = _record(args)
        elif args.command == "verify":
            result = _verify(args)
        else:
            result = _list(args)
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError, KeyError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
