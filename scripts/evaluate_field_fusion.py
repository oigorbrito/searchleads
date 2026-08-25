from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from searchleads.domain import CandidateFact
from searchleads.field_fusion import FusionStatus,fuse_candidate_facts,naive_majority_value
FIXTURE=ROOT/'tests'/'fixtures'/'field_fusion_v1.json'

def fact(s,i,c): return CandidateFact(f"{s['scenario_id']}:f:{i}",'company:benchmark','legal_name',c['raw'],c['normalized'],(c['evidence'],),f"prov:{s['scenario_id']}:{i}")
def main():
    scenarios=json.loads(FIXTURE.read_text(encoding='utf-8')); auto=correct=false=conflicts=maj_ok=maj_bad=corr=tie=known=0
    for s in scenarios:
        fs=[fact(s,i,c) for i,c in enumerate(s['candidates'],1)]; expected=s['expected_value']; known+=expected is not None
        out=fuse_candidate_facts(fs)
        if out.status is FusionStatus.CANONICAL:
            auto+=1; correct += expected is not None and out.canonical_fact.value==expected; false += not(expected is not None and out.canonical_fact.value==expected)
        else: conflicts+=1
        mv,_=naive_majority_value(fs)
        if expected is not None and mv==expected: maj_ok+=1
        else: maj_bad+=1
        corr += s['category']=='majority_wrong_correlated' and mv!=expected
        tie += s['category']=='unresolved_tie' and mv is not None
    print(f'scenarios={len(scenarios)} known_truth={known}')
    print(f'unanimous auto={auto} correct={correct} false={false} conflicts={conflicts} precision={correct/auto:.3f} known_truth_coverage={correct/known:.3f}')
    print(f'naive_majority correct={maj_ok} wrong_or_overclaim={maj_bad} overall_accuracy={maj_ok/len(scenarios):.3f} known_truth_accuracy={maj_ok/known:.3f}')
    print(f'correlated_wrong_majorities={corr}/4 unresolved_tie_overclaims={tie}/4')
if __name__=='__main__': main()
