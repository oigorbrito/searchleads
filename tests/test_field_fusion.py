from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from searchleads.domain import CandidateFact, CanonicalFact, Conflict, DecisionClass, Evidence, Provenance, Source
from searchleads.field_fusion import (
    ACTIVITY, AGENT, RESOLUTION_METHOD, FusionOutcome, FusionStatus,
    fuse_candidate_facts, fuse_persisted_candidates, naive_majority_value, persist_fusion_outcome,
)
from searchleads.persistence import SQLiteRepository

T1=datetime(2026,8,25,1,0,tzinfo=timezone.utc)
T2=datetime(2026,8,25,1,1,tzinfo=timezone.utc)
FIXTURE=Path(__file__).parent/'fixtures'/'field_fusion_v1.json'

def fact(fid:str,value,*,normalized=None,evidence='ev-1',at=T1,subject='company-1',field='legal_name'):
    return CandidateFact(fid,subject,field,value,normalized,(evidence,),f'prov:{fid}',observed_at=at)

def test_empty_is_explicit():
    out=fuse_candidate_facts([])
    assert out.status is FusionStatus.EMPTY and out.subject_id is None and out.supports==()
    assert persist_fusion_outcome(SQLiteRepository(),out)==()

def test_empty_outcome_rejects_derived_data():
    with pytest.raises(ValueError): FusionOutcome(FusionStatus.EMPTY,'c',None,())

def test_nonempty_outcome_requires_shape():
    with pytest.raises(ValueError): FusionOutcome(FusionStatus.CONFLICT,None,'x',())
    with pytest.raises(ValueError): FusionOutcome(FusionStatus.CANONICAL,'c','x',(object(),))

def test_conflict_outcome_rejects_canonical_shape():
    dummy=Conflict('c','s','f',('a','b'))
    with pytest.raises(ValueError): FusionOutcome(FusionStatus.CONFLICT,'s','f',(object(),),canonical_fact=object(),conflict=dummy)

def test_single_candidate_canonicalizes():
    out=fuse_candidate_facts([fact('f1','ACME')])
    assert out.status is FusionStatus.CANONICAL
    assert out.canonical_fact.value=='ACME'
    assert out.canonical_fact.candidate_fact_ids==('f1',)
    assert out.diagnostic_majority_ratio==1.0

def test_unanimous_uses_effective_normalized_value():
    a=fact('f1',' ACME ',normalized='ACME',evidence='e1')
    b=fact('f2','ACME',normalized='ACME',evidence='e2',at=T2)
    out=fuse_candidate_facts([a,b])
    assert out.canonical_fact.value=='ACME'
    assert a.raw_value==' ACME '
    assert out.provenance.evidence_ids==('e1','e2')
    assert out.provenance.generated_at==T2

def test_fusion_provenance_derives_from_all_candidates():
    out=fuse_candidate_facts([fact('b','X',evidence='e2'),fact('a','X',evidence='e1')])
    assert out.provenance.derived_from_fact_ids==('a','b')
    assert out.provenance.activity==ACTIVITY and out.provenance.agent==AGENT
    assert out.canonical_fact.provenance_id==out.provenance.provenance_id
    assert out.canonical_fact.resolution_method==RESOLUTION_METHOD
    assert out.canonical_fact.decision_class is DecisionClass.ENGINEERING_CHOICE

def test_disagreement_stays_open_conflict():
    out=fuse_candidate_facts([fact('f1','A'),fact('f2','B',evidence='e2')])
    assert out.status is FusionStatus.CONFLICT
    assert out.canonical_fact is None and out.provenance is None
    assert out.conflict.candidate_fact_ids==('f1','f2')
    assert out.conflict.status.value=='OPEN'

def test_majority_is_diagnostic_only():
    items=[fact('f1','OLD'),fact('f2','OLD',evidence='e2'),fact('f3','OLD',evidence='e3'),fact('f4','NEW',evidence='e4')]
    out=fuse_candidate_facts(items)
    assert out.status is FusionStatus.CONFLICT
    assert out.diagnostic_majority_value=='OLD' and out.diagnostic_majority_ratio==.75
    assert naive_majority_value(items)==('OLD',.75)

def test_naive_majority_empty(): assert naive_majority_value([])==(None,0.0)

def test_tie_is_deterministic_but_not_truth():
    items=[fact('f1','B'),fact('f2','A',evidence='e2')]
    value,ratio=naive_majority_value(items)
    assert value=='A' and ratio==.5
    assert fuse_candidate_facts(items).status is FusionStatus.CONFLICT

def test_heterogeneous_subject_rejected():
    with pytest.raises(ValueError): fuse_candidate_facts([fact('f1','A'),fact('f2','A',subject='company-2')])

