from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src')); sys.path.insert(0,str(ROOT/'tests'))
from test_contact_validation import _bench
FIXTURE=ROOT/'tests'/'fixtures'/'contact_validation_v1.json'

def main():
    cases=json.loads(FIXTURE.read_text(encoding='utf-8')); tp=fp=tn=fn=0
    for case in cases:
        predicted=_bench(case); expected=case['expected_validated']
        if expected and predicted: tp+=1
        elif predicted: fp+=1
        elif expected: fn+=1
        else: tn+=1
    precision=tp/(tp+fp) if tp+fp else 0.0; recall=tp/(tp+fn) if tp+fn else 0.0
    print(f'scenarios={len(cases)} tp={tp} fp={fp} tn={tn} fn={fn}')
    print(f'auto_validation_precision={precision:.3f} auto_validation_recall={recall:.3f} false_validation_rate={fp/(fp+tn):.3f}')
if __name__=='__main__': main()
