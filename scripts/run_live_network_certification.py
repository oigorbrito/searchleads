from __future__ import annotations

import sys
import os
# Add src directory to PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from dataclasses import asdict
import json

from searchleads.live_network_smoke import run_live_network_certification


def main() -> int:
    result = run_live_network_certification()
    print(json.dumps(asdict(result), sort_keys=True, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
