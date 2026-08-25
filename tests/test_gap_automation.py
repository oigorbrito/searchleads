from __future__ import annotations
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import pytest

from searchleads.company_enrichment import OFFICIAL_URL
from searchleads.domain import (
    CandidateFact, CanonicalFact, Company, ContactKind, ContactPoint, ContactStatus,
    Lead, LeadStage, Person, QualificationStatus,
)
from searchleads.gap_automation import (
    ActionDisposition, ActionEffect, ActionKind, AutomationAction, AutomationInputs,
    AutomationPlan, Gap, GapKind, GapRequirements, detect_gaps, plan_gap_actions,
)

NOW=datetime(2026,8,25,18,30,tzinfo=timezone.utc)
ROOT=Path(__file__).resolve().parents[1]
CASES=json.loads((ROOT/'tests'/'fixtures'/'gap_automation_v1.json').read_text())

def canonical(field, value='x'):
    return CanonicalFact(f'can-{field}','c1',field,value,(f'cf-{field}',),f'prov-{field}','test')

def person_role():
    person=Person('p1','c1',('ev-people',))
    role=CandidateFact('f-role','p1','professional_role_title','Diretora','Diretora',('ev-people',),'prov-role',observed_at=NOW)
    return person, role

def contact(status=ContactStatus.DISCOVERED, owner='c1'):
    validation=('ev-v',) if status is ContactStatus.VALIDATED else ()
    validated_at=NOW if status is ContactStatus.VALIDATED else None
    return ContactPoint('ct',owner,ContactKind.EMAIL,'x@example.test',('ev-d',),status,NOW,validation,validated_at)

def _scenario(case):
    req=GapRequirements(**case['requirements'])
    inputs=AutomationInputs(**case.get('inputs',{}))
    canonical_facts=(); contacts=(); people=(); candidate_facts=(); lead=None
    setup=case.get('setup')
    if setup=='state_present': canonical_facts=(canonical('state','DF'),)
    elif setup=='validated_contact': contacts=(contact(ContactStatus.VALIDATED),)
    elif setup=='person_role':
        p,r=person_role(); people=(p,); candidate_facts=(r,)
    elif setup=='qualified_lead': lead=Lead('l1','c1',LeadStage.QUALIFIED,QualificationStatus.QUALIFIED,('policy',),NOW)
    elif setup=='unknown_lead': lead=Lead('l1','c1',LeadStage.REVIEW,QualificationStatus.UNKNOWN,('ICP undefined',),NOW)
    return plan_gap_actions('c1',req,inputs=inputs,canonical_facts=canonical_facts,contacts=contacts,people=people,candidate_facts=candidate_facts,lead=lead)

@pytest.mark.parametrize('case', CASES, ids=lambda c:c['name'])
def test_curated_planning_contract(case):
    plan=_scenario(case)
    assert len(plan.gaps)==case['expected_gaps']
    assert len(plan.ready_actions)==case['expected_ready']
    assert len(plan.blocked_actions)==case['expected_blocked']

def test_explicit_requirements_only_and_deterministic_gap_order():
    gaps=detect_gaps('c1',GapRequirements(('zeta','alpha','zeta')))
    assert [g.key for g in gaps]==['alpha','zeta']
    assert detect_gaps('c1',GapRequirements())==()

def test_other_company_records_do_not_close_gaps():
    other_fact=CanonicalFact('x','other','state','DF',('cf',),'prov','x')
    other_contact=contact(ContactStatus.VALIDATED,owner='other')
    other_person=Person('p-other','other',('ev',))
    role=CandidateFact('role','p-other','professional_role_title','CEO','CEO',('ev',),'prov',observed_at=NOW)
    lead=Lead('lead','other',LeadStage.QUALIFIED,QualificationStatus.QUALIFIED,(),NOW)
    req=GapRequirements(('state',),True,True,True)
    gaps=detect_gaps('c1',req,canonical_facts=(other_fact,),contacts=(other_contact,),people=(other_person,),candidate_facts=(role,),lead=lead)
    assert {g.kind for g in gaps}==set(GapKind)

