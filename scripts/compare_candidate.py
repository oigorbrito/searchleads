from __future__ import annotations

import argparse
import json
from pathlib import Path


def compare(baseline_path: Path, candidate_path: Path) -> dict[str, object]:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    base_metrics = baseline["metrics"]
    candidate_metrics = candidate.get("metrics", candidate)
    keys = sorted(set(base_metrics) | set(candidate_metrics))
    differences = {
        key: {"baseline": base_metrics.get(key), "candidate": candidate_metrics.get(key)}
        for key in keys
        if base_metrics.get(key) != candidate_metrics.get(key)
    }
    critical = {"technical_data_path": "PASS", "reproducible": True, "persistence_replay_ok": True}
    checks = {key: candidate_metrics.get(key) == expected for key, expected in critical.items()}
    status = "PASS" if all(checks.values()) else "REGRESSION"
    return {"status": status, "differences": differences, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare an MVP candidate run with a baseline.")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    result = compare(args.baseline, args.candidate)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
