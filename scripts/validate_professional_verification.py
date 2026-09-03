from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from searchleads.professional_verification_io import (  # noqa: E402
    professional_verification_from_mapping,
    professional_verification_to_mapping,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate and canonicalize a reviewed professional verification payload."
    )
    parser.add_argument("payload", type=Path, help="Path to a JSON verification payload")
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.payload.read_text(encoding="utf-8"))
        record = professional_verification_from_mapping(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2

    canonical = professional_verification_to_mapping(record)
    print(json.dumps(canonical, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
