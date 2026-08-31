from __future__ import annotations
from dataclasses import asdict
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from searchleads.person_entity_resolution import (
    EvidenceSignal, LabeledPersonPair, PersonRecord,
    evaluate_experimental_auto_match, evaluate_person_resolution,
)

def signal(value,evidence): return EvidenceSignal(value,(evidence,))
def record(record_id,data):
    kwargs=dict(record_id=record_id,company_id=data['company'],relationship_evidence_ids=(data['rel'],),
                names=(signal(data['name'],data['rel']+'n'),),roles=(signal(data['role'],data['rel']+'r'),))
    if data.get('email'): kwargs['emails']=(signal(data['email'],data['rel']+'e'),)
    if data.get('phone'): kwargs['phones']=(signal(data['phone'],data['rel']+'p'),)
    if data.get('profile'): kwargs['professional_profiles']=(signal(data['profile'],data['rel']+'l'),)
    return PersonRecord(**kwargs)

data=json.loads((ROOT/'tests/fixtures/person_er_v1.json').read_text(encoding='utf-8'))
pairs=tuple(LabeledPersonPair(c['id'],record(c['id']+'L',c['left']),record(c['id']+'R',c['right']),c['same'],c['category']) for c in data['pairs'])
print(json.dumps({
    'operational':asdict(evaluate_person_resolution(pairs)),
    'experimental_profile_name_auto_rule':asdict(evaluate_experimental_auto_match(pairs)),
    'operational_auto_match_authority':False,
    'persisted_person_merge_execution':False,
    'benchmark_is_production_accuracy':False,
},ensure_ascii=False,sort_keys=True,indent=2))
