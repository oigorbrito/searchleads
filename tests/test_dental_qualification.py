from dataclasses import replace
from datetime import datetime, timezone
import pytest

from searchleads.domain import CandidateFact, CanonicalFact, Conflict, ConflictStatus, ContactKind, ContactPoint, ContactStatus, Person, QualificationStatus, LeadStage
from searchleads.qualification import DentalFit, DentalIntent, DentalOfferTrack, DentalPriority, materialize_lead, qualify_dental_person
from searchleads.qualification_policy import APPROVED_DENTAL_ICP_POLICY_V1

NOW=datetime(2026,8,25,22,30,tzinfo=timezone.utc)

def person(pid='p', company='c'):
    return Person(pid,company,('rel-evidence',))

def fact(fid,subject,field,value,normalized=None,evidence=None):
    return CandidateFact(fid,subject,field,value,normalized,(evidence or 'ev-'+fid,), 'prov-'+fid, observed_at=NOW)

def canonical(fid,subject,field,value,candidate_ids):
    return CanonicalFact(fid,subject,field,value,tuple(candidate_ids),'prov-'+fid,'unanimous')

def contact(cid,owner,status=ContactStatus.DISCOVERED):
    validation=('ev-v-'+cid,) if status is ContactStatus.VALIDATED else ()
    validated_at=NOW if status is ContactStatus.VALIDATED else None
    return ContactPoint(cid,owner,ContactKind.EMAIL,cid+'@example.com',('ev-d-'+cid,),status,NOW,validation,validated_at)

def qualify(*facts, offer=DentalOfferTrack.CEOF_SPECIALIZATION, conflicts=(), contacts=(), require_contact=False, p=None, canonicals=()):
    p=p or person()
    return qualify_dental_person(p,candidate_facts=facts,canonical_facts=canonicals,conflicts=conflicts,contacts=contacts,offer_track=offer,require_validated_contact=require_contact)

def br_state(fid='state', subject='c', value='PR'):
    return fact(fid,subject,'state',value)

def test_high_fit_bucomax_missing_intent_is_qualified_p2():
    d=qualify(fact('r','p','professional_role_title','Cirurgião Bucomaxilofacial'),br_state())
    assert (d.qualification_status,d.fit,d.intent,d.priority)==(QualificationStatus.QUALIFIED,DentalFit.HIGH,DentalIntent.UNKNOWN,DentalPriority.P2)
    assert d.evidence_ids==('ev-r','ev-state','rel-evidence')


def test_general_dentist_without_facial_signal_is_medium_p3():
    d=qualify(fact('r','p','professional_role_title','Cirurgião-Dentista'),br_state())
    assert (d.qualification_status,d.fit,d.priority)==(QualificationStatus.QUALIFIED,DentalFit.MEDIUM,DentalPriority.P3)


def test_facial_relevance_raises_general_dentist_to_high():
    d=qualify(fact('r','p','professional_role_title','Dentista'),fact('p1','p','procedure','Blefaroplastia'),br_state())
    assert d.fit is DentalFit.HIGH and d.priority is DentalPriority.P2


def test_high_and_medium_intent_mapping_and_priority():
    high=qualify(fact('r','p','professional_role_title','Dentista'),fact('i','p','education_intent','COURSE_INTEREST'),br_state())
    medium=qualify(fact('r2','p','professional_role_title','Harmonização Orofacial'),fact('i2','p','education_intent','CONTINUING_EDUCATION'),br_state('s2'))
    assert (high.intent,high.priority)==(DentalIntent.HIGH,DentalPriority.P2)
    assert (medium.intent,medium.priority)==(DentalIntent.MEDIUM,DentalPriority.P2)


def test_explicit_no_interest_does_not_disqualify_fit():
    d=qualify(fact('r','p','professional_role_title','HOF'),fact('i','p','education_intent','EXPLICIT_NO_INTEREST'),br_state())
    assert d.qualification_status is QualificationStatus.QUALIFIED
    assert d.intent is DentalIntent.LOW and d.priority is DentalPriority.P3


def test_conflicting_intent_becomes_unknown_not_low_or_high():
    d=qualify(fact('r','p','professional_role_title','Dentista'),fact('i1','p','education_intent','EXPLICIT_NO_INTEREST'),fact('i2','p','education_intent','COURSE_INTEREST'),br_state())
    assert d.intent is DentalIntent.UNKNOWN


def test_missing_title_is_unknown_review():
    d=qualify(br_state())
    assert (d.qualification_status,d.fit,d.priority)==(QualificationStatus.UNKNOWN,DentalFit.UNKNOWN,DentalPriority.REVIEW)


