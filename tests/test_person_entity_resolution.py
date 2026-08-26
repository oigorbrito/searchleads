from __future__ import annotations
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import pytest

from searchleads.domain import CandidateFact, ContactKind, ContactPoint, Person
from searchleads.person_entity_resolution import (
    EvidenceSignal, LabeledPersonPair, PersonRecord, PersonResolutionDisposition,
    compare_person_features, evaluate_experimental_auto_match, evaluate_person_resolution,
    is_experimental_profile_name_auto_candidate, person_record_from_observation, triage_person_pair,
)

ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/'tests/fixtures/person_er_v1.json').read_text())
NOW=datetime(2026,8,25,20,0,tzinfo=timezone.utc)

def sig(value, ev): return EvidenceSignal(value,(ev,))

def rec(record_id, data):
    kwargs={
        'record_id':record_id,
        'company_id':data['company'],
        'relationship_evidence_ids':(data['rel'],),
        'names':(sig(data['name'],data['rel']+'n'),),
        'roles':(sig(data['role'],data['rel']+'r'),),
    }
    if data.get('email'): kwargs['emails']=(sig(data['email'],data['rel']+'e'),)
    if data.get('phone'): kwargs['phones']=(sig(data['phone'],data['rel']+'p'),)
    if data.get('profile'): kwargs['professional_profiles']=(sig(data['profile'],data['rel']+'l'),)
    return PersonRecord(**kwargs)

def pairs():
    return tuple(LabeledPersonPair(c['id'],rec(c['id']+'L',c['left']),rec(c['id']+'R',c['right']),c['same'],c['category']) for c in DATA['pairs'])

def find(pair_id): return next(p for p in pairs() if p.pair_id==pair_id)

def test_curated_metrics_are_conservative_and_measured():
    items=pairs()
    op=evaluate_person_resolution(items)
    exp=evaluate_experimental_auto_match(items)
    assert (op.pairs,op.same_person_pairs,op.distinct_person_pairs)==(25,12,13)
    assert (op.reviews,op.insufficient)==(16,9)
    assert op.review_rate==pytest.approx(16/25) and op.insufficient_rate==pytest.approx(9/25)
    assert op.positive_review_recall==pytest.approx(10/12)
    assert (exp.candidate_matches,exp.true_positive,exp.false_positive)==(5,4,1)
    assert exp.precision==pytest.approx(4/5) and exp.recall==pytest.approx(4/12)
    assert exp.false_merge_rate==pytest.approx(1/13)

def test_profile_name_rule_is_diagnostic_and_routes_review_not_auto():
    for pid in ('p01','p02','p03','p04','n13'):
        p=find(pid)
        assert is_experimental_profile_name_auto_candidate(p.left,p.right)
        d=triage_person_pair(p.left,p.right)
        assert d.disposition is PersonResolutionDisposition.REVIEW
        assert 'auto_match_not_authorized' in d.reasons
    assert not is_experimental_profile_name_auto_candidate(find('p08').left,find('p08').right)
    assert not is_experimental_profile_name_auto_candidate(find('p09').left,find('p09').right)

def test_same_name_alone_never_forces_identity_homonyms_or_changed_snapshots():
    for pid in ('p11','p12','n01','n08'):
        assert triage_person_pair(find(pid).left,find(pid).right).disposition is PersonResolutionDisposition.INSUFFICIENT_EVIDENCE

def test_same_name_plus_weak_or_shared_signal_routes_review():
    for pid in ('p05','p06','p07','n02','n03','n04','n11'):
        assert triage_person_pair(find(pid).left,find(pid).right).disposition is PersonResolutionDisposition.REVIEW

def test_different_name_profile_or_two_contacts_routes_review():
    for pid in ('p09','p10','n06'):
        assert triage_person_pair(find(pid).left,find(pid).right).disposition is PersonResolutionDisposition.REVIEW

def test_different_name_single_shared_contact_is_insufficient():
    for pid in ('n05','n12'):
        assert triage_person_pair(find(pid).left,find(pid).right).disposition is PersonResolutionDisposition.INSUFFICIENT_EVIDENCE

def test_name_normalization_is_case_accent_whitespace_only_not_fuzzy():
    f=compare_person_features(find('p02').left,find('p02').right)
    assert f.name_exact is True
    assert compare_person_features(find('n09').left,find('n09').right).name_exact is False

def test_decision_carries_union_of_underlying_evidence():
    p=find('p05'); d=triage_person_pair(p.left,p.right)
    assert set(p.left.evidence_ids).issubset(d.evidence_ids)
    assert set(p.right.evidence_ids).issubset(d.evidence_ids)
    assert 'email_exact' in d.reasons

def test_record_builder_preserves_relationship_fact_and_contact_evidence():
    person=Person('p','c',('ev-rel',))
    name=CandidateFact('fn','p','person_name','Ana','Ana',('ev-name',),'prov',observed_at=NOW)
    role=CandidateFact('fr','p','professional_role_title','CEO','CEO',('ev-role',),'prov',observed_at=NOW)
    noise=CandidateFact('fx','other','person_name','Other','Other',('ev-x',),'prov',observed_at=NOW)
    email=ContactPoint('ce','p',ContactKind.EMAIL,'ANA@EXAMPLE.COM',('ev-email',),discovered_at=NOW,validation_evidence_ids=('ev-email-v',))
    phone=ContactPoint('cp','p',ContactKind.PHONE,'(11) 99999-0000',('ev-phone',),discovered_at=NOW)
    profile=ContactPoint('cl','p',ContactKind.PROFESSIONAL_PROFILE,'https://linkedin.com/in/ana',('ev-linkedin',),discovered_at=NOW)
    ignored=ContactPoint('ci','other',ContactKind.EMAIL,'other@example.com',('ev-other',),discovered_at=NOW)
    r=person_record_from_observation(person,candidate_facts=(noise,role,name),contacts=(ignored,profile,phone,email))
    assert [s.value for s in r.names]==['Ana'] and [s.value for s in r.roles]==['CEO']
    assert [s.value for s in r.emails]==['ANA@EXAMPLE.COM']
    assert set(r.evidence_ids)=={'ev-rel','ev-name','ev-role','ev-email','ev-email-v','ev-phone','ev-linkedin'}

