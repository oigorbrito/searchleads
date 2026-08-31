from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from searchleads.contact_discovery import discover_contacts_from_html
FIXTURE=ROOT/'tests'/'fixtures'/'contact_discovery_v1.json'

def main():
    scenarios=json.loads(FIXTURE.read_text(encoding='utf-8'))
    tp=fp=fn=0
    for s in scenarios:
        expected={tuple(x) for x in s['expected']}
        predicted={(x.kind.value,x.value) for x in discover_contacts_from_html(s['url'],s['html'])}
        tp += len(expected & predicted); fp += len(predicted-expected); fn += len(expected-predicted)
    precision=tp/(tp+fp) if tp+fp else 0.0
    recall=tp/(tp+fn) if tp+fn else 0.0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
    print(f'scenarios={len(scenarios)} expected_contacts={tp+fn} tp={tp} fp={fp} fn={fn}')
    print(f'precision={precision:.3f} recall={recall:.3f} f1={f1:.3f}')
if __name__=='__main__': main()
