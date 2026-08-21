import unittest
from searchleads.icp_decision_support import ICPDimension, ReadinessLevel, qualification_field_canonicalization_snapshot, assess_icp_readiness

class ICPFieldReadinessTests(unittest.TestCase):
    def test_field_canonicalization_reaches_four_ready_two_partial_two_blocked(self):
        r=assess_icp_readiness(qualification_field_canonicalization_snapshot())
        self.assertEqual((r.ready,r.partial,r.blocked),(4,2,2))

    def test_industry_becomes_ready(self):
        r=assess_icp_readiness(qualification_field_canonicalization_snapshot())
        item=next(x for x in r.assessments if x.dimension is ICPDimension.INDUSTRY)
        self.assertEqual(item.readiness,ReadinessLevel.READY)

    def test_business_signal_becomes_ready(self):
        r=assess_icp_readiness(qualification_field_canonicalization_snapshot())
        item=next(x for x in r.assessments if x.dimension is ICPDimension.BUSINESS_SIGNAL)
        self.assertEqual(item.readiness,ReadinessLevel.READY)

    def test_geography_and_contactability_remain_partial(self):
        r=assess_icp_readiness(qualification_field_canonicalization_snapshot())
        by={x.dimension:x for x in r.assessments}
        self.assertEqual(by[ICPDimension.GEOGRAPHY].readiness,ReadinessLevel.PARTIAL)
        self.assertEqual(by[ICPDimension.REQUIRED_CONTACTABILITY].readiness,ReadinessLevel.PARTIAL)

if __name__=='__main__': unittest.main()
