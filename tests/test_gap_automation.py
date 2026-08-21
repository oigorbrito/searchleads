from __future__ import annotations
import unittest
from datetime import datetime, timezone
from searchleads.domain import CanonicalFact, ContactKind, ContactPoint, ContactStatus, EntityRef, EntityType, LeadStatus, ProfessionalRole, Provenance
from searchleads.gap_automation import ActionDisposition, ActionKind, GapRequirements, detect_gaps, plan_gap_actions
from searchleads.qualification import QualificationResult

NOW=datetime(2026,8,21,16,0,tzinfo=timezone.utc)
SUB=EntityRef(EntityType.COMPANY,"c1"); PROV=Provenance(("e1",),"test",generated_at=NOW)
def fact(pred,val): return CanonicalFact("can-"+pred,SUB,pred,val,("cf-"+pred,),PROV)

class GapAutomationTests(unittest.TestCase):
    def test_missing_fields_are_detected_only_from_explicit_requirements(self):
        req=GapRequirements(("state","website_url")); gaps=detect_gaps("c1",req,canonical_facts=(fact("state","DF"),)); self.assertEqual([g.key for g in gaps],["website_url"])
    def test_registry_gap_maps_to_existing_brasilapi_capability(self):
        plan=plan_gap_actions("c1",GapRequirements(("primary_cnae_code",))); self.assertEqual(plan.actions[0].action_kind,ActionKind.BRASILAPI_LOOKUP); self.assertEqual(plan.actions[0].disposition,ActionDisposition.READY)
    def test_location_gap_maps_to_existing_official_location_capability(self):
        plan=plan_gap_actions("c1",GapRequirements(("postal_code",))); self.assertEqual(plan.actions[0].action_kind,ActionKind.OFFICIAL_LOCATION_ENRICHMENT)
    def test_unknown_field_is_blocked_instead_of_inventing_source(self):
        plan=plan_gap_actions("c1",GapRequirements(("employee_count",))); self.assertEqual(plan.actions[0].disposition,ActionDisposition.BLOCKED); self.assertIsNone(plan.actions[0].action_kind)
    def test_validated_contact_requirement_uses_contact_capability(self):
        req=GapRequirements(require_validated_contact=True); plan=plan_gap_actions("c1",req); self.assertEqual(plan.actions[0].action_kind,ActionKind.OFFICIAL_CONTACT_DISCOVERY)
        validated=ContactPoint("ct",SUB,ContactKind.EMAIL,"a@b.test",PROV,ContactStatus.VALIDATED); self.assertEqual(plan_gap_actions("c1",req,contacts=(validated,)).gaps,())
    def test_person_role_requirement_uses_known_people_capability(self):
        req=GapRequirements(require_person_role=True); self.assertEqual(plan_gap_actions("c1",req).actions[0].action_kind,ActionKind.OFFICIAL_PEOPLE_DISCOVERY)
        role=ProfessionalRole("r1","p1","c1","Diretor",PROV); self.assertEqual(plan_gap_actions("c1",req,roles=(role,)).gaps,())
    def test_qualification_gap_is_blocked_without_policy_and_ready_with_policy(self):
        req=GapRequirements(require_qualification=True); blocked=plan_gap_actions("c1",req); self.assertEqual(blocked.actions[0].disposition,ActionDisposition.BLOCKED)
        ready=plan_gap_actions("c1",req,qualification_policy_id="policy-1"); self.assertEqual(ready.actions[0].action_kind,ActionKind.QUALIFICATION_EVALUATION)
    def test_existing_qualification_closes_gap_even_if_unknown(self):
        q=QualificationResult("c1",None,LeadStatus.UNKNOWN,(),("ICP missing",),()); self.assertEqual(plan_gap_actions("c1",GapRequirements(require_qualification=True),qualification=q).gaps,())
    def test_ready_network_actions_have_bounded_retry_cache_and_rate_interval(self):
        action=plan_gap_actions("c1",GapRequirements(("state",))).actions[0]; self.assertEqual(action.retry_max_attempts,3); self.assertTrue(action.cache_key.startswith("gap:")); self.assertGreater(action.min_interval_seconds,0)

if __name__=='__main__': unittest.main()
