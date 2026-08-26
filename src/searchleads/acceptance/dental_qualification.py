from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from searchleads.domain import CandidateFact, Person, QualificationStatus
from searchleads.qualification import DentalFit, DentalIntent, DentalPriority, materialize_lead, qualify_dental_person
from searchleads.qualification_policy import APPROVED_DENTAL_ICP_POLICY_V1

_FIXED_TIME=datetime(2026,8,25,22,30,tzinfo=timezone.utc)

@dataclass(frozen=True,slots=True)
class DentalCommercialAcceptance:
    policy_id:str; qualification_status:str; fit:str; intent:str; priority:str; evidence_count:int; deterministic:bool
    technical_acceptance_gate:str='SEPARATE_UNCHANGED'
    live_cfo_gate:str='NOT_EVALUATED'
    campaign_legal_gate:str='NOT_EVALUATED'

def _fact(fid,subject,field,value):
    return CandidateFact(fid,subject,field,value,None,(f'ev:{fid}',),f'prov:{fid}',observed_at=_FIXED_TIME)

def _run_once():
    person=Person('acceptance:dental:person','acceptance:dental:company',('ev:relationship',))
    facts=(
        _fact('role',person.person_id,'professional_role_title','Cirurgião Bucomaxilofacial'),
        _fact('state',person.company_id,'state','DF'),
    )
    decision=qualify_dental_person(person,candidate_facts=facts)
    lead=materialize_lead(decision,created_at=_FIXED_TIME)
    return decision,lead

def run_dental_commercial_acceptance()->DentalCommercialAcceptance:
    first_decision,first_lead=_run_once(); second_decision,second_lead=_run_once()
    deterministic=first_decision.decision_id==second_decision.decision_id and first_lead.lead_id==second_lead.lead_id and first_lead==second_lead
    if first_decision.policy_id!=APPROVED_DENTAL_ICP_POLICY_V1.policy_id: raise AssertionError('wrong policy')
    if first_decision.qualification_status is not QualificationStatus.QUALIFIED: raise AssertionError('policy path did not qualify expected fixture')
    if not deterministic: raise AssertionError('commercial policy path is not deterministic')
    return DentalCommercialAcceptance(first_decision.policy_id,first_decision.qualification_status.value,first_decision.fit.value,first_decision.intent.value,first_decision.priority.value,len(first_decision.evidence_ids),deterministic)
