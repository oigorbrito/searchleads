from __future__ import annotations
import csv, io, json, unittest
from datetime import datetime, timezone
from searchleads.domain import CanonicalFact, Company, ContactKind, ContactPoint, ContactStatus, EntityRef, EntityType, Evidence, Lead, LeadStatus, Person, ProfessionalRole, Provenance, Source, SourceType
from searchleads.lead_export import LeadExportBundle, export_csv, export_json, to_export_dict
from searchleads.qualification import QualificationResult

NOW=datetime(2026,8,21,15,0,tzinfo=timezone.utc)
COMPANY=Company("c1",NOW); PERSON=Person("p1",NOW); SOURCE=Source("s1",SourceType.OFFICIAL_SOURCE,"https://example.test")
EVIDENCE=Evidence("e1","s1",NOW,{"body":"official"}); PROV=Provenance(("e1",),"test",generated_at=NOW)
ROLE=ProfessionalRole("r1","p1","c1","Diretora",PROV)
CONTACT=ContactPoint("ct1",EntityRef(EntityType.COMPANY,"c1"),ContactKind.EMAIL,"contato@example.test",PROV,ContactStatus.VALIDATED)
FACT=CanonicalFact("can1",EntityRef(EntityType.COMPANY,"c1"),"state","DF",("cf1",),PROV)
QUAL=QualificationResult("c1",None,LeadStatus.UNKNOWN,(),("ICP/policy is not defined",),())
LEAD=Lead("l1","c1",LeadStatus.UNKNOWN,metadata={"qualification_policy_id":None})

def bundle(**overrides):
    data=dict(company=COMPANY,lead=LEAD,people=(PERSON,),roles=(ROLE,),contacts=(CONTACT,),canonical_facts=(FACT,),sources=(SOURCE,),evidence=(EVIDENCE,),qualification=QUAL)
    data.update(overrides); return LeadExportBundle(**data)

class LeadExportTests(unittest.TestCase):
    def test_export_contains_all_required_sections(self):
        data=to_export_dict(bundle()); self.assertEqual(set(data),{"company","lead","people","roles","contacts","candidate_facts","canonical_facts","conflicts","sources","evidence","qualification"})
    def test_json_is_deterministic_and_roundtrippable(self):
        a=export_json(bundle()); b=export_json(bundle()); self.assertEqual(a,b); self.assertEqual(json.loads(a)["company"]["company_id"],"c1")
    def test_provenance_is_visible_per_fact_contact_and_role(self):
        data=to_export_dict(bundle()); self.assertEqual(data["canonical_facts"][0]["provenance"]["evidence_ids"],["e1"]); self.assertEqual(data["contacts"][0]["provenance"]["evidence_ids"],["e1"]); self.assertEqual(data["roles"][0]["provenance"]["evidence_ids"],["e1"])
    def test_csv_is_one_independent_record_with_nested_audit_cells(self):
        rows=list(csv.DictReader(io.StringIO(export_csv(bundle())))); self.assertEqual(len(rows),1); self.assertEqual(rows[0]["company_id"],"c1"); self.assertEqual(rows[0]["lead_status"],"UNKNOWN"); self.assertIn('evidence_ids',rows[0]["facts"])
    def test_company_can_export_without_lead_when_icp_not_defined(self):
        data=to_export_dict(bundle(lead=None,qualification=None)); self.assertIsNone(data["lead"]); self.assertIsNone(data["qualification"])
    def test_missing_provenance_evidence_is_rejected(self):
        with self.assertRaises(ValueError): to_export_dict(bundle(evidence=()))
    def test_cross_company_lead_is_rejected(self):
        bad=Lead("l2","other",LeadStatus.UNKNOWN)
        with self.assertRaises(ValueError): to_export_dict(bundle(lead=bad))

if __name__=='__main__': unittest.main()
