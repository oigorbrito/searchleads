from __future__ import annotations
import csv, io, json, math
from dataclasses import replace
from datetime import datetime, timezone
import pytest
from searchleads.domain import *
from searchleads.lead_export import *
from searchleads.selective_review import ReviewItem, ReviewKind, ReviewPriority
NOW=datetime(2026,8,25,18,0,tzinfo=timezone.utc)

def base_bundle(**kw):
    company=Company('c1')
    s1=Source('s1','official','https://example.test','Official')
    e1=Evidence('e1','s1','https://example.test',NOW,'Olá', 'sha256:x', {'rank':1})
    e2=Evidence('e2','s1','https://example.test/people',NOW,'Pessoa', None, {})
    p1=Person('p1','c1',('e2',))
    prov_name=Provenance('prov-name','c1','legal_name',('e1',),'extract',NOW,'test')
    prov_state=Provenance('prov-state','c1','state',('e1',),'extract',NOW,'test')
    prov_fusion=Provenance('prov-fusion','c1','state',('e1',),'fuse',NOW,'test',('f-state1','f-state2'))
    prov_role=Provenance('prov-role','p1','professional_role_title',('e2',),'extract',NOW,'test')
    f_name=CandidateFact('f-name','c1','legal_name','ACME Ltda','ACME Ltda',('e1',),'prov-name',decision_class=DecisionClass.EVIDENCE_BACKED,observed_at=NOW)
    f_state1=CandidateFact('f-state1','c1','state','DF','DF',('e1',),'prov-state',confidence=.9,observed_at=NOW)
    f_state2=CandidateFact('f-state2','c1','state','DF','DF',('e1',),'prov-state',observed_at=NOW)
    f_role=CandidateFact('f-role','p1','professional_role_title','Diretora','Diretora',('e2',),'prov-role',observed_at=NOW)
    can=CanonicalFact('can-state','c1','state','DF',('f-state1','f-state2'),'prov-fusion','unanimous')
    conflict=Conflict('conf-name','c1','legal_name',('f-name','f-name2'))
    prov_name2=Provenance('prov-name2','c1','legal_name',('e1',),'extract2',NOW,'test')
    f_name2=CandidateFact('f-name2','c1','legal_name','ACME Tecnologia','ACME Tecnologia',('e1',),'prov-name2',observed_at=NOW)
    contact=ContactPoint('ct1','p1',ContactKind.EMAIL,'ana@example.test',('e2',),ContactStatus.DISCOVERED,NOW)
    lead=Lead('l1','c1',LeadStage.REVIEW,QualificationStatus.UNKNOWN,('ICP undefined',),NOW)
    review=ReviewItem('r1',ReviewKind.DATA_CONFLICT,ReviewPriority.HIGH,('c1','conf-name'),'resolve conflict',('e1',))
    data=dict(company=company,lead=lead,people=(p1,),contacts=(contact,),candidate_facts=(f_name,f_name2,f_state1,f_state2,f_role),canonical_facts=(can,),conflicts=(conflict,),provenances=(prov_name,prov_name2,prov_state,prov_fusion,prov_role),sources=(s1,),evidence=(e1,e2),review_items=(review,))
    data.update(kw)
    return LeadExportBundle(**data)

def test_sections_and_clean_model_shape():
    data=to_export_dict(base_bundle())
    assert set(data)=={'schema_version','company','lead','people','contacts','candidate_facts','canonical_facts','conflicts','provenances','sources','evidence','review_items'}
    assert data['schema_version']==SCHEMA_VERSION
    assert data['people'][0]['person_id']=='p1'
    assert data['candidate_facts'][-1]['subject_id'] in {'c1','p1'}

def test_json_deterministic_unicode_and_input_order_independent():
    b=base_bundle(); a=export_json(b)
    shuffled=replace(b,candidate_facts=tuple(reversed(b.candidate_facts)),provenances=tuple(reversed(b.provenances)),evidence=tuple(reversed(b.evidence)))
    assert export_json(shuffled)==a
    assert 'Olá' in a and json.loads(a)['company']['company_id']=='c1'

def test_csv_one_row_and_audit_cells():
    text=export_csv(base_bundle()); rows=list(csv.DictReader(io.StringIO(text)))
    assert len(rows)==1 and rows[0]['company_id']=='c1' and rows[0]['lead_stage']=='REVIEW'
    assert json.loads(rows[0]['facts'])['canonical'][0]['fact_id']=='can-state'
    assert json.loads(rows[0]['provenances'])[0]['provenance_id'].startswith('prov-')

