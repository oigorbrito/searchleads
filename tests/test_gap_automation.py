from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
import pytest

from searchleads.company_enrichment import OFFICIAL_URL
from searchleads.domain import CandidateFact, CanonicalFact, ContactKind, ContactPoint, ContactStatus, Lead, LeadStage, Person, QualificationStatus
from searchleads.gap_automation import ActionDisposition, ActionEffect, ActionKind, AutomationAction, AutomationInputs, AutomationPlan, Gap, GapKind, GapRequirements, detect_gaps, plan_gap_actions
from searchleads.qualification_policy import APPROVED_DENTAL_ICP_POLICY_V1

NOW=datetime(2026,8,25,18,30,tzinfo=timezone.utc)
ROOT=Path(__file__).resolve().parents[1]
CASES=json.loads((ROOT/'tests'/'fixtures'/'gap_automation_v1.json').read_text())

def canonical(field,value='x'):
    return CanonicalFact(f'can-{field}','c1',field,value,(f'cf-{field}',),f'prov-{field}','test')

def person_role():
    person=Person('p1','c1',('ev-people',))
    role=CandidateFact('f-role','p1','professional_role_title','Diretora','Diretora',('ev-people',),'prov-role',observed_at=NOW)
    return person,role

def contact(status=ContactStatus.DISCOVERED,owner='c1'):
    validation=('ev-v',) if status is ContactStatus.VALIDATED else ()
    validated_at=NOW if status is ContactStatus.VALIDATED else None
    return ContactPoint('ct',owner,ContactKind.EMAIL,'x@example.test',('ev-d',),status,NOW,validation,validated_at)

def _scenario(case):
    req=GapRequirements(**case['requirements']); inputs=AutomationInputs(**case.get('inputs',{}))
    canonical_facts=(); contacts=(); people=(); candidate_facts=(); lead=None
    setup=case.get('setup')
    if setup=='state_present': canonical_facts=(canonical('state','DF'),)
    elif setup=='validated_contact': contacts=(contact(ContactStatus.VALIDATED),)
    elif setup=='person_role': p,r=person_role(); people=(p,); candidate_facts=(r,)
    elif setup=='qualified_lead': lead=Lead('l1','c1',LeadStage.QUALIFIED,QualificationStatus.QUALIFIED,('policy',),NOW)
    elif setup=='unknown_lead': lead=Lead('l1','c1',LeadStage.REVIEW,QualificationStatus.UNKNOWN,('unknown',),NOW)
    return plan_gap_actions('c1',req,inputs=inputs,canonical_facts=canonical_facts,contacts=contacts,people=people,candidate_facts=candidate_facts,lead=lead)

@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_curated_planning_contract(case):
    plan=_scenario(case)
    assert len(plan.gaps)==case['expected_gaps']
    assert len(plan.ready_actions)==case['expected_ready']
    assert len(plan.blocked_actions)==case['expected_blocked']

def test_explicit_requirements_only_and_deterministic_gap_order():
    gaps=detect_gaps('c1',GapRequirements(('zeta','alpha','zeta')))
    assert [g.key for g in gaps]==['alpha','zeta']; assert detect_gaps('c1',GapRequirements())==()

def test_other_company_records_do_not_close_gaps():
    other_fact=CanonicalFact('x','other','state','DF',('cf',),'prov','x'); other_contact=contact(ContactStatus.VALIDATED,'other')
    other_person=Person('p-other','other',('ev',)); role=CandidateFact('role','p-other','professional_role_title','CEO','CEO',('ev',),'prov',observed_at=NOW)
    lead=Lead('lead','other',LeadStage.QUALIFIED,QualificationStatus.QUALIFIED,(),NOW)
    gaps=detect_gaps('c1',GapRequirements(('state',),True,True,True),canonical_facts=(other_fact,),contacts=(other_contact,),people=(other_person,),candidate_facts=(role,),lead=lead)
    assert {g.kind for g in gaps}==set(GapKind)

def test_role_and_contact_scope_guards():
    p=Person('p1','c1',('ev',)); name=CandidateFact('name','p1','person_name','Ana','Ana',('ev',),'prov',observed_at=NOW)
    assert detect_gaps('c1',GapRequirements(require_person_role=True),people=(p,),candidate_facts=(name,))[0].kind is GapKind.PERSON_ROLE
    role=CandidateFact('role','ghost','professional_role_title','CEO','CEO',('ev',),'prov',observed_at=NOW)
    assert detect_gaps('c1',GapRequirements(require_person_role=True),candidate_facts=(role,))[0].kind is GapKind.PERSON_ROLE
    assert detect_gaps('c1',GapRequirements(require_validated_company_contact=True),contacts=(contact(ContactStatus.VALIDATED,'p1'),))[0].kind is GapKind.VALIDATED_COMPANY_CONTACT

