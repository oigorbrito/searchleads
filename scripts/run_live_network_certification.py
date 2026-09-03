from __future__ import annotations

from dataclasses import asdict
import json

from searchleads.live_network_smoke import run_live_network_certification


def main() -> int:
    result = run_live_network_certification()
    print(json.dumps(asdict(result), sort_keys=True, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