def test_heterogeneous_field_rejected():
    with pytest.raises(ValueError): fuse_candidate_facts([fact('f1','A'),fact('f2','A',field='state')])

def test_duplicate_fact_id_rejected():
    with pytest.raises(ValueError): fuse_candidate_facts([fact('same','A'),fact('same','A',evidence='e2')])

def test_ids_independent_of_input_order():
    a,b=fact('a','X',evidence='e1'),fact('b','X',evidence='e2')
    one,two=fuse_candidate_facts([a,b]),fuse_candidate_facts([b,a])
    assert one.canonical_fact.fact_id==two.canonical_fact.fact_id
    assert one.provenance.provenance_id==two.provenance.provenance_id

def test_structured_values_have_stable_support_grouping():
    v1={'a':[1,2],'b':b'\x01'}; v2={'b':b'\x01','a':[1,2]}
    out=fuse_candidate_facts([fact('a',v1),fact('b',v2,evidence='e2')])
    assert out.status is FusionStatus.CANONICAL and out.supports[0].support_count==2

def test_datetime_and_tuple_values_are_supported():
    v=(T1,['x'])
    assert fuse_candidate_facts([fact('a',v),fact('b',v,evidence='e2')]).status is FusionStatus.CANONICAL

def test_unsupported_value_type_is_explicit():
    with pytest.raises(TypeError): fuse_candidate_facts([fact('a',{1,2})])

def seed(repository:SQLiteRepository, items:list[CandidateFact]):
    repository.save(Source('src','dataset','x'))
    for item in items:
        repository.save(Evidence(item.evidence_ids[0],'src',item.evidence_ids[0],item.observed_at,'raw'))
        repository.save(Provenance(item.provenance_id,item.subject_id,item.field_name,item.evidence_ids,'extract',item.observed_at))
        repository.save(item)

def test_persist_canonical_saves_provenance_before_canonical():
    items=[fact('f1','A',evidence='e1'),fact('f2','A',evidence='e2')]
    repo=SQLiteRepository(); seed(repo,items); out=fuse_candidate_facts(items)
    assert persist_fusion_outcome(repo,out)==(True,True)
    assert repo.load(Provenance,out.provenance.provenance_id)==out.provenance
    assert repo.load(CanonicalFact,out.canonical_fact.fact_id)==out.canonical_fact
    assert persist_fusion_outcome(repo,out)==(False,False)

def test_persist_conflict_does_not_create_provenance():
    items=[fact('f1','A',evidence='e1'),fact('f2','B',evidence='e2')]
    repo=SQLiteRepository(); seed(repo,items); out=fuse_candidate_facts(items)
    assert persist_fusion_outcome(repo,out)==(True,)
    assert repo.load(Conflict,out.conflict.conflict_id)==out.conflict

def test_fuse_persisted_candidates_and_missing_id():
    items=[fact('f1','A',evidence='e1'),fact('f2','A',evidence='e2')]
    repo=SQLiteRepository(); seed(repo,items)
    assert fuse_persisted_candidates(repo,['f2','f1']).canonical_fact.value=='A'
    with pytest.raises(ValueError,match='missing candidate fact'): fuse_persisted_candidates(repo,['missing'])

def scenario_facts(scenario):
    return [fact(f"{scenario['scenario_id']}:f:{i}",c['raw'],normalized=c['normalized'],evidence=c['evidence']) for i,c in enumerate(scenario['candidates'],1)]

def test_benchmark_conservative_policy_exact_numbers():
    scenarios=json.loads(FIXTURE.read_text(encoding='utf-8'))
    auto=correct=false=conflicts=known=0
    for s in scenarios:
        expected=s['expected_value']; known += expected is not None
        out=fuse_candidate_facts(scenario_facts(s))
        if out.status is FusionStatus.CANONICAL:
            auto+=1
            if expected is not None and out.canonical_fact.value==expected: correct+=1
            else: false+=1
        else: conflicts+=1
    assert (len(scenarios),known,auto,correct,false,conflicts)==(32,28,18,18,0,14)
    assert correct/auto==1.0 and correct/known==pytest.approx(18/28)

def test_benchmark_majority_exact_failure_numbers():
    scenarios=json.loads(FIXTURE.read_text(encoding='utf-8'))
    correct=wrong=correlated=tie_overclaim=0
    for s in scenarios:
        value,_=naive_majority_value(scenario_facts(s)); expected=s['expected_value']
        if expected is not None and value==expected: correct+=1
        else: wrong+=1
        if s['category']=='majority_wrong_correlated' and value!=expected: correlated+=1
        if s['category']=='unresolved_tie' and value is not None: tie_overclaim+=1
    assert (correct,wrong,correlated,tie_overclaim)==(24,8,4,4)
    assert correct/32==.75 and correct/28==pytest.approx(24/28)