def test_brasilapi_and_location_actions_are_bounded_prerequisites():
    a=plan_gap_actions('c1',GapRequirements(('state',)),inputs=AutomationInputs(known_cnpj='33.683.111/0002-80')).ready_actions[0]
    assert a.action_kind is ActionKind.BRASILAPI_POINT_LOOKUP and a.effect is ActionEffect.PREREQUISITE and a.locator.endswith('/33683111000280') and a.input_ids==('33683111000280',) and (a.retry_max_attempts,a.min_interval_seconds)==(3,60)
    b=plan_gap_actions('c1',GapRequirements(('postal_code',)),inputs=AutomationInputs(known_cnpj='33.683.111/0002-80')).ready_actions[0]
    assert b.action_kind is ActionKind.OFFICIAL_COMPANY_LOCATION_INGEST and b.locator==OFFICIAL_URL and b.input_ids==('33683111000280',)

def test_all_location_fields_and_missing_cnpj():
    plan=plan_gap_actions('c1',GapRequirements(('street_address','postal_code','activity_start_date')),inputs=AutomationInputs(known_cnpj='33683111000280'))
    assert len(plan.ready_actions)==3 and {a.action_kind for a in plan.ready_actions}=={ActionKind.OFFICIAL_COMPANY_LOCATION_INGEST}
    for field in ('street_address','postal_code','activity_start_date'):
        assert 'requires an explicit known CNPJ' in plan_gap_actions('c1',GapRequirements((field,))).blocked_actions[0].reason

def test_network_and_local_actions():
    inputs=AutomationInputs(company_contact_page_urls=('https://EXAMPLE.test:443/contact#x','https://example.test/contact'))
    action=plan_gap_actions('c1',GapRequirements(require_validated_company_contact=True),inputs=inputs).actions[0]
    assert action.locator=='https://example.test/contact' and action.retry_max_attempts==3
    action=plan_gap_actions('c1',GapRequirements(require_validated_company_contact=True),inputs=AutomationInputs(validation_contact_ids=('ct-b','ct-a','ct-b'))).ready_actions[0]
    assert action.action_kind is ActionKind.CONTACT_PUBLICATION_VALIDATION and action.effect is ActionEffect.DIRECT and action.input_ids==('ct-a','ct-b') and (action.retry_max_attempts,action.min_interval_seconds)==(1,0)
    action=plan_gap_actions('c1',GapRequirements(require_person_role=True),inputs=AutomationInputs(people_page_url='https://EXAMPLE.test:443/people#team')).ready_actions[0]
    assert action.action_kind is ActionKind.PERSON_ROLE_PAGE_INGEST and action.locator=='https://example.test/people'

def test_qualification_action_requires_explicit_person_and_exact_policy_and_is_local_direct():
    req=GapRequirements(require_qualification=True)
    assert 'explicit target Person ID' in plan_gap_actions('c1',req).blocked_actions[0].reason
    wrong=AutomationInputs(qualification_person_id='p1',qualification_policy_id='wrong')
    assert 'explicit approved dental policy ID' in plan_gap_actions('c1',req,inputs=wrong).blocked_actions[0].reason
    good=AutomationInputs(qualification_person_id='p1',qualification_policy_id=APPROVED_DENTAL_ICP_POLICY_V1.policy_id)
    action=plan_gap_actions('c1',req,inputs=good).ready_actions[0]
    assert action.action_kind is ActionKind.DENTAL_QUALIFICATION_EVALUATION and action.effect is ActionEffect.DIRECT
    assert action.input_ids==('dental-facial-surgery-education-br-v1','p1') and (action.retry_max_attempts,action.min_interval_seconds)==(1,0)

def test_blocked_action_and_idempotence():
    action=plan_gap_actions('c1',GapRequirements(('employee_count',))).blocked_actions[0]
    assert action.disposition is ActionDisposition.BLOCKED and action.action_kind is None and action.effect is ActionEffect.NONE and action.retry_max_attempts==0 and action.cache_key is None
    req=GapRequirements(('state','legal_name'),True)
    a=AutomationInputs(known_cnpj='33683111000280',company_contact_page_urls=('https://x.test/b','https://x.test/a'))
    b=AutomationInputs(known_cnpj='33683111000280',company_contact_page_urls=('https://x.test/a','https://x.test/b'))
    assert plan_gap_actions('c1',req,inputs=a)==plan_gap_actions('c1',req,inputs=b)