def test_explicit_non_dental_title_is_not_qualified():
    d=qualify(fact('r','p','professional_role_title','Software Engineer'),br_state())
    assert (d.qualification_status,d.fit,d.priority)==(QualificationStatus.NOT_QUALIFIED,DentalFit.LOW,DentalPriority.EXCLUDE)


def test_missing_geography_is_unknown_and_non_brazil_is_excluded():
    missing=qualify(fact('r','p','professional_role_title','Dentista'))
    foreign=qualify(fact('r2','p','professional_role_title','Dentista'),fact('country','c','country','US'))
    assert missing.qualification_status is QualificationStatus.UNKNOWN
    assert foreign.qualification_status is QualificationStatus.NOT_QUALIFIED


def test_brazil_country_or_state_satisfies_geography():
    by_country=qualify(fact('r','p','professional_role_title','Dentista'),fact('country','c','country','Brasil'))
    by_state=qualify(fact('r2','p','professional_role_title','Dentista'),br_state('state2',value='SP'))
    assert by_country.qualification_status is QualificationStatus.QUALIFIED
    assert by_state.qualification_status is QualificationStatus.QUALIFIED


def test_conflicting_country_semantics_are_unknown():
    d=qualify(fact('r','p','professional_role_title','Dentista'),fact('c1','c','country','BR'),fact('c2','c','country','US'))
    assert d.qualification_status is QualificationStatus.UNKNOWN


def test_open_required_conflict_for_title_or_geo_forces_unknown_and_preserves_refs():
    a=fact('a','p','professional_role_title','Dentista'); b=fact('b','p','professional_role_title','Software Engineer')
    c=Conflict('conf','p','professional_role_title',('a','b'),ConflictStatus.OPEN)
    d=qualify(a,b,br_state(),conflicts=(c,))
    assert d.qualification_status is QualificationStatus.UNKNOWN
    assert d.conflict_ids==('conf',) and {'a','b'}.issubset(d.candidate_fact_ids)
    assert {'ev-a','ev-b'}.issubset(d.evidence_ids)


def test_resolved_conflict_does_not_block_and_canonical_value_wins():
    a=fact('a','p','professional_role_title','Dentista'); b=fact('b','p','professional_role_title','Software Engineer')
    c=Conflict('conf','p','professional_role_title',('a','b'),ConflictStatus.RESOLVED,'a')
    can=canonical('can','p','professional_role_title','Dentista',('a',))
    d=qualify(a,b,br_state(),conflicts=(c,),canonicals=(can,))
    assert d.qualification_status is QualificationStatus.QUALIFIED
    assert d.canonical_fact_ids==('can',)


def test_open_intent_conflict_only_changes_intent_not_fit_status():
    r=fact('r','p','professional_role_title','HOF'); i1=fact('i1','p','education_intent','COURSE_INTEREST'); i2=fact('i2','p','education_intent','EXPLICIT_NO_INTEREST')
    c=Conflict('ci','p','education_intent',('i1','i2'),ConflictStatus.OPEN)
    d=qualify(r,i1,i2,br_state(),conflicts=(c,))
    assert d.qualification_status is QualificationStatus.QUALIFIED and d.fit is DentalFit.HIGH
    assert d.intent is DentalIntent.UNKNOWN and d.conflict_ids==('ci',)


def test_complementary_ceof_requires_explicit_ceof_title():
    ok=qualify(fact('r','p','professional_role_title','Especialista em Cirurgia Estética Orofacial - CEOF'),br_state(),offer=DentalOfferTrack.COMPLEMENTARY_EXCLUSIVE_CEOF)
    hof=qualify(fact('r2','p','professional_role_title','Especialista em Harmonização Orofacial'),br_state('s2'),offer=DentalOfferTrack.COMPLEMENTARY_EXCLUSIVE_CEOF)
    assert ok.qualification_status is QualificationStatus.QUALIFIED
    assert hof.qualification_status is QualificationStatus.NOT_QUALIFIED and hof.priority is DentalPriority.EXCLUDE


def test_complementary_ceof_missing_required_evidence_remains_unknown():
    d=qualify(br_state(),offer=DentalOfferTrack.COMPLEMENTARY_EXCLUSIVE_CEOF)
    assert d.qualification_status is QualificationStatus.UNKNOWN


