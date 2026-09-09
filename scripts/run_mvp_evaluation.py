from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from searchleads.acceptance import load_fixture, run_end_to_end_acceptance

BENCHMARK_VERSION = "end_to_end_acceptance_v1"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / f"{BENCHMARK_VERSION}.json"


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNAVAILABLE"


def _dependency_versions() -> dict[str, str]:
    try:
        import pytest

        return {"pytest": pytest.__version__}
    except ImportError:
        return {}


def _metrics(result) -> dict[str, object]:
    run = result.first
    return {
        "technical_data_path": result.technical_data_path,
        "reproducible": result.reproducible,
        "discovered_seeds": run.discovered_seeds,
        "structured_snapshots": run.structured_snapshots,
        "evidence_records": run.evidence_records,
        "canonical_facts": run.canonical_facts,
        "conflicts": run.conflicts,
        "validated_company_contacts": run.validated_company_contacts,
        "people": run.people,
        "role_facts": run.role_facts,
        "review_items": run.review_items,
        "persistence_replay_ok": run.persistence_replay_ok,
        "er_disposition": run.er_disposition,
        "live_network_smoke": result.live_network_smoke,
        "commercial_qualification": result.commercial_qualification,
        "multi_source_company_enrichment": result.multi_source_company_enrichment,
    }


def _decision(metrics: dict[str, object]) -> dict[str, object]:
    required = {
        "technical_data_path": "PASS",
        "reproducible": True,
        "persistence_replay_ok": True,
        "er_disposition": "AUTO_MATCH",
    }
    checks = {key: metrics.get(key) == expected for key, expected in required.items()}
    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "status": status,
        "decision": "ADOPT" if status == "PASS" else "REVIEW",
        "checks": checks,
        "external_gates": {
            "live_network_smoke": metrics["live_network_smoke"],
            "commercial_qualification": metrics["commercial_qualification"],
            "multi_source_company_enrichment": metrics["multi_source_company_enrichment"],
        },
    }


def run(output_root: Path = ROOT / "evaluation") -> tuple[Path, dict[str, object]]:
    fixture = load_fixture(FIXTURE_PATH)
    result = run_end_to_end_acceptance(fixture)
    metrics = _metrics(result)
    raw_results = asdict(result)
    raw_results["fixture_sha256"] = hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest()
    environment = {
        "commit_sha": _git_sha(),
        "python_version": platform.python_version(),
        "os": platform.platform(),
        "dependency_versions": _dependency_versions(),
        "benchmark_version": BENCHMARK_VERSION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    config = {"fixture": str(FIXTURE_PATH.relative_to(ROOT)), "benchmark_version": BENCHMARK_VERSION}
    decision = _decision(metrics)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = output_root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    for name, value in {
        "environment.json": environment,
        "config.json": config,
        "raw_results.json": raw_results,
        "metrics.json": metrics,
        "decision.json": decision,
    }.items():
        (run_dir / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    baseline = {
        "commit": environment["commit_sha"],
        "benchmark_version": BENCHMARK_VERSION,
        "metrics": metrics,
        "environment": environment,
        "status": "BASELINE",
        "run_id": run_id,
    }
    (output_root / "baseline.json").write_text(json.dumps(baseline, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"run": str(run_dir), "status": decision["status"], "exit_code": 0 if decision["status"] == "PASS" else 1}, ensure_ascii=False, sort_keys=True))
    return run_dir, decision


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the deterministic SearchLeads MVP evaluation.")
    parser.add_argument("--output-root", type=Path, default=ROOT / "evaluation")
    args = parser.parse_args()
    try:
        _, decision = run(args.output_root)
    except Exception as exc:  # The JSON artifacts remain the contract; emit a clear process failure.
        print(json.dumps({"status": "FAIL", "error": str(exc), "exit_code": 1}, ensure_ascii=False))
        return 1
    return 0 if decision["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