def test_gap_and_action_invariants():
    with pytest.raises(ValueError): Gap('',GapKind.COMPANY_FIELD,'x','why')
    with pytest.raises(ValueError): Gap('g',GapKind.COMPANY_FIELD,'','why')
    with pytest.raises(ValueError): AutomationAction('','g',ActionDisposition.BLOCKED,None,ActionEffect.NONE,'x')
    with pytest.raises(ValueError): AutomationAction('a','g',ActionDisposition.READY,None,ActionEffect.DIRECT,'x',retry_max_attempts=1,cache_key='k')
    with pytest.raises(ValueError): AutomationAction('a','g',ActionDisposition.READY,ActionKind.CONTACT_PUBLICATION_VALIDATION,ActionEffect.NONE,'x',retry_max_attempts=1,cache_key='k')
    with pytest.raises(ValueError): AutomationAction('a','g',ActionDisposition.READY,ActionKind.CONTACT_PUBLICATION_VALIDATION,ActionEffect.DIRECT,'x',input_ids=('b','a'),retry_max_attempts=1,cache_key='k')
    with pytest.raises(ValueError): AutomationAction('a','g',ActionDisposition.READY,ActionKind.CONTACT_PUBLICATION_VALIDATION,ActionEffect.DIRECT,'x',retry_max_attempts=0,cache_key='k')
    with pytest.raises(ValueError): AutomationAction('a','g',ActionDisposition.READY,ActionKind.CONTACT_PUBLICATION_VALIDATION,ActionEffect.DIRECT,'x',retry_max_attempts=1,cache_key='k',min_interval_seconds=-1)
    with pytest.raises(ValueError): AutomationAction('a','g',ActionDisposition.BLOCKED,ActionKind.BRASILAPI_POINT_LOOKUP,ActionEffect.NONE,'x')
    with pytest.raises(ValueError): AutomationAction('a','g',ActionDisposition.BLOCKED,None,ActionEffect.NONE,'x',retry_max_attempts=1)

def test_plan_invariants():
    gap=Gap('g',GapKind.COMPANY_FIELD,'x','why')
    with pytest.raises(ValueError): AutomationPlan('',GapRequirements(),(),())
    with pytest.raises(ValueError): AutomationPlan('c',GapRequirements(),(gap,gap),())
    bad=AutomationAction('a','other',ActionDisposition.BLOCKED,None,ActionEffect.NONE,'why')
    with pytest.raises(ValueError): AutomationPlan('c',GapRequirements(),(gap,),(bad,))

def test_requirements_and_inputs_validation():
    with pytest.raises(ValueError): GapRequirements(('state',' '))
    with pytest.raises(ValueError): AutomationInputs(known_cnpj='123')
    with pytest.raises(TypeError): AutomationInputs(known_cnpj=123) # type: ignore[arg-type]
    with pytest.raises(ValueError): AutomationInputs(company_contact_page_urls=(' ',))
    with pytest.raises(ValueError): AutomationInputs(company_contact_page_urls=('ftp://example.test/x',))
    with pytest.raises(ValueError): AutomationInputs(company_contact_page_urls=('https://u:p@example.test/x',))
    with pytest.raises(ValueError): AutomationInputs(company_contact_page_urls=('https://example.test:99999/x',))
    with pytest.raises(ValueError): AutomationInputs(people_page_url='relative')
    with pytest.raises(ValueError): AutomationInputs(validation_contact_ids=('ct',' '))
    with pytest.raises(ValueError): AutomationInputs(qualification_person_id=' ')
    with pytest.raises(ValueError): AutomationInputs(qualification_policy_id=' ')

def test_bad_company_and_url_guards():
    with pytest.raises(ValueError): detect_gaps(' ',GapRequirements())
    with pytest.raises(TypeError): AutomationInputs(people_page_url=123) # type: ignore[arg-type]
    inputs=AutomationInputs(people_page_url='https://Example.test:8443/people?q=1#x')
    assert plan_gap_actions('c1',GapRequirements(require_person_role=True),inputs=inputs).ready_actions[0].locator=='https://example.test:8443/people?q=1'

def test_action_blank_id_and_unsupported_kind_guards():
    with pytest.raises(ValueError): AutomationAction('a','g',ActionDisposition.READY,ActionKind.CONTACT_PUBLICATION_VALIDATION,ActionEffect.DIRECT,'x',input_ids=(' ',),retry_max_attempts=1,cache_key='k')
    from searchleads.gap_automation import planning
    class Fake: value='FAKE'
    gap=Gap('g',GapKind.COMPANY_FIELD,'state','why'); object.__setattr__(gap,'kind',Fake())
    with pytest.raises(ValueError,match='unsupported gap kind'): planning._actions_for_gap('c1',gap,AutomationInputs())
