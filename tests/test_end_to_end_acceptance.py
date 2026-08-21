from __future__ import annotations
import json, unittest
from searchleads.acceptance import run_acceptance_fixture
from searchleads.domain import ContactStatus, EntityType, LeadStatus

class EndToEndAcceptanceTests(unittest.TestCase):
    def test_all_exercisable_non_business_handoff_gates_pass(self):
        result=run_acceptance_fixture()
        for gate in (
            "REAL_COMPANIES","MULTI_SOURCE","NORMALIZATION","DEDUPLICATION",
            "COMPANY_ER","PROVENANCE","CONTACT_DISCOVERY","CONTACT_VALIDATION",
            "PERSON_ROLE","PERSON_ER","PERSON_PROFESSIONAL_CONTACT",
            "QUALIFICATION_ENGINE","EXPORT","REPRODUCIBLE",
        ):
            self.assertIn(result.gate(gate),{"YES","PASS"},gate)

    def test_real_business_qualification_remains_blocked_by_missing_icp(self):
        result=run_acceptance_fixture()
        self.assertEqual(result.gate("ICP_DEFINED"),"NO")
        self.assertEqual(result.gate("REAL_QUALIFICATION"),"NOT_EVALUABLE")
        self.assertEqual(result.business_qualification_status,LeadStatus.UNKNOWN)

    def test_normalization_is_exercised_before_fusion_and_er(self):
        result=run_acceptance_fixture()
        self.assertGreater(result.normalized_candidate_count,0)
        self.assertGreater(result.normalization_rule_count,0)
        data=json.loads(result.export_json)
        normalized=[f for f in data["candidate_facts"] if f["normalization_rule"]]
        self.assertEqual(len(normalized),result.normalized_candidate_count)
        self.assertTrue(all(f["normalized_value"] is not None for f in normalized))

    def test_person_observations_are_distinct_and_person_er_is_exercised(self):
        result=run_acceptance_fixture()
        self.assertEqual(result.people_count,4)
        self.assertEqual(result.roles_count,4)
        self.assertEqual(result.person_er_decisions,2)
        self.assertEqual(result.person_er_review_items,2)
        self.assertEqual(result.gate("PERSON_ER"),"PASS")

    def test_technical_policy_exercises_qualification_without_becoming_product_icp(self):
        result=run_acceptance_fixture()
        self.assertEqual(result.technical_qualification_status,LeadStatus.QUALIFIED)

    def test_pipeline_produces_evidence_contacts_people_conflict_and_review(self):
        result=run_acceptance_fixture()
        self.assertGreaterEqual(result.evidence_count,7)
        self.assertEqual(result.validated_contacts,2)
        self.assertEqual(result.person_professional_contacts,4)
        self.assertEqual(result.person_professional_profiles,0)
        self.assertGreaterEqual(result.conflicts,1)
        self.assertGreaterEqual(result.review_items,4)

    def test_export_keeps_company_validated_and_person_discovered_contacts_separate(self):
        result=run_acceptance_fixture()
        data=json.loads(result.export_json)
        self.assertEqual(data["company"]["company_id"],"company:cnpj:33683111000280")
        self.assertIsNone(data["lead"])
        self.assertEqual(data["qualification"]["status"],"UNKNOWN")
        self.assertEqual(len(data["evidence"]),7)
        self.assertEqual(len(data["contacts"]),6)
        company_contacts=[c for c in data["contacts"] if c["owner"]["entity_type"]==EntityType.COMPANY.value]
        person_contacts=[c for c in data["contacts"] if c["owner"]["entity_type"]==EntityType.PERSON.value]
        self.assertEqual(len(company_contacts),2)
        self.assertTrue(all(c["status"]==ContactStatus.VALIDATED.value for c in company_contacts))
        self.assertEqual(len(person_contacts),4)
        self.assertTrue(all(c["status"]==ContactStatus.DISCOVERED.value for c in person_contacts))

    def test_provenance_gate_is_derived_from_exported_graph(self):
        result=run_acceptance_fixture()
        self.assertEqual(result.gate("PROVENANCE"),"PASS")
        data=json.loads(result.export_json)
        evidence_ids={e["evidence_id"] for e in data["evidence"]}
        for collection in ("contacts","candidate_facts","canonical_facts","roles"):
            for item in data[collection]:
                self.assertTrue(set(item["provenance"]["evidence_ids"]) <= evidence_ids)

    def test_full_run_reproducibility_gate_is_measured(self):
        result=run_acceptance_fixture()
        self.assertEqual(result.gate("REPRODUCIBLE"),"PASS")
        first=run_acceptance_fixture()
        second=run_acceptance_fixture()
        self.assertEqual(first.export_sha256,second.export_sha256)
        self.assertEqual(first.export_json,second.export_json)

if __name__=='__main__': unittest.main()
