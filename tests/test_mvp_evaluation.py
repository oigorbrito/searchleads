from __future__ import annotations

import json
from pathlib import Path

from scripts.run_mvp_evaluation import run
from scripts.compare_candidate import compare


def test_mvp_evaluation_persists_raw_evidence_and_decision(tmp_path: Path) -> None:
    run_dir, decision = run(tmp_path / "evaluation")
    assert decision["status"] == "PASS"
    assert json.loads((run_dir / "decision.json").read_text())["decision"] == "ADOPT"
    raw = json.loads((run_dir / "raw_results.json").read_text())
    assert raw["first"]["persistence_replay_ok"] is True
    assert (run_dir.parent.parent / "baseline.json").exists()


def test_candidate_metrics_compare_as_pass(tmp_path: Path) -> None:
    run_dir, _ = run(tmp_path / "evaluation")
    baseline = tmp_path / "evaluation" / "baseline.json"
    result = compare(baseline, run_dir / "metrics.json")
    assert result["status"] == "PASS"
    assert result["differences"] == {}