def test_builder_prefers_nonblank_string_normalized_value_and_ignores_nonstring_fact():
    p=Person('p','c',('ev-rel',))
    a=CandidateFact('a','p','person_name','Raw','Norm',('ev-a',),'prov',observed_at=NOW)
    b=CandidateFact('b','p','professional_role_title','Role',' ',('ev-b',),'prov',observed_at=NOW)
    c=CandidateFact('c','p','person_name',123,None,('ev-c',),'prov',observed_at=NOW)
    r=person_record_from_observation(p,candidate_facts=(a,b,c))
    assert [s.value for s in r.names]==['Norm'] and [s.value for s in r.roles]==['Role']

def test_builder_ignores_contact_kinds_outside_person_er_signals():
    p=Person('p','c',('ev-rel',))
    other=ContactPoint('x','p',ContactKind.OTHER,'x',('ev',),discovered_at=NOW)
    assert person_record_from_observation(p,contacts=(other,)).emails==()

def test_invalid_contact_values_do_not_create_feature_overlap():
    a=PersonRecord('a','c',('ea',),names=(sig('Ana','na'),),emails=(sig('bad mail','xa'),),phones=(sig('123','pa'),),professional_profiles=(sig('https://linkedin.com/company/x','la'),))
    b=PersonRecord('b','c',('eb',),names=(sig('Bia','nb'),),emails=(sig('bad mail','xb'),),phones=(sig('123','pb'),),professional_profiles=(sig('https://linkedin.com/company/x','lb'),))
    f=compare_person_features(a,b)
    assert f.email_overlap is None and f.phone_overlap is None and f.professional_profile_overlap is None

def test_valid_contact_sets_can_be_comparable_without_overlap():
    a=PersonRecord('a','c',('ea',),emails=(sig('a@example.com','x'),),phones=(sig('11999990000','p'),),professional_profiles=(sig('https://linkedin.com/in/a','l'),))
    b=PersonRecord('b','c',('eb',),emails=(sig('b@example.com','y'),),phones=(sig('11999991111','q'),),professional_profiles=(sig('https://linkedin.com/in/b','m'),))
    f=compare_person_features(a,b)
    assert f.email_overlap is False and f.phone_overlap is False and f.professional_profile_overlap is False

def test_relationship_evidence_overlap_is_diagnostic_not_auto_authority():
    a=PersonRecord('a','c',('same',),names=(sig('Ana','na'),))
    b=PersonRecord('b','c',('same',),names=(sig('Ana','nb'),))
    f=compare_person_features(a,b)
    assert f.relationship_evidence_overlap is True
    assert triage_person_pair(a,b).disposition is PersonResolutionDisposition.INSUFFICIENT_EVIDENCE

def test_record_and_signal_invariants():
    with pytest.raises(ValueError): EvidenceSignal('',('e',))
    with pytest.raises(ValueError): EvidenceSignal('x',())
    with pytest.raises(ValueError): PersonRecord('','c',('e',))
    with pytest.raises(ValueError): PersonRecord('p','',('e',))
    with pytest.raises(ValueError): PersonRecord('p','c',())

def test_labeled_pair_invariants():
    r=PersonRecord('a','c',('e',))
    with pytest.raises(ValueError): LabeledPersonPair('',r,replace(r,record_id='b'),True,'x')
    with pytest.raises(ValueError): LabeledPersonPair('p',r,replace(r,record_id='b'),True,' ')
    with pytest.raises(ValueError): LabeledPersonPair('p',r,r,True,'x')

def test_triage_rejects_same_observation_id():
    a=PersonRecord('same','c',('e1',)); b=PersonRecord('same','c',('e2',))
    with pytest.raises(ValueError): triage_person_pair(a,b)

def test_empty_evaluation_is_well_defined():
    op=evaluate_person_resolution(())
    exp=evaluate_experimental_auto_match(())
    assert op.pairs==0 and op.review_rate==op.insufficient_rate==op.positive_review_recall==0.0
    assert exp.pairs==0 and exp.precision is None
    assert exp.recall==exp.false_merge_rate==0.0

def test_profile_normalization_rejects_bad_scheme_host_and_port():
    base=lambda rid,profile: PersonRecord(rid,'c',(rid+'e',),names=(sig('Ana',rid+'n'),),professional_profiles=(sig(profile,rid+'p'),))
    good=base('g','https://linkedin.com/in/ana')
    for i,bad_value in enumerate(('ftp://linkedin.com/in/ana','https://example.com/in/ana','https://linkedin.com:bad/in/ana')):
        f=compare_person_features(good,base(f'b{i}',bad_value))
        assert f.professional_profile_overlap is None

def test_builder_ignores_same_person_unrelated_candidate_field():
    p=Person('p','c',('ev-rel',))
    unrelated=CandidateFact('x','p','department','Finance','Finance',('ev-x',),'prov',observed_at=NOW)
    r=person_record_from_observation(p,candidate_facts=(unrelated,))
    assert r.names==() and r.roles==()
