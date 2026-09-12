from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from searchleads.governance_effective_review_verification_receipt import (  # noqa: E402
    EffectiveReviewVerificationReceiptRepository,
    process_verification_receipt,
    receipt_to_mapping,
)


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record or list immutable technical verification receipts for effective-review evidence. Receipts never represent human approval or campaign/send authorization.")
    sub = parser.add_subparsers(dest="command", required=True)

    record = sub.add_parser("record")
    record.add_argument("--evidence", required=True, type=Path)
    record.add_argument("--receipt", required=True, type=Path)
    record.add_argument("--db", required=True, type=Path)

    listing = sub.add_parser("list")
    listing.add_argument("--evidence-sha256", required=True)
    listing.add_argument("--db", required=True, type=Path)

    args = parser.parse_args(argv)
    try:
        with EffectiveReviewVerificationReceiptRepository(args.db) as repository:
            if args.command == "record":
                evidence = _json_object(args.evidence, "evidence")
                receipt_payload = _json_object(args.receipt, "receipt")
                receipt, inserted = process_verification_receipt(repository=repository, evidence_bundle=evidence, receipt_payload=receipt_payload)
                result = receipt_to_mapping(receipt)
                result["storage_action"] = "INSERTED" if inserted else "ALREADY_PRESENT"
            else:
                receipts = repository.list_for_evidence(args.evidence_sha256)
                result = {
                    "evidence_sha256": args.evidence_sha256,
                    "receipts": [receipt_to_mapping(receipt) for receipt in receipts],
                    "receipt_count": len(receipts),
                    "send_authorized": False,
                    "verification_is_campaign_authorization": False,
                    "verification_is_human_approval": False,
                }
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError, KeyError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