def test_company_without_lead_exports():
    b=base_bundle(lead=None)
    data=to_export_dict(b); assert data['lead'] is None
    row=next(csv.DictReader(io.StringIO(export_csv(b))))
    assert row['lead_id']==row['lead_stage']==row['qualification_status']==''

def test_bytes_sets_and_enums_are_deterministic():
    b=base_bundle(); e=b.evidence[0]
    e3=replace(e,evidence_id='e3',metadata={'payload':b'\x00\xff','tags':{'b','a'},'status':ContactStatus.DISCOVERED})
    b=replace(b,evidence=b.evidence+(e3,))
    data=to_export_dict(b); meta=next(x for x in data['evidence'] if x['evidence_id']=='e3')['metadata']
    assert meta['payload']=={'encoding':'hex','value':'00ff'} and meta['tags']==['a','b'] and meta['status']=='DISCOVERED'

def test_bad_primitive_types_rejected():
    class X: pass
    b=base_bundle(); e=replace(b.evidence[0],metadata={'x':X()}); b=replace(b,evidence=(e,b.evidence[1]))
    with pytest.raises(TypeError,match='unsupported export value type'): export_json(b)

def test_non_string_mapping_key_rejected():
    b=base_bundle(); e=replace(b.evidence[0],metadata={1:'x'}); b=replace(b,evidence=(e,b.evidence[1]))
    with pytest.raises(TypeError,match='mapping keys'): export_json(b)

def test_nonfinite_float_rejected():
    b=base_bundle(); e=replace(b.evidence[0],metadata={'x':math.nan}); b=replace(b,evidence=(e,b.evidence[1]))
    with pytest.raises(TypeError,match='non-finite'): export_json(b)

def test_naive_datetime_rejected():
    b=base_bundle(); e=replace(b.evidence[0],captured_at=NOW.replace(tzinfo=None)); b=replace(b,evidence=(e,b.evidence[1]))
    with pytest.raises(TypeError,match='naive'): export_json(b)

@pytest.mark.parametrize('field,records',[
 ('people',(Person('p1','c1',('e2',)),Person('p1','c1',('e2',)))),
 ('contacts',(ContactPoint('ct1','c1',ContactKind.EMAIL,'x@a.test',('e1',),discovered_at=NOW),ContactPoint('ct1','c1',ContactKind.EMAIL,'y@a.test',('e1',),discovered_at=NOW))),
 ('candidate_facts',None), ('canonical_facts',None), ('conflicts',None), ('provenances',None), ('sources',None), ('evidence',None), ('review_items',None),
])
def test_duplicate_ids_rejected(field,records):
    b=base_bundle()
    if records is None:
        seq=getattr(b,field); records=seq+(seq[0],)
    with pytest.raises(ValueError,match='duplicate'): to_export_dict(replace(b,**{field:records}))

def test_cross_company_lead_rejected():
    with pytest.raises(ValueError,match='lead belongs'): to_export_dict(base_bundle(lead=Lead('l2','other',created_at=NOW)))

def test_person_other_company_rejected():
    b=base_bundle(); bad=replace(b.people[0],company_id='other')
    with pytest.raises(ValueError,match='person belongs'): to_export_dict(replace(b,people=(bad,)))

def test_person_missing_relationship_evidence_rejected():
    b=base_bundle(); bad=replace(b.people[0],relationship_evidence_ids=('missing',))
    with pytest.raises(ValueError,match='person p1 references'): to_export_dict(replace(b,people=(bad,)))

def test_contact_owner_outside_bundle_rejected():
    b=base_bundle(); bad=replace(b.contacts[0],owner_id='p-missing')
    with pytest.raises(ValueError,match='contact owner'): to_export_dict(replace(b,contacts=(bad,)))

def test_contact_missing_discovery_and_validation_evidence_rejected():
    b=base_bundle(); bad=replace(b.contacts[0],discovery_evidence_ids=('missing',))
    with pytest.raises(ValueError,match='discovery references'): to_export_dict(replace(b,contacts=(bad,)))
    bad=replace(b.contacts[0],validation_evidence_ids=('missing',))
    with pytest.raises(ValueError,match='validation references'): to_export_dict(replace(b,contacts=(bad,)))

