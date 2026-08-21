from __future__ import annotations
import json, unittest
from searchleads.acceptance import run_acceptance_fixture
from searchleads.domain import ContactStatus, EntityType, LeadStatus

class EndToEndAcceptanceTests(unittest.TestCase):
    def test_all_non_business_handoff_gates_pass(self):
        result=run_acceptance_fixture()
        for gate in ("REAL_COMPANIES","MULTI_SOURCE","DEDUPLICATION","COMPANY_ER","PROVENANCE","CONTACT_DISCOVERY","CONTACT_VALIDATION","PERSON_ROLE","PERSON_PROFESSIONAL_CONTACT","QUALIFICATION_ENGINE","EXPORT","REPRODUCIBLE"):
            self.assertIn(result.gate(gate),{"YES","PASS"},gate)
    def test_real_business_qualification_remains_blocked_by_missing_icp(self):
        result=run_acceptance_fixture(); self.assertEqual(result.gate("ICP_DEFINED"),"NO"); self.assertEqual(result.gate("REAL_QUALIFICATION"),"NOT_EVALUABLE"); self.assertEqual(result.business_qualification_status,LeadStatus.UNKNOWN)
    def test_technical_policy_exercises_qualification_without_becoming_product_icp(self):
        result=run_acceptance_fixture(); self.assertEqual(result.technical_qualification_status,LeadStatus.QUALIFIED)
    def test_pipeline_produces_evidence_contacts_people_conflict_and_review(self):
        result=run_acceptance_fixture(); self.assertGreaterEqual(result.evidence_count,6); self.assertEqual(result.validated_contacts,2); self.assertEqual(result.person_professional_contacts,4); self.assertEqual(result.person_professional_profiles,0); self.assertEqual(result.people_count,2); self.assertEqual(result.people_count,result.roles_count); self.assertGreaterEqual(result.conflicts,1); self.assertGreaterEqual(result.review_items,2)
    def test_export_keeps_company_validated_and_person_discovered_contacts_separate(self):
        result=run_acceptance_fixture(); data=json.loads(result.export_json); self.assertEqual(data["company"]["company_id"],"company:cnpj:33683111000280"); self.assertIsNone(data["lead"]); self.assertEqual(data["qualification"]["status"],"UNKNOWN"); self.assertTrue(data["evidence"]); self.assertEqual(len(data["contacts"]),6)
        company_contacts=[c for c in data["contacts"] if c["owner"]["entity_type"]==EntityType.COMPANY.value]
        person_contacts=[c for c in data["contacts"] if c["owner"]["entity_type"]==EntityType.PERSON.value]
        self.assertEqual(len(company_contacts),2); self.assertTrue(all(c["status"]==ContactStatus.VALIDATED.value for c in company_contacts))
        self.assertEqual(len(person_contacts),4); self.assertTrue(all(c["status"]==ContactStatus.DISCOVERED.value for c in person_contacts))
    def test_full_run_is_bit_reproducible(self):
        first=run_acceptance_fixture(); second=run_acceptance_fixture(); self.assertEqual(first.export_sha256,second.export_sha256); self.assertEqual(first.export_json,second.export_json)

if __name__=='__main__': unittest.main()
