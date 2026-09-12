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
from searchleads.governance_evidence_review_status import (  # noqa: E402
    consolidate_evidence_reviews,
    consolidated_evidence_review_status_to_mapping,
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
    parser = argparse.ArgumentParser(
        description=(
            "Show consolidated human-review state for one verified governance evidence bundle. "
            "Conflicts are reported, never auto-resolved. This command never authorizes send or a campaign."
        )
    )
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--db", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        bundle = _json_object(args.bundle, "bundle")
        with EvidenceReviewRepository(args.db) as repository:
            status = consolidate_evidence_reviews(repository=repository, bundle=bundle)
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError, KeyError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(consolidated_evidence_review_status_to_mapping(status), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