def test_candidate_wrong_subject_missing_evidence_provenance_and_mismatch_rejected():
    b=base_bundle(); fact=b.candidate_facts[0]
    with pytest.raises(ValueError,match='another entity'): to_export_dict(replace(b,candidate_facts=(replace(fact,subject_id='x'),)+b.candidate_facts[1:]))
    with pytest.raises(ValueError,match='candidate fact f-name references'): to_export_dict(replace(b,candidate_facts=(replace(fact,evidence_ids=('missing',)),)+b.candidate_facts[1:]))
    with pytest.raises(ValueError,match='candidate fact f-name references'): to_export_dict(replace(b,candidate_facts=(replace(fact,provenance_id='missing'),)+b.candidate_facts[1:]))
    wrong=replace(next(p for p in b.provenances if p.provenance_id=='prov-name'),field_name='other')
    provs=tuple(wrong if p.provenance_id=='prov-name' else p for p in b.provenances)
    with pytest.raises(ValueError,match='provenance subject/field mismatch'): to_export_dict(replace(b,provenances=provs))

def test_candidate_evidence_must_be_in_provenance():
    b=base_bundle(); fact=b.candidate_facts[0]; prov=next(p for p in b.provenances if p.provenance_id=='prov-name')
    e3=replace(b.evidence[0],evidence_id='e3')
    badfact=replace(fact,evidence_ids=('e3',));
    with pytest.raises(ValueError,match='not represented'): to_export_dict(replace(b,candidate_facts=(badfact,)+b.candidate_facts[1:], evidence=b.evidence+(e3,)))

def test_canonical_integrity_guards():
    b=base_bundle(); can=b.canonical_facts[0]
    with pytest.raises(ValueError,match='another entity'): to_export_dict(replace(b,canonical_facts=(replace(can,subject_id='x'),)))
    with pytest.raises(ValueError,match='canonical fact can-state references'): to_export_dict(replace(b,canonical_facts=(replace(can,candidate_fact_ids=('missing',)),)))
    with pytest.raises(ValueError,match='canonical fact can-state references'): to_export_dict(replace(b,canonical_facts=(replace(can,provenance_id='missing'),)))
    wrong=replace(next(p for p in b.provenances if p.provenance_id=='prov-fusion'),field_name='city')
    provs=tuple(wrong if p.provenance_id=='prov-fusion' else p for p in b.provenances)
    with pytest.raises(ValueError,match='canonical fact provenance'): to_export_dict(replace(b,provenances=provs))
    badprov=Provenance('prov-state2-city','c1','city',('e1',),'extract',NOW,'test')
    badcand=replace(next(f for f in b.candidate_facts if f.fact_id=='f-state2'),field_name='city',provenance_id='prov-state2-city')
    facts=tuple(badcand if f.fact_id=='f-state2' else f for f in b.candidate_facts)
    with pytest.raises(ValueError,match='candidate from another'): to_export_dict(replace(b,candidate_facts=facts,provenances=b.provenances+(badprov,)))

def test_conflict_integrity_guards():
    b=base_bundle(); conf=b.conflicts[0]
    with pytest.raises(ValueError,match='another entity'): to_export_dict(replace(b,conflicts=(replace(conf,subject_id='x'),)))
    with pytest.raises(ValueError,match='conflict conf-name references'): to_export_dict(replace(b,conflicts=(replace(conf,candidate_fact_ids=('missing','f-name')),)))
    badprov=Provenance('prov-name2-other','c1','other',('e1',),'extract',NOW,'test')
    bad=replace(next(f for f in b.candidate_facts if f.fact_id=='f-name2'),field_name='other',provenance_id='prov-name2-other')
    facts=tuple(bad if f.fact_id=='f-name2' else f for f in b.candidate_facts)
    with pytest.raises(ValueError,match='candidate from another'): to_export_dict(replace(b,candidate_facts=facts,provenances=b.provenances+(badprov,)))

def test_provenance_integrity_guards():
    b=base_bundle(); p=b.provenances[0]
    with pytest.raises(ValueError,match='provenance belongs'): to_export_dict(replace(b,provenances=(replace(p,subject_id='x'),)+b.provenances[1:]))
    with pytest.raises(ValueError,match='provenance .* references'): to_export_dict(replace(b,provenances=(replace(p,evidence_ids=('missing',)),)+b.provenances[1:]))
    pf=next(p for p in b.provenances if p.provenance_id=='prov-fusion')
    bad=replace(pf,derived_from_fact_ids=('missing',))
    provs=tuple(bad if p.provenance_id=='prov-fusion' else p for p in b.provenances)
    with pytest.raises(ValueError,match='derivation references'): to_export_dict(replace(b,provenances=provs))

def test_evidence_source_and_review_evidence_integrity():
    b=base_bundle(); bad=replace(b.evidence[0],source_id='missing')
    with pytest.raises(ValueError,match='evidence e1 references'): to_export_dict(replace(b,evidence=(bad,b.evidence[1])))
    review=replace(b.review_items[0],evidence_ids=('missing',))
    with pytest.raises(ValueError,match='review item r1 references'): to_export_dict(replace(b,review_items=(review,)))
