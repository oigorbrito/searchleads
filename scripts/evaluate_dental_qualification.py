#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from searchleads.domain import CandidateFact, Conflict, ConflictStatus, ContactKind, ContactPoint, ContactStatus, Person
from searchleads.qualification import DentalOfferTrack, qualify_dental_person

ROOT=Path(__file__).resolve().parents[1]
CASES=json.loads((ROOT/'tests/fixtures/dental_qualification_v1.json').read_text())
NOW=datetime(2026,8,25,22,30,tzinfo=timezone.utc)

def cf(fid,subject,field,value):
    return CandidateFact(fid,subject,field,value,None,(f'ev:{fid}',),f'prov:{fid}',observed_at=NOW)

def evaluate_case(case):
    person=Person('p:'+case['id'],'c:'+case['id'],(f"ev:rel:{case['id']}",))
    facts=[]
    if case.get('title'): facts.append(cf('title:'+case['id'],person.person_id,'professional_role_title',case['title']))
    if case.get('alternate_title'): facts.append(cf('title2:'+case['id'],person.person_id,'professional_role_title',case['alternate_title']))
    if case.get('state'): facts.append(cf('state:'+case['id'],person.company_id,'state',case['state']))
    if case.get('country'): facts.append(cf('country:'+case['id'],person.company_id,'country',case['country']))
    if case.get('procedure'): facts.append(cf('procedure:'+case['id'],person.person_id,'procedure',case['procedure']))
    if case.get('intent'): facts.append(cf('intent:'+case['id'],person.person_id,'education_intent',case['intent']))
    if case.get('alternate_intent'): facts.append(cf('intent2:'+case['id'],person.person_id,'education_intent',case['alternate_intent']))
    conflicts=[]
    if case.get('conflict_field')=='professional_role_title': conflicts.append(Conflict('conf:'+case['id'],person.person_id,'professional_role_title',(f'title:{case["id"]}',f'title2:{case["id"]}'),ConflictStatus.OPEN))
    if case.get('conflict_field')=='education_intent': conflicts.append(Conflict('conf:'+case['id'],person.person_id,'education_intent',(f'intent:{case["id"]}',f'intent2:{case["id"]}'),ConflictStatus.OPEN))
    contacts=[]
    if case.get('validated_contact'):
        contacts.append(ContactPoint('contact:'+case['id'],person.person_id,ContactKind.EMAIL,'person@example.com',(f'ev:contact:{case["id"]}',),ContactStatus.VALIDATED,NOW,(f'ev:contact-validation:{case["id"]}',),NOW))
    decision=qualify_dental_person(person,candidate_facts=facts,conflicts=conflicts,contacts=contacts,offer_track=DentalOfferTrack(case.get('offer_track','CEOF_SPECIALIZATION')),require_validated_contact=case.get('require_validated_contact',False))
    actual=[decision.qualification_status.value,decision.fit.value,decision.intent.value,decision.priority.value]
    return actual, case['expected']

def main():
    outcomes=[evaluate_case(case) for case in CASES]
    exact=sum(actual==expected for actual,expected in outcomes)
    false_qualified=sum(actual[0]=='QUALIFIED' and expected[0]!='QUALIFIED' for actual,expected in outcomes)
    false_not_qualified=sum(actual[0]=='NOT_QUALIFIED' and expected[0]!='NOT_QUALIFIED' for actual,expected in outcomes)
    unknown_exact=sum(actual[0]=='UNKNOWN' and expected[0]=='UNKNOWN' for actual,expected in outcomes)
    expected_unknown=sum(expected[0]=='UNKNOWN' for _,expected in outcomes)
    print(f'CASES={len(outcomes)} EXACT={exact} FALSE_QUALIFIED={false_qualified} FALSE_NOT_QUALIFIED={false_not_qualified} UNKNOWN_EXACT={unknown_exact}/{expected_unknown}')
    if exact!=len(outcomes) or false_qualified or false_not_qualified: raise SystemExit(1)

if __name__=='__main__': main()
