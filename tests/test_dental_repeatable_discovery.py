from __future__ import annotations

import unittest

from searchleads.dental_facial_surgery_icp import (
    BrazilRegion,
    DentalTitleGroup,
    select_dental_icp,
)
from searchleads.dental_repeatable_discovery import (
    CFOVerificationStatus,
    PublicSearchObservation,
    build_dental_discovery_queries,
    discover_dental_candidates,
)


class DentalRepeatableDiscoveryMVPTests(unittest.TestCase):
    def test_query_plan_is_bounded_deterministic_and_respects_region_title_filter(self):
        icp = select_dental_icp(
            regions=(BrazilRegion.SOUTH,),
            title_groups=(DentalTitleGroup.BUCOMAXILLOFACIAL,),
        )
        first = build_dental_discovery_queries(icp, max_queries=3)
        second = build_dental_discovery_queries(icp, max_queries=3)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 3)
        self.assertEqual({item.state for item in first}, {"PR", "RS", "SC"})
        self.assertTrue(all(item.title_group is DentalTitleGroup.BUCOMAXILLOFACIAL for item in first))

    def test_public_claim_becomes_candidate_but_stays_pending_cfo_verification(self):
        observation = PublicSearchObservation(
            observation_id="obs-1",
            url="https://example.org/profissional/?utm_source=x",
            title="Dra. Exemplo — Cirurgiã Bucomaxilofacial",
            snippet="CRO-SP: 136407. Cirurgia facial e atendimento profissional.",
            evidence_id="ev-search-1",
        )
        candidates = discover_dental_candidates((observation,))
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual((candidate.cro_state, candidate.cro_number), ("SP", "136407"))
        self.assertEqual(candidate.observed_title_group, DentalTitleGroup.BUCOMAXILLOFACIAL)
        self.assertEqual(candidate.cfo_verification_status, CFOVerificationStatus.PENDING)
        self.assertEqual(candidate.evidence_ids, ("ev-search-1",))

    def test_exact_cro_deduplicates_but_same_name_without_cro_does_not(self):
        observations = (
            PublicSearchObservation(
                "obs-a", "https://a.example/p", "Dra. Ana — Dentista",
                "CRO PR 33221", "ev-a"
            ),
            PublicSearchObservation(
                "obs-b", "https://b.example/profile", "Dra. Ana — Bucomaxilofacial",
                "CRO-PR: 33221", "ev-b"
            ),
            PublicSearchObservation(
                "obs-c", "https://c.example/ana", "Dra. Ana — Dentista",
                "Cirurgiã-dentista em Curitiba", "ev-c"
            ),
        )
        candidates = discover_dental_candidates(observations)
        self.assertEqual(len(candidates), 2)
        exact = next(item for item in candidates if item.cro_number == "33221")
        self.assertEqual(exact.evidence_ids, ("ev-a", "ev-b"))
        self.assertTrue(any(item.cro_number is None for item in candidates))


if __name__ == "__main__":
    unittest.main()
