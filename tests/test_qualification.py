from __future__ import annotations
import unittest
from datetime import datetime, timezone
from searchleads.domain import CanonicalFact, EntityRef, EntityType, LeadStatus, Provenance
from searchleads.qualification import CriterionOperator, QualificationCriterion, QualificationPolicy, lead_from_qualification, qualify_company

NOW=datetime(2026,8,21,16,0,tzinfo=timezone.utc); REF=EntityRef(EntityType.COMPANY,"company-1"); PROV=Provenance(("ev",),"fusion",generated_at=NOW)
def cf(fid,pred,val): return CanonicalFact(fid,REF,pred,val,("candidate-"+fid,),PROV)
def policy(): return QualificationPolicy("explicit-test-policy",(
    QualificationCriterion("active","registration_status",CriterionOperator.EQ,"ATIVA",True),
    QualificationCriterion("state","state",CriterionOperator.IN,("DF","SP"),True),
    QualificationCriterion("industry","primary_cnae_description",CriterionOperator.CONTAINS,"tecnologia",False),
),minimum_optional_matches=1)

class QualificationTests(unittest.TestCase):
    def test_no_policy_means_unknown_not_qualified(self):
        r=qualify_company("company-1",[cf("c1","registration_status","ATIVA")],None); self.assertEqual(r.status,LeadStatus.UNKNOWN); self.assertIsNone(r.policy_id)
    def test_empty_policy_is_rejected(self):
        with self.assertRaises(ValueError): QualificationPolicy("x",())
    def test_all_required_and_optional_threshold_can_qualify(self):
        r=qualify_company("company-1",[cf("c1","registration_status","ATIVA"),cf("c2","state","DF"),cf("c3","primary_cnae_description","Consultoria em tecnologia da informação")],policy()); self.assertEqual(r.status,LeadStatus.QUALIFIED); self.assertEqual(set(r.qualification_fact_ids),{"c1","c2","c3"})
    def test_required_contradiction_is_not_qualified(self):
        r=qualify_company("company-1",[cf("c1","registration_status","BAIXADA"),cf("c2","state","DF"),cf("c3","primary_cnae_description","tecnologia")],policy()); self.assertEqual(r.status,LeadStatus.NOT_QUALIFIED)
    def test_missing_required_evidence_is_unknown(self):
        self.assertEqual(qualify_company("company-1",[cf("c1","registration_status","ATIVA")],policy()).status,LeadStatus.UNKNOWN)
    def test_multiple_canonical_values_for_same_predicate_are_unknown(self):
        self.assertEqual(qualify_company("company-1",[cf("c1","registration_status","ATIVA"),cf("c2","registration_status","ATIVA"),cf("c3","state","DF")],policy()).status,LeadStatus.UNKNOWN)
    def test_optional_threshold_failure_is_not_qualified(self):
        self.assertEqual(qualify_company("company-1",[cf("c1","registration_status","ATIVA"),cf("c2","state","DF"),cf("c3","primary_cnae_description","Serviços administrativos")],policy()).status,LeadStatus.NOT_QUALIFIED)
    def test_facts_for_other_company_are_not_used(self):
        other=CanonicalFact("o",EntityRef(EntityType.COMPANY,"other"),"state","DF",("x",),PROV); self.assertEqual(qualify_company("company-1",[cf("c1","registration_status","ATIVA"),other],policy()).status,LeadStatus.UNKNOWN)
    def test_lead_preserves_status_reasons_and_fact_ids(self):
        r=qualify_company("company-1",[cf("c1","registration_status","ATIVA"),cf("c2","state","DF"),cf("c3","primary_cnae_description","tecnologia")],policy()); lead=lead_from_qualification(r); self.assertEqual(lead.status,LeadStatus.QUALIFIED); self.assertEqual(lead.qualification_facts,r.qualification_fact_ids); self.assertEqual(lead.metadata["qualification_policy_id"],"explicit-test-policy")
    def test_unknown_lead_remains_representable_without_fake_reasoning(self):
        lead=lead_from_qualification(qualify_company("company-1",[],None)); self.assertEqual(lead.status,LeadStatus.UNKNOWN); self.assertIn("ICP/policy",lead.reasons[0])
    def test_in_operator_requires_nonempty_collection(self):
        with self.assertRaises(ValueError): QualificationCriterion("x","state",CriterionOperator.IN,(),True)
    def test_optional_threshold_must_fit_optional_count(self):
        with self.assertRaises(ValueError): QualificationPolicy("x",(QualificationCriterion("a","x",CriterionOperator.EXISTS,None,True),),1)

if __name__=='__main__': unittest.main()
