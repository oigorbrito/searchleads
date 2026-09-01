from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src')); sys.path.insert(0,str(ROOT/'tests'))
from test_gap_automation import _scenario
CASES=json.loads((ROOT/'tests'/'fixtures'/'gap_automation_v1.json').read_text())

def main():
    scenarios=gap_tp=gap_fp=gap_fn=ready_ok=blocked_ok=0
    for case in CASES:
        scenarios += 1
        plan=_scenario(case)
        expected=case['expected_gaps']; actual=len(plan.gaps)
        gap_tp += min(expected,actual); gap_fp += max(0,actual-expected); gap_fn += max(0,expected-actual)
        ready_ok += len(plan.ready_actions)==case['expected_ready']
        blocked_ok += len(plan.blocked_actions)==case['expected_blocked']
    precision=gap_tp/(gap_tp+gap_fp) if gap_tp+gap_fp else 1.0
    recall=gap_tp/(gap_tp+gap_fn) if gap_tp+gap_fn else 1.0
    print(f'scenarios={scenarios} gap_tp={gap_tp} gap_fp={gap_fp} gap_fn={gap_fn}')
    print(f'gap_precision={precision:.3f} gap_recall={recall:.3f} ready_routing_exact={ready_ok}/{scenarios} blocked_routing_exact={blocked_ok}/{scenarios}')
if __name__=='__main__': main()
