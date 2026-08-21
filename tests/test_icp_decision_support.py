import unittest
from searchleads.icp_decision_support import (
    ICPDimension, ICPReadinessSnapshot, ReadinessLevel,
    acceptance_fixture_snapshot, assess_icp_readiness,
)

class ICPDecisionSupportTests(unittest.TestCase):
    def test_acceptance_snapshot_has_eight_dimensions_and_no_implicit_icp(self):
        report=assess_icp_readiness(acceptance_fixture_snapshot())
        self.assertEqual(report.total,8)
        self.assertTrue(all(a.business_definition_required for a in report.assessments))

    def test_acceptance_snapshot_numbers_are_stable(self):
        report=assess_icp_readiness(acceptance_fixture_snapshot())
        self.assertEqual((report.ready,report.partial,report.blocked),(0,6,2))

    def test_target_market_is_blocked_not_inferred_from_b2b(self):
        report=assess_icp_readiness(acceptance_fixture_snapshot())
        item=next(a for a in report.assessments if a.dimension is ICPDimension.TARGET_MARKET)
        self.assertEqual(item.readiness,ReadinessLevel.BLOCKED)

    def test_industry_is_partial_when_only_candidate_evidence_exists(self):
        report=assess_icp_readiness(acceptance_fixture_snapshot())
        item=next(a for a in report.assessments if a.dimension is ICPDimension.INDUSTRY)
        self.assertEqual(item.readiness,ReadinessLevel.PARTIAL)
        self.assertIn("primary_cnae_code",item.observed_support)

    def test_geography_is_partial_when_city_is_unresolved(self):
        report=assess_icp_readiness(acceptance_fixture_snapshot())
        item=next(a for a in report.assessments if a.dimension is ICPDimension.GEOGRAPHY)
        self.assertEqual(item.readiness,ReadinessLevel.PARTIAL)
        self.assertIn("state",item.observed_support)

    def test_company_size_is_blocked(self):
        report=assess_icp_readiness(acceptance_fixture_snapshot())
        item=next(a for a in report.assessments if a.dimension is ICPDimension.COMPANY_SIZE)
        self.assertEqual(item.readiness,ReadinessLevel.BLOCKED)

    def test_role_is_evidence_available_but_not_engine_ready(self):
        report=assess_icp_readiness(acceptance_fixture_snapshot())
        item=next(a for a in report.assessments if a.dimension is ICPDimension.TARGET_ROLE)
        self.assertEqual(item.readiness,ReadinessLevel.PARTIAL)
        self.assertIn("CanonicalFact",item.blockers[0])

    def test_contactability_does_not_claim_deliverability(self):
        report=assess_icp_readiness(acceptance_fixture_snapshot())
        item=next(a for a in report.assessments if a.dimension is ICPDimension.REQUIRED_CONTACTABILITY)
        self.assertEqual(item.readiness,ReadinessLevel.PARTIAL)
        self.assertTrue(any("deliverability" in b for b in item.blockers))

    def test_negative_operator_would_make_exclusion_engine_ready(self):
        snap=ICPReadinessSnapshot(qualification_operators=frozenset({"EQ","NOT_IN"}))
        report=assess_icp_readiness(snap)
        item=next(a for a in report.assessments if a.dimension is ICPDimension.EXCLUSION_CRITERIA)
        self.assertEqual(item.readiness,ReadinessLevel.READY)

    def test_canonical_industry_can_be_ready(self):
        snap=ICPReadinessSnapshot(canonical_predicates=frozenset({"primary_cnae_code"}))
        report=assess_icp_readiness(snap)
        item=next(a for a in report.assessments if a.dimension is ICPDimension.INDUSTRY)
        self.assertEqual(item.readiness,ReadinessLevel.READY)

if __name__=='__main__': unittest.main()
