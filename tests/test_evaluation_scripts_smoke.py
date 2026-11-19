"""Smoke tests for offline evaluation scripts.

These scripts had no pytest coverage, so a stale script (for example one that
no longer satisfies a domain invariant) could fail unnoticed. Each script is
executed in-process and must complete and print its report. Scripts that need
network access or external credentials are deliberately excluded.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

OFFLINE_EVALUATION_SCRIPTS = (
    "evaluate_company_enrichment",
    "evaluate_contact_discovery",
    "evaluate_contact_validation",
    "evaluate_discovery_coverage",
    "evaluate_entity_resolution",
    "evaluate_field_fusion",
    "evaluate_gap_automation",
    "evaluate_lead_export",
    "evaluate_person_entity_resolution",
    "evaluate_person_role_discovery",
    "evaluate_repeatable_web_discovery",
    "evaluate_selective_review",
    "show_dental_icp_policy",
)


@pytest.mark.parametrize("name", OFFLINE_EVALUATION_SCRIPTS)
def test_offline_evaluation_script_runs_and_reports(name, capsys, monkeypatch):
    script = ROOT / "scripts" / f"{name}.py"
    monkeypatch.setattr(sys, "argv", [str(script)])
    runpy.run_path(str(script), run_name="__main__")
    assert capsys.readouterr().out.strip(), f"{name} produced no report"


def test_selective_review_script_matches_fixture_metrics(capsys, monkeypatch):
    script = ROOT / "scripts" / "evaluate_selective_review.py"
    monkeypatch.setattr(sys, "argv", [str(script)])
    runpy.run_path(str(script), run_name="__main__")
    out = capsys.readouterr().out
    assert "scenarios=19 tp=8 fp=0 tn=11 fn=0 high_priority=2" in out
