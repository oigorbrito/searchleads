from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from searchleads.governance_evidence_review import EvidenceReviewRepository  # noqa: E402
from searchleads.governance_evidence_review_resolution import (  # noqa: E402
    EvidenceReviewResolutionRepository,
    build_evidence_review_resolution_status,
    evidence_review_resolution_status_to_mapping,
    evidence_review_resolution_to_mapping,
    process_evidence_review_resolution,
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
    payload = _json_object(args.resolution, "resolution")
    with EvidenceReviewRepository(args.review_db) as review_repository, EvidenceReviewResolutionRepository(args.resolution_db) as resolution_repository:
        record, inserted = process_evidence_review_resolution(
            review_repository=review_repository,
            resolution_repository=resolution_repository,
            bundle=bundle,
            resolution_payload=payload,
        )
    result = evidence_review_resolution_to_mapping(record)
    result["storage_action"] = "INSERTED" if inserted else "ALREADY_PRESENT"
    return result


def _status(args: argparse.Namespace) -> dict:
    bundle = _json_object(args.bundle, "bundle")
    with EvidenceReviewRepository(args.review_db) as review_repository, EvidenceReviewResolutionRepository(args.resolution_db) as resolution_repository:
        status = build_evidence_review_resolution_status(
            review_repository=review_repository,
            resolution_repository=resolution_repository,
            bundle=bundle,
        )
    return evidence_review_resolution_status_to_mapping(status)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record or inspect explicit human conflict resolution for an exact evidence-review set. This never authorizes send or campaign execution.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("record", "status"):
        sub = subparsers.add_parser(name)
        sub.add_argument("--bundle", required=True, type=Path)
        sub.add_argument("--review-db", required=True, type=Path)
        sub.add_argument("--resolution-db", required=True, type=Path)
        if name == "record":
            sub.add_argument("--resolution", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = _record(args) if args.command == "record" else _status(args)
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError, KeyError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
