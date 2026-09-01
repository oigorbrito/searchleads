from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from searchleads.repeatable_discovery import discover_serpro_office_seeds
FIXTURE=ROOT/'tests'/'fixtures'/'repeatable_web_discovery_v1.json'

def main():
    data=json.loads(FIXTURE.read_text(encoding='utf-8')); cases=data['benchmark']; tp=fp=fn=0
    for case in cases:
        expected=set(case['expected']); predicted={s.cnpj for s in discover_serpro_office_seeds(case['html'])}
        tp += len(expected & predicted); fp += len(predicted-expected); fn += len(expected-predicted)
    precision=tp/(tp+fp) if tp+fp else 0.0; recall=tp/(tp+fn) if tp+fn else 0.0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
    current=discover_serpro_office_seeds(data['current_calibration']['html'])
    print(f'scenarios={len(cases)} tp={tp} fp={fp} fn={fn} precision={precision:.3f} recall={recall:.3f} f1={f1:.3f}')
    print(f'current_calibration_unique_seeds={len(current)} recipe_id=serpro_office_directory_v1')
if __name__=='__main__': main()
