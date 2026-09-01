from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from searchleads.repeatable_discovery import measure_serpro_snapshot_coverage, reference_from_mapping

fixture = json.loads((ROOT / "tests" / "fixtures" / "discovery_coverage_v1.json").read_text())
reference = reference_from_mapping(fixture)
result = measure_serpro_snapshot_coverage(reference, fixture["snapshot_html"])
summary = asdict(result)
summary["source_reported_localities"] = fixture["source_reported_localities"]
summary["coverage_denominator"] = "visible headquarters/regional blocks with explicit CNPJ labels"
summary["market_coverage_claimed"] = False
summary["live_source_accessibility_measured"] = False
print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
