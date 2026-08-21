from __future__ import annotations
import unittest
from datetime import datetime, timezone, timedelta
from searchleads.domain import (
    CandidateFact, CanonicalFact, Conflict, ContactKind, ContactPoint, ContactStatus,
    EntityRef, EntityType, LeadStatus, Provenance,
)
from searchleads.metrics import (
    MetricAvailability, compute_contact_metrics, compute_discovery_metrics,
    compute_enrichment_metrics, compute_entity_resolution_metrics,
    compute_operational_metrics, compute_qualification_metrics,
)
NOW = datetime(2026,8,21,17,0,tzinfo=timezone.utc)
COMPANY = EntityRef(EntityType.COMPANY, "c1")
PROV = Provenance(("e1",), "test", generated_at=NOW)

def cf(fid,pred,val): return CanonicalFact(fid,COMPANY,pred,val,("cand-"+fid,),PROV)
def cand(fid,pred,val): return CandidateFact(fid,COMPANY,pred,val,PROV)

class MetricsTests(unittest.TestCase):
    def test_discovery_duplicate_rate_is_measured_without_universe(self):
        m=compute_discovery_metrics(["a","a","b"])
        self.assertAlmostEqual(m.duplicate_discovery_rate.value,1/3)
        self.assertIsNone(m.company_coverage.value)
        self.assertIsNone(m.discovery_precision.value)

    def test_discovery_coverage_and_precision_need_explicit_denominators(self):
        m=compute_discovery_metrics(["a","b"],universe_company_ids=["a","b","c","d"],true_relevant_company_ids=["a","c"])
        self.assertEqual(m.company_coverage.value,0.5)
        self.assertEqual(m.discovery_precision.value,0.5)

    def test_er_includes_false_split_rate(self):
        m=compute_entity_resolution_metrics(8,1,9,2)
        self.assertEqual(m.precision.value,8/9)
        self.assertEqual(m.recall.value,0.8)
        self.assertEqual(m.false_merge_rate.value,0.1)
        self.assertEqual(m.false_split_rate.value,0.2)

    def test_enrichment_measures_coverage_provenance_and_conflicts(self):
        facts=[cf("f1","state","DF"),cf("f2","industry","tech")]
        candidates=[cand("a","state","DF"),cand("b","industry","tech")]
        conflict=Conflict("x",COMPANY,"city",("ca","cb"))
        m=compute_enrichment_metrics(["c1"],["state","industry","city"],canonical_facts=facts,candidate_facts=candidates,conflicts=[conflict])
        self.assertEqual(m.field_coverage.value,2/3)
        self.assertEqual(m.provenance_coverage.value,1.0)
        self.assertEqual(m.conflict_rate.value,1/3)
        self.assertIsNone(m.field_accuracy.value)

    def test_field_accuracy_requires_labels_and_uses_present_fields(self):
        m=compute_enrichment_metrics(["c1"],["state"],canonical_facts=[cf("f1","state","DF")],field_accuracy_labels={("c1","state"):True})
        self.assertEqual(m.field_accuracy.value,1.0)

    def test_contact_metrics_dedupe_discovered_validated_snapshots(self):
        d=ContactPoint("d",COMPANY,ContactKind.EMAIL,"X@EXAMPLE.COM",PROV,ContactStatus.DISCOVERED)
        later=Provenance(("e2",),"validate",generated_at=NOW+timedelta(minutes=1))
        v=ContactPoint("v",COMPANY,ContactKind.EMAIL,"x@example.com",later,ContactStatus.VALIDATED)
        m=compute_contact_metrics([d,v],company_ids=["c1"])
        self.assertEqual(m.logical_contacts,1)
        self.assertEqual(m.contact_discovery_rate.value,1.0)
        self.assertEqual(m.validation_rate.value,1.0)

    def test_contact_rates_distinguish_invalid_and_stale(self):
        a=ContactPoint("a",COMPANY,ContactKind.PHONE,"11111111",PROV,ContactStatus.INVALID)
        b=ContactPoint("b",COMPANY,ContactKind.EMAIL,"x@y.com",PROV,ContactStatus.STALE)
        m=compute_contact_metrics([a,b],company_ids=["c1"])
        self.assertEqual(m.invalid_rate.value,0.5)
        self.assertEqual(m.stale_rate.value,0.5)

    def test_qualification_metrics_are_unavailable_without_ground_truth(self):
        m=compute_qualification_metrics({"c1":LeadStatus.UNKNOWN})
        self.assertEqual(m.precision.availability,MetricAvailability.UNAVAILABLE)
        self.assertIn("ICP",m.precision.reason)

    def test_qualification_metrics_work_when_labels_exist(self):
        preds={"a":LeadStatus.QUALIFIED,"b":LeadStatus.QUALIFIED,"c":LeadStatus.NOT_QUALIFIED}
        m=compute_qualification_metrics(preds,ground_truth={"a":True,"b":False,"c":True},human_decisions={"a":LeadStatus.QUALIFIED,"b":LeadStatus.NOT_QUALIFIED,"c":LeadStatus.NOT_QUALIFIED})
        self.assertEqual(m.precision.value,0.5)
        self.assertEqual(m.recall.value,0.5)
        self.assertEqual(m.human_disagreement_rate.value,1/3)

    def test_operational_metrics_do_not_invent_missing_costs(self):
        m=compute_operational_metrics(discovered_companies=2)
        self.assertIsNone(m.cost_per_discovered_company.value)

    def test_operational_metrics_compute_only_from_supplied_telemetry(self):
        m=compute_operational_metrics(total_cost=10,elapsed_seconds=30,discovered_companies=2,enriched_companies=1,qualified_leads=1,validated_contacts=2,processed_leads=3)
        self.assertEqual(m.cost_per_discovered_company.value,5)
        self.assertEqual(m.cost_per_validated_contact.value,5)
        self.assertEqual(m.time_per_lead_seconds.value,10)

if __name__=='__main__': unittest.main()
