import unittest
from searchleads.icp_decision_support import ICPDimension, ReadinessLevel, acceptance_fixture_snapshot, qualification_bridge_snapshot, assess_icp_readiness

class ICPBridgeReadinessTests(unittest.TestCase):
    def test_before_bridge_counts(self):
        r=assess_icp_readiness(acceptance_fixture_snapshot())
        self.assertEqual((r.ready,r.partial,r.blocked),(0,6,2))

    def test_after_bridge_counts(self):
        r=assess_icp_readiness(qualification_bridge_snapshot())
        self.assertEqual((r.ready,r.partial,r.blocked),(2,4,2))

    def test_exclusion_criteria_becomes_ready(self):
        r=assess_icp_readiness(qualification_bridge_snapshot())
        item=next(x for x in r.assessments if x.dimension is ICPDimension.EXCLUSION_CRITERIA)
        self.assertEqual(item.readiness,ReadinessLevel.READY)

    def test_target_role_becomes_ready(self):
        r=assess_icp_readiness(qualification_bridge_snapshot())
        item=next(x for x in r.assessments if x.dimension is ICPDimension.TARGET_ROLE)
        self.assertEqual(item.readiness,ReadinessLevel.READY)

    def test_contactability_remains_partial_without_deliverability(self):
        r=assess_icp_readiness(qualification_bridge_snapshot())
        item=next(x for x in r.assessments if x.dimension is ICPDimension.REQUIRED_CONTACTABILITY)
        self.assertEqual(item.readiness,ReadinessLevel.PARTIAL)
        self.assertTrue(any('deliverability' in b for b in item.blockers))

if __name__=='__main__': unittest.main()
