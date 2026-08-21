import unittest
from datetime import datetime, timezone

from searchleads.brasilapi import BrasilAPISource
from searchleads.icp_decision_support import ICPDimension, ReadinessLevel, assess_icp_readiness, registry_size_signal_snapshot
from searchleads.persistence import SQLiteLeadStore
from searchleads.qualification_field_canonicalization import canonicalize_selected_company_fields

NOW=datetime(2026,8,21,17,0,tzinfo=timezone.utc)
PAYLOAD={
    "cnpj":"33683111000280",
    "razao_social":"SERVICO FEDERAL DE PROCESSAMENTO DE DADOS (SERPRO)",
    "porte":"DEMAIS",
    "codigo_porte":5,
}

class CompanySizeRegistrySignalTests(unittest.TestCase):
    def test_brasilapi_extracts_registry_size_without_inferred_metrics(self):
        with SQLiteLeadStore() as store:
            result=BrasilAPISource(transport=lambda _:PAYLOAD).ingest(store,PAYLOAD["cnpj"],retrieved_at=NOW)
            facts={f.predicate:f.raw_value for f in result.candidate_facts}
            self.assertEqual(facts["registry_size_class"],"DEMAIS")
            self.assertEqual(facts["registry_size_code"],5)
            self.assertNotIn("employee_count",facts)
            self.assertNotIn("revenue",facts)

    def test_registry_size_class_can_use_existing_conservative_canonicalization(self):
        with SQLiteLeadStore() as store:
            result=BrasilAPISource(transport=lambda _:PAYLOAD).ingest(store,PAYLOAD["cnpj"],retrieved_at=NOW)
            fused=canonicalize_selected_company_fields(result.candidate_facts,("registry_size_class",))
            self.assertEqual(len(fused.canonical_facts),1)
            self.assertEqual(fused.canonical_facts[0].value,"DEMAIS")

    def test_registry_size_class_is_partial_not_full_size_readiness(self):
        report=assess_icp_readiness(registry_size_signal_snapshot())
        item=next(x for x in report.assessments if x.dimension is ICPDimension.COMPANY_SIZE)
        self.assertEqual(item.readiness,ReadinessLevel.PARTIAL)
        self.assertTrue(any("employee count/revenue" in b for b in item.blockers))

    def test_registry_size_stage_has_only_target_market_blocked(self):
        report=assess_icp_readiness(registry_size_signal_snapshot())
        self.assertEqual((report.ready,report.partial,report.blocked),(4,3,1))
        blocked=tuple(x.dimension for x in report.assessments if x.readiness is ReadinessLevel.BLOCKED)
        self.assertEqual(blocked,(ICPDimension.TARGET_MARKET,))

if __name__=='__main__': unittest.main()
