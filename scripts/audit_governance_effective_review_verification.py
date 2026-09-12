from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from searchleads.governance_effective_review_verification_audit import (  # noqa: E402
    EffectiveReviewVerificationAuditRepository,
    append_receipt_by_id,
    verification_audit_entry_to_mapping,
)
from searchleads.governance_effective_review_verification_receipt import (  # noqa: E402
    EffectiveReviewVerificationReceiptRepository,
)


def _record(args: argparse.Namespace) -> dict:
    with EffectiveReviewVerificationReceiptRepository(args.receipt_db) as receipts, EffectiveReviewVerificationAuditRepository(args.audit_db) as audit:
        entry, inserted = append_receipt_by_id(
            receipt_repository=receipts,
            audit_repository=audit,
            receipt_id=args.receipt_id,
            audit_entry_id=args.audit_entry_id,
        )
    result = verification_audit_entry_to_mapping(entry)
    result["storage_action"] = "INSERTED" if inserted else "ALREADY_PRESENT"
    return result


def _verify(args: argparse.Namespace) -> dict:
    with EffectiveReviewVerificationAuditRepository(args.audit_db) as audit:
        entries = audit.verify_chain()
    return {
        "valid": True,
        "entry_count": len(entries),
        "latest_entry_hash": entries[-1].entry_hash if entries else None,
        "send_authorized": False,
        "audit_is_campaign_authorization": False,
        "audit_is_human_approval": False,
    }


def _list(args: argparse.Namespace) -> dict:
    with EffectiveReviewVerificationAuditRepository(args.audit_db) as audit:
        entries = audit.list_entries()
    return {
        "entries": [verification_audit_entry_to_mapping(entry) for entry in entries],
        "send_authorized": False,
        "audit_is_campaign_authorization": False,
        "audit_is_human_approval": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append, verify, or list the tamper-evident audit trail of technical effective-review verification receipts. This command never authorizes campaign dispatch/send and never records human approval.")
    sub = parser.add_subparsers(dest="command", required=True)

    record = sub.add_parser("record")
    record.add_argument("--receipt-db", required=True, type=Path)
    record.add_argument("--audit-db", required=True, type=Path)
    record.add_argument("--receipt-id", required=True)
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
    except (OSError, ValueError, RuntimeError, KeyError, json.JSONDecodeError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