def test_validated_contact_campaign_gate_is_explicit_and_owner_scoped():
    base=(fact('r','p','professional_role_title','Dentista'),br_state())
    blocked=qualify(*base,require_contact=True,contacts=(contact('x','other',ContactStatus.VALIDATED),))
    ready=qualify(*base,require_contact=True,contacts=(contact('pcontact','p',ContactStatus.VALIDATED),))
    company_ready=qualify(*base,require_contact=True,contacts=(contact('ccontact','c',ContactStatus.VALIDATED),))
    assert blocked.qualification_status is QualificationStatus.NOT_QUALIFIED
    assert ready.qualification_status is QualificationStatus.QUALIFIED
    assert company_ready.qualification_status is QualificationStatus.QUALIFIED


def test_discovered_contact_does_not_satisfy_validated_gate():
    d=qualify(fact('r','p','professional_role_title','Dentista'),br_state(),require_contact=True,contacts=(contact('x','p'),))
    assert d.qualification_status is QualificationStatus.NOT_QUALIFIED


def test_canonical_fact_evidence_is_traced_through_parent_candidate():
    a=fact('a','p','professional_role_title','Dentista',evidence='source-role')
    can=canonical('can','p','professional_role_title','Dentista',('a',))
    d=qualify(a,br_state(),canonicals=(can,))
    assert 'source-role' in d.evidence_ids and 'can' in d.canonical_fact_ids


def test_normalized_candidate_value_is_used_when_present():
    d=qualify(fact('r','p','professional_role_title','raw unknown','Dentista'),br_state())
    assert d.qualification_status is QualificationStatus.QUALIFIED


def test_empty_normalized_candidate_falls_back_to_raw():
    d=qualify(fact('r','p','professional_role_title','Dentista',' '),br_state())
    assert d.qualification_status is QualificationStatus.QUALIFIED


def test_duplicate_equivalent_values_do_not_create_ambiguity():
    d=qualify(fact('r1','p','professional_role_title','Dentista'),fact('r2','p','professional_role_title','DENTISTA'),br_state())
    assert d.qualification_status is QualificationStatus.QUALIFIED



def test_dental_specialty_pattern_is_eligible_and_high_high_is_p1():
    specialist=qualify(fact('r','p','professional_role_title','Especialista em Endodontia'),br_state())
    top=qualify(fact('r2','p','professional_role_title','HOF'),fact('i','p','education_intent','PROCEDURE_LEARNING'),br_state('s2'))
    assert specialist.qualification_status is QualificationStatus.QUALIFIED and specialist.fit is DentalFit.MEDIUM
    assert top.priority is DentalPriority.P1


def test_invalid_offer_track_is_rejected():
    with pytest.raises(ValueError):
        qualify_dental_person(person(), candidate_facts=(fact('r','p','professional_role_title','Dentista'),br_state()), offer_track=object())

def test_materialize_lead_preserves_company_status_stage_and_audit_reasons():
    d=qualify(fact('r','p','professional_role_title','Dentista'),br_state())
    lead=materialize_lead(d,created_at=NOW)
    assert lead.company_id=='c' and lead.stage is LeadStage.QUALIFIED and lead.qualification_status is QualificationStatus.QUALIFIED
    assert 'person_id=p' in lead.qualification_reasons and 'policy_id='+APPROVED_DENTAL_ICP_POLICY_V1.policy_id in lead.qualification_reasons
    assert materialize_lead(d,created_at=NOW).lead_id==lead.lead_id


def test_materialize_unknown_and_disqualified_stages_and_custom_id():
    unknown=qualify(br_state())
    bad=qualify(fact('r','p','professional_role_title','Engineer'),br_state('s2'))
    assert materialize_lead(unknown,created_at=NOW).stage is LeadStage.REVIEW
    assert materialize_lead(bad,created_at=NOW,lead_id='custom').stage is LeadStage.DISQUALIFIED
    assert materialize_lead(bad,created_at=NOW,lead_id='custom').lead_id=='custom'


def test_materialize_rejects_naive_timestamp():
    d=qualify(fact('r','p','professional_role_title','Dentista'),br_state())
    with pytest.raises(ValueError): materialize_lead(d,created_at=datetime(2026,8,25))


def test_engine_rejects_unsupported_policy_contract():
    bad=replace(APPROVED_DENTAL_ICP_POLICY_V1, decision_basis='other')
    with pytest.raises(ValueError):
        qualify_dental_person(person(),policy=bad)
    with pytest.raises(ValueError):
        qualify_dental_person(person(),policy=object())


def test_decision_invariants_reject_unsorted_or_missing_evidence():
    d=qualify(fact('r','p','professional_role_title','Dentista'),br_state())
    with pytest.raises(ValueError): replace(d,evidence_ids=())
    with pytest.raises(ValueError): replace(d,evidence_ids=('z','a'))
    with pytest.raises(ValueError): replace(d,decision_id=' ')
