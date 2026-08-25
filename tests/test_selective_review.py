from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
import pytest

from searchleads.domain import (
    Conflict, ConflictStatus, ContactKind, ContactPoint, ContactStatus, Lead, QualificationStatus,
)
from searchleads.entity_resolution import CompanyRecord, ResolutionDisposition, TriageDecision
from searchleads.selective_review import (
    ReviewItem, ReviewKind, ReviewPriority, build_review_queue, review_company_match,
    review_conflict, review_contact, review_person_match, review_qualification,
)

ROOT=Path(__file__).parent
CASES=json.loads((ROOT/'fixtures'/'selective_review_v1.json').read_text(encoding='utf-8'))
NOW=datetime(2026,8,25,17,0,tzinfo=timezone.utc)


def route(case):
    kind=case['type']
    if kind=='company':
        decision=TriageDecision(ResolutionDisposition(case['state']),None,('domain_exact','name=0.900'))
        return review_company_match(CompanyRecord('company:a'),CompanyRecord('company:b'),decision)
    if kind=='person':
        evidence=('ev:1','ev:2') if case.get('more_evidence') else ('ev:1',)
        return review_person_match('person:a','person:b','company:1','same name/role but identity unresolved',evidence)
    if kind=='conflict':
        status=ConflictStatus(case['state'])
        selected='fact:1' if status is ConflictStatus.RESOLVED else None
        conflict=Conflict('conflict:1','company:1','legal_name',('fact:1','fact:2'),status,selected)
        return review_conflict(conflict,high_impact=case.get('high_impact',False),evidence_ids=('ev:1',))
    if kind=='contact':
        contact=ContactPoint('contact:1','company:1',ContactKind.EMAIL,'x@example.com',('ev:1',),ContactStatus(case['state']),NOW)
        return review_contact(contact)
    if kind=='lead':
        lead=Lead('lead:1','company:1',qualification_status=QualificationStatus(case['state']),qualification_reasons=('ICP unresolved',))
        return review_qualification(lead,high_value=case.get('high_value',False))
    raise AssertionError(kind)


@pytest.mark.parametrize('case',CASES,ids=lambda c:c['id'])
def test_curated_selective_review_routing(case):
    item=route(case)
    assert (item is not None) is case['expected']
    if item is not None:
        assert item.priority.value==case['priority']
        assert item.reason.strip()
        assert item.review_id.startswith('review:v1:')


def test_company_review_requires_explicit_reason_and_pair_order_is_stable():
    a,b=CompanyRecord('b'),CompanyRecord('a')
    decision=TriageDecision(ResolutionDisposition.REVIEW,None,('strong evidence',))
    item=review_company_match(a,b,decision)
    assert item.record_ids==('a','b')
    with pytest.raises(ValueError):
        review_company_match(a,b,TriageDecision(ResolutionDisposition.REVIEW,None,()))


def test_person_review_requires_distinct_people_company_reason_and_evidence():
    with pytest.raises(ValueError): review_person_match('p','p','c','ambiguous',('ev',))
    with pytest.raises(ValueError): review_person_match('p1','p2',' ','ambiguous',('ev',))
    with pytest.raises(ValueError): review_person_match('p1','p2','c','   ',('ev',))
    with pytest.raises(ValueError): review_person_match('p1','p2','c','ambiguous',())
    with pytest.raises(ValueError): review_person_match('p1','p2','c','ambiguous',(' ',))


def test_person_review_is_order_stable_and_deduplicates_evidence():
    one=review_person_match('p2','p1','c',' ambiguous   identity ',('ev2','ev1','ev2'))
    two=review_person_match('p1','p2','c','ambiguous identity',('ev1','ev2'))
    assert one==two
    assert one.evidence_ids==('ev1','ev2')


