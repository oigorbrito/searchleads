from __future__ import annotations
import unittest
from datetime import datetime, timezone
from searchleads.domain import Conflict, ContactKind, ContactPoint, ContactStatus, EntityRef, EntityType, LeadStatus, Provenance
from searchleads.entity_resolution import CompanyRecord, triage_pair
from searchleads.person_entity_resolution import PersonRecord, resolve_person_pair
from searchleads.qualification import QualificationResult
from searchleads.selective_review import ReviewKind, ReviewPriority, build_review_queue, review_company_match, review_conflict, review_contact, review_person_match, review_person_resolution, review_qualification

NOW=datetime(2026,8,21,14,0,tzinfo=timezone.utc)
PROV=Provenance(("ev-1",),"test",generated_at=NOW)

class SelectiveReviewTests(unittest.TestCase):
    def test_ambiguous_company_match_is_queued(self):
        a=CompanyRecord("a",name="ACME Tecnologia Ltda",domain="acme.com"); b=CompanyRecord("b",name="ACME Tecnologia",domain="acme.com"); item=review_company_match(a,b,triage_pair(a,b)); self.assertIsNotNone(item); self.assertEqual(item.kind,ReviewKind.COMPANY_MATCH)
    def test_obvious_exact_registry_match_is_not_queued(self):
        a=CompanyRecord("a",registry_id="123"); b=CompanyRecord("b",registry_id="123"); self.assertIsNone(review_company_match(a,b,triage_pair(a,b)))
    def test_explicit_person_ambiguity_is_reviewable_without_auto_merge(self):
        item=review_person_match("p1","p2","c1","same name and role; profile identity unresolved",("ev-1","ev-2")); self.assertEqual(item.kind,ReviewKind.PERSON_MATCH); self.assertEqual(len(item.evidence_ids),2)
    def test_typed_person_er_review_is_queued(self):
        decision=resolve_person_pair(PersonRecord("p1",name="Ana Costa",company_id="c1",role="CFO"),PersonRecord("p2",name="Ana Costa",company_id="c1",role="CFO")); item=review_person_resolution("p1","p2","c1",decision,("ev-1","ev-2")); self.assertIsNotNone(item); self.assertEqual(item.kind,ReviewKind.PERSON_MATCH); self.assertEqual(item.evidence_ids,("ev-1","ev-2"))
    def test_non_review_person_er_decisions_are_not_queued(self):
        insufficient=resolve_person_pair(PersonRecord("p1",name="Ana Costa"),PersonRecord("p2",name="Ana Costa")); self.assertIsNone(review_person_resolution("p1","p2","c1",insufficient))
        auto=resolve_person_pair(PersonRecord("p3",name="Ana Costa",profile_url="https://linkedin.com/in/ana",profile_is_person_unique=True),PersonRecord("p4",name="Ana Costa",profile_url="https://linkedin.com/in/ana/",profile_is_person_unique=True)); self.assertIsNone(review_person_resolution("p3","p4","c1",auto))
    def test_authoritative_open_conflict_is_high_priority(self):
        conflict=Conflict("conf-1",EntityRef(EntityType.COMPANY,"c1"),"business_registry_id",("cf1","cf2")); item=review_conflict(conflict,authoritative=True,evidence_ids=("ev-1","ev-2")); self.assertEqual(item.priority,ReviewPriority.HIGH)
    def test_resolved_conflict_is_not_requeued(self):
        from searchleads.domain import ConflictStatus
        conflict=Conflict("conf-1",EntityRef(EntityType.COMPANY,"c1"),"city",("cf1","cf2"),status=ConflictStatus.RESOLVED,resolved_canonical_fact_id="can-1"); self.assertIsNone(review_conflict(conflict))
    def test_discovered_contact_is_reviewable_but_validated_contact_is_not(self):
        discovered=ContactPoint("ct1",EntityRef(EntityType.COMPANY,"c1"),ContactKind.EMAIL,"x@example.com",PROV,ContactStatus.DISCOVERED); validated=ContactPoint("ct2",EntityRef(EntityType.COMPANY,"c1"),ContactKind.EMAIL,"x@example.com",PROV,ContactStatus.VALIDATED); self.assertIsNotNone(review_contact(discovered)); self.assertIsNone(review_contact(validated))
    def test_only_high_value_unknown_qualification_is_queued(self):
        result=QualificationResult("c1",None,LeadStatus.UNKNOWN,(),("ICP/policy is not defined",),()); self.assertIsNotNone(review_qualification(result,high_value=True)); self.assertIsNone(review_qualification(result,high_value=False))
    def test_queue_is_deduplicated_and_high_priority_first(self):
        q=QualificationResult("c1",None,LeadStatus.UNKNOWN,(),("missing",),()); high=review_qualification(q,high_value=True); normal=review_person_match("p1","p2","c1","ambiguous"); queue=build_review_queue((normal,high,normal,None)); self.assertEqual(len(queue),2); self.assertEqual(queue[0].priority,ReviewPriority.HIGH)

if __name__=='__main__': unittest.main()