def test_person_without_role_does_not_close_role_gap():
    p=Person('p1','c1',('ev',))
    name=CandidateFact('name','p1','person_name','Ana','Ana',('ev',),'prov',observed_at=NOW)
    assert detect_gaps('c1',GapRequirements(require_person_role=True),people=(p,),candidate_facts=(name,))[0].kind is GapKind.PERSON_ROLE

def test_person_role_for_nonexported_person_does_not_close_gap():
    role=CandidateFact('role','ghost','professional_role_title','CEO','CEO',('ev',),'prov',observed_at=NOW)
    assert detect_gaps('c1',GapRequirements(require_person_role=True),candidate_facts=(role,))[0].kind is GapKind.PERSON_ROLE

def test_validated_person_contact_does_not_satisfy_company_contact_requirement():
    c=contact(ContactStatus.VALIDATED, owner='p1')
    assert detect_gaps('c1',GapRequirements(require_validated_company_contact=True),contacts=(c,))[0].kind is GapKind.VALIDATED_COMPANY_CONTACT

def test_brasilapi_action_is_prerequisite_and_bounded_network_work():
    action=plan_gap_actions('c1',GapRequirements(('state',)),inputs=AutomationInputs(known_cnpj='33.683.111/0002-80')).ready_actions[0]
    assert action.action_kind is ActionKind.BRASILAPI_POINT_LOOKUP
    assert action.effect is ActionEffect.PREREQUISITE
    assert action.locator.endswith('/33683111000280')
    assert action.input_ids==('33683111000280',)
    assert (action.retry_max_attempts,action.min_interval_seconds)==(3,60)
    assert action.cache_key and action.cache_key.startswith('automation-cache:v1:')

def test_official_location_action_is_prerequisite_and_bounded_network_work():
    action=plan_gap_actions('c1',GapRequirements(('postal_code',)),inputs=AutomationInputs(known_cnpj='33.683.111/0002-80')).ready_actions[0]
    assert action.action_kind is ActionKind.OFFICIAL_COMPANY_LOCATION_INGEST
    assert action.effect is ActionEffect.PREREQUISITE
    assert action.locator==OFFICIAL_URL
    assert action.input_ids==('33683111000280',)
    assert (action.retry_max_attempts,action.min_interval_seconds)==(3,60)
    assert action.cache_key and action.cache_key.startswith('automation-cache:v1:')

def test_all_official_location_fields_route_to_new_capability():
    plan=plan_gap_actions('c1',GapRequirements(('street_address','postal_code','activity_start_date')),inputs=AutomationInputs(known_cnpj='33683111000280'))
    assert len(plan.ready_actions)==3
    assert {a.action_kind for a in plan.ready_actions}=={ActionKind.OFFICIAL_COMPANY_LOCATION_INGEST}
    assert {a.locator for a in plan.ready_actions}=={OFFICIAL_URL}

def test_official_location_fields_remain_blocked_without_cnpj():
    for field in ('street_address','postal_code','activity_start_date'):
        action=plan_gap_actions('c1',GapRequirements((field,))).blocked_actions[0]
        assert 'requires an explicit known CNPJ' in action.reason

def test_network_page_actions_are_normalized_and_deduplicated():
    inputs=AutomationInputs(company_contact_page_urls=('https://EXAMPLE.test:443/contact#x','https://example.test/contact'))
    plan=plan_gap_actions('c1',GapRequirements(require_validated_company_contact=True),inputs=inputs)
    assert len(plan.actions)==1
    action=plan.actions[0]
    assert action.locator=='https://example.test/contact'
    assert action.effect is ActionEffect.PREREQUISITE and action.retry_max_attempts==3

def test_validation_action_is_local_direct_and_uses_sorted_unique_ids():
    inputs=AutomationInputs(validation_contact_ids=('ct-b','ct-a','ct-b'))
    action=plan_gap_actions('c1',GapRequirements(require_validated_company_contact=True),inputs=inputs).ready_actions[0]
    assert action.action_kind is ActionKind.CONTACT_PUBLICATION_VALIDATION
    assert action.effect is ActionEffect.DIRECT
    assert action.input_ids==('ct-a','ct-b')
    assert (action.retry_max_attempts,action.min_interval_seconds)==(1,0)

