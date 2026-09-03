from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from searchleads.governance_decision_io import (
    campaign_authorization_from_mapping,
    campaign_authorization_to_mapping,
    compliance_signoff_from_mapping,
    compliance_signoff_to_mapping,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("compliance-signoff", "campaign-authorization"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    try:
        payload = json.loads(args.path.read_text(encoding="utf-8"))
        if args.kind == "compliance-signoff":
            record = compliance_signoff_from_mapping(payload)
            canonical = compliance_signoff_to_mapping(record)
        else:
            record = campaign_authorization_from_mapping(payload)
            canonical = campaign_authorization_to_mapping(record)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(canonical, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