def test_conflict_records_candidate_fact_ids_and_only_open_is_reviewable():
    conflict=Conflict('conf','company','city',('f2','f1'))
    item=review_conflict(conflict,evidence_ids=('ev2','ev1','ev2'))
    assert item.record_ids==('company','conf','f1','f2')
    assert item.evidence_ids==('ev1','ev2')
    assert review_conflict(Conflict('c2','company','city',('f1','f2'),ConflictStatus.DEFERRED)) is None


def test_contact_review_preserves_discovery_and_validation_evidence_for_unknown():
    contact=ContactPoint('ct','company',ContactKind.EMAIL,'x@example.com',('ev2','ev1'),ContactStatus.UNKNOWN,NOW,('ev3','ev1'),NOW)
    item=review_contact(contact)
    assert item.evidence_ids==('ev1','ev2','ev3')


def test_qualification_without_reasons_has_explicit_fallback():
    lead=Lead('lead','company',qualification_status=QualificationStatus.UNKNOWN)
    item=review_qualification(lead,high_value=True)
    assert 'remains unresolved' in item.reason


def test_review_item_shape_invariants():
    with pytest.raises(ValueError): ReviewItem('',ReviewKind.CONTACT,ReviewPriority.NORMAL,('c',),'reason')
    with pytest.raises(ValueError): ReviewItem('r',ReviewKind.CONTACT,ReviewPriority.NORMAL,(),'reason')
    with pytest.raises(ValueError): ReviewItem('r',ReviewKind.CONTACT,ReviewPriority.NORMAL,(' ',),'reason')
    with pytest.raises(ValueError): ReviewItem('r',ReviewKind.CONTACT,ReviewPriority.NORMAL,('c',),' ')
    with pytest.raises(ValueError): ReviewItem('r',ReviewKind.CONTACT,ReviewPriority.NORMAL,('c',),'reason',(' ',))
    with pytest.raises(ValueError): ReviewItem('r',ReviewKind.CONTACT,ReviewPriority.NORMAL,('c',),'reason',('b','a'))
    with pytest.raises(ValueError): ReviewItem('r',ReviewKind.CONTACT,ReviewPriority.NORMAL,('c',),'reason',('a','a'))


def test_queue_deduplicates_merges_evidence_and_promotes_priority():
    normal=ReviewItem('r',ReviewKind.DATA_CONFLICT,ReviewPriority.NORMAL,('c','conf'),'reason',('ev1',))
    high=ReviewItem('r',ReviewKind.DATA_CONFLICT,ReviewPriority.HIGH,('c','conf'),'reason',('ev2',))
    queue=build_review_queue((normal,None,high,normal))
    assert len(queue.items)==1
    assert queue.items[0].priority is ReviewPriority.HIGH
    assert queue.items[0].evidence_ids==('ev1','ev2')
    assert queue.high_priority==1 and queue.normal_priority==0


def test_queue_orders_high_before_normal_and_reports_counts():
    normal=review_person_match('p1','p2','c','ambiguous',('ev',))
    high=review_qualification(Lead('lead','c',qualification_status=QualificationStatus.UNKNOWN),high_value=True)
    queue=build_review_queue((normal,high))
    assert [item.priority for item in queue.items]==[ReviewPriority.HIGH,ReviewPriority.NORMAL]
    assert queue.high_priority==1 and queue.normal_priority==1


def test_queue_rejects_manual_review_id_collision():
    a=ReviewItem('same',ReviewKind.CONTACT,ReviewPriority.NORMAL,('c','ct'),'reason a')
    b=ReviewItem('same',ReviewKind.CONTACT,ReviewPriority.NORMAL,('c','ct'),'reason b')
    with pytest.raises(ValueError): build_review_queue((a,b))


def test_queue_empty_is_well_defined():
    queue=build_review_queue((None,))
    assert queue.items==() and queue.high_priority==0 and queue.normal_priority==0

def test_internal_item_builder_defensively_rejects_blank_record_id():
    from searchleads.selective_review.routing import _make_item
    with pytest.raises(ValueError):
        _make_item(ReviewKind.CONTACT,ReviewPriority.NORMAL,(' ',),'reason')
