from __future__ import annotations
import json, unittest
from searchleads.acceptance import run_acceptance_fixture
from searchleads.dental_facial_surgery_icp import DEFAULT_DENTAL_FACIAL_SURGERY_ICP_V1
from searchleads.domain import LeadStatus

class EndToEndAcceptanceTests(unittest.TestCase):
    def test_all_non_business_handoff_gates_pass(self):
        result=run_acceptance_fixture()
        for gate in ("REAL_COMPANIES","MULTI_SOURCE","DEDUPLICATION","COMPANY_ER","PROVENANCE","CONTACT_DISCOVERY","CONTACT_VALIDATION","PERSON_ROLE","QUALIFICATION_ENGINE","EXPORT","REPRODUCIBLE"):
            self.assertIn(result.gate(gate),{"YES","PASS"},gate)
    def test_real_business_qualification_remains_blocked_by_missing_icp(self):
        result=run_acceptance_fixture(); self.assertEqual(result.gate("ICP_DEFINED"),"NO"); self.assertEqual(result.gate("REAL_QUALIFICATION"),"NOT_EVALUABLE"); self.assertEqual(result.business_qualification_status,LeadStatus.UNKNOWN)
    def test_dental_icp_bridge_marks_policy_defined_without_faking_company_qualification(self):
        legacy=run_acceptance_fixture()
        result=run_acceptance_fixture(icp_policy_id=DEFAULT_DENTAL_FACIAL_SURGERY_ICP_V1.policy_id)
        self.assertEqual(result.gate("ICP_DEFINED"),"YES")
        self.assertEqual(result.gate("REAL_QUALIFICATION"),"NOT_EVALUABLE")
        self.assertEqual(result.business_qualification_status,LeadStatus.UNKNOWN)
        self.assertEqual(result.export_sha256,legacy.export_sha256)
        self.assertEqual(result.export_json,legacy.export_json)
    def test_technical_policy_exercises_qualification_without_becoming_product_icp(self):
        result=run_acceptance_fixture(); self.assertEqual(result.technical_qualification_status,LeadStatus.QUALIFIED)
    def test_pipeline_produces_evidence_contacts_people_conflict_and_review(self):
        result=run_acceptance_fixture(); self.assertGreaterEqual(result.evidence_count,6); self.assertEqual(result.validated_contacts,2); self.assertGreaterEqual(result.people_count,1); self.assertEqual(result.people_count,result.roles_count); self.assertGreaterEqual(result.conflicts,1); self.assertGreaterEqual(result.review_items,2)
    def test_export_is_auditable_company_record_without_fake_lead(self):
        result=run_acceptance_fixture(); data=json.loads(result.export_json); self.assertEqual(data["company"]["company_id"],"company:cnpj:33683111000280"); self.assertIsNone(data["lead"]); self.assertEqual(data["qualification"]["status"],"UNKNOWN"); self.assertTrue(data["evidence"]); self.assertTrue(data["contacts"])
    def test_full_run_is_bit_reproducible(self):
        first=run_acceptance_fixture(); second=run_acceptance_fixture(); self.assertEqual(first.export_sha256,second.export_sha256); self.assertEqual(first.export_json,second.export_json)

if __name__=='__main__': unittest.main()
