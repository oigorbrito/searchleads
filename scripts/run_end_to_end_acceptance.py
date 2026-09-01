from __future__ import annotations
from dataclasses import asdict
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from searchleads.acceptance import load_fixture, run_end_to_end_acceptance
result = run_end_to_end_acceptance(load_fixture(ROOT / "tests" / "fixtures" / "end_to_end_acceptance_v1.json"))
summary = asdict(result)
summary["first"].pop("export_json")
summary["first"].pop("export_csv")
summary["second"].pop("export_json")
summary["second"].pop("export_csv")
print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