def test_people_page_action_is_prerequisite_not_identity_claim():
    action=plan_gap_actions('c1',GapRequirements(require_person_role=True),inputs=AutomationInputs(people_page_url='https://EXAMPLE.test:443/people#team')).ready_actions[0]
    assert action.action_kind is ActionKind.PERSON_ROLE_PAGE_INGEST
    assert action.effect is ActionEffect.PREREQUISITE
    assert action.locator=='https://example.test/people'

def test_blocked_action_has_no_execution_metadata():
    action=plan_gap_actions('c1',GapRequirements(('employee_count',))).blocked_actions[0]
    assert action.disposition is ActionDisposition.BLOCKED
    assert action.action_kind is None and action.effect is ActionEffect.NONE
    assert action.retry_max_attempts==0 and action.cache_key is None and action.min_interval_seconds==0

def test_qualification_remains_blocked_even_when_reason_mentions_policy():
    plan=plan_gap_actions('c1',GapRequirements(require_qualification=True))
    assert plan.blocked_actions[0].gap_id==plan.gaps[0].gap_id
    assert 'no qualification engine/ICP capability' in plan.blocked_actions[0].reason

def test_same_inputs_are_idempotent_and_input_order_independent():
    req=GapRequirements(('state','legal_name'),True)
    a=AutomationInputs(known_cnpj='33683111000280',company_contact_page_urls=('https://x.test/b','https://x.test/a'))
    b=AutomationInputs(known_cnpj='33683111000280',company_contact_page_urls=('https://x.test/a','https://x.test/b'))
    pa=plan_gap_actions('c1',req,inputs=a); pb=plan_gap_actions('c1',req,inputs=b)
    assert pa==pb

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
    with pytest.raises(TypeError): AutomationInputs(known_cnpj=123)  # type: ignore[arg-type]
    with pytest.raises(ValueError): AutomationInputs(company_contact_page_urls=(' ',))
    with pytest.raises(ValueError): AutomationInputs(company_contact_page_urls=('ftp://example.test/x',))
    with pytest.raises(ValueError): AutomationInputs(company_contact_page_urls=('https://u:p@example.test/x',))
    with pytest.raises(ValueError): AutomationInputs(company_contact_page_urls=('https://example.test:99999/x',))
    with pytest.raises(ValueError): AutomationInputs(people_page_url='relative')
    with pytest.raises(ValueError): AutomationInputs(validation_contact_ids=('ct',' '))

def test_bad_company_id_rejected():
    with pytest.raises(ValueError): detect_gaps(' ',GapRequirements())

def test_http_url_type_guard_and_nondefault_port_preserved():
    with pytest.raises(TypeError): AutomationInputs(people_page_url=123)  # type: ignore[arg-type]
    inputs=AutomationInputs(people_page_url='https://Example.test:8443/people?q=1#x')
    action=plan_gap_actions('c1',GapRequirements(require_person_role=True),inputs=inputs).ready_actions[0]
    assert action.locator=='https://example.test:8443/people?q=1'

def test_action_constructor_blank_input_id_rejected():
    with pytest.raises(ValueError): AutomationAction('a','g',ActionDisposition.READY,ActionKind.CONTACT_PUBLICATION_VALIDATION,ActionEffect.DIRECT,'x',input_ids=(' ',),retry_max_attempts=1,cache_key='k')

def test_unsupported_internal_gap_kind_guard(monkeypatch):
    from searchleads.gap_automation import planning
    class Fake:
        value='FAKE'
    gap=Gap('g',GapKind.COMPANY_FIELD,'state','why')
    object.__setattr__(gap,'kind',Fake())
    with pytest.raises(ValueError,match='unsupported gap kind'):
        planning._actions_for_gap('c1',gap,AutomationInputs())
