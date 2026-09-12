from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from searchleads.governance_evidence_bundle import verify_governance_evidence_bundle  # noqa: E402
from searchleads.governance_evidence_review import (  # noqa: E402
    EvidenceReviewRepository,
    evidence_review_to_mapping,
    process_evidence_review,
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


def _record(args: argparse.Namespace) -> dict:
    bundle = _json_object(args.bundle, "bundle")
    review_payload = _json_object(args.review, "review")
    with EvidenceReviewRepository(args.db) as repository:
        record, inserted = process_evidence_review(
            repository=repository,
            bundle=bundle,
            review_payload=review_payload,
        )
    result = evidence_review_to_mapping(record)
    result["storage_action"] = "INSERTED" if inserted else "ALREADY_PRESENT"
    return result


def _list(args: argparse.Namespace) -> dict:
    bundle = _json_object(args.bundle, "bundle")
    verify_governance_evidence_bundle(bundle)
    audit_id = bundle.get("audit_id")
    bundle_sha256 = bundle.get("bundle_sha256")
    if not isinstance(audit_id, str) or not isinstance(bundle_sha256, str):
        raise ValueError("verified bundle is missing audit_id or bundle_sha256")
    with EvidenceReviewRepository(args.db) as repository:
        records = repository.list_for_bundle(audit_id=audit_id, bundle_sha256=bundle_sha256)
    return {
        "audit_id": audit_id,
        "bundle_sha256": bundle_sha256,
        "reviews": [evidence_review_to_mapping(record) for record in records],
        "send_authorized": False,
        "reviews_are_campaign_authorization": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Record or list human reviews cryptographically bound to a verified governance evidence bundle. "
            "This command never authorizes, sends, dispatches, or promotes a campaign."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record")
    record.add_argument("--bundle", required=True, type=Path)
    record.add_argument("--review", required=True, type=Path)
    record.add_argument("--db", required=True, type=Path)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--bundle", required=True, type=Path)
    list_parser.add_argument("--db", required=True, type=Path)

    args = parser.parse_args(argv)
    try:
        result = _record(args) if args.command == "record" else _list(args)
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError, KeyError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
