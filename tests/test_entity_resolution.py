from __future__ import annotations

import json
import unittest
from pathlib import Path

from searchleads.entity_resolution import (
    CompanyRecord,
    LabeledPair,
    ResolutionDisposition,
    Strategy,
    compare_features,
    evaluate,
    evaluate_blocking,
    evaluate_blocking_corpus,
    resolve_pair,
    triage_pair,
)

FIXTURE = Path(__file__).parent / "fixtures" / "company_er_v1.json"


def load_pairs():
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return tuple(
        LabeledPair(
            pair_id=item["id"],
            left=CompanyRecord(record_id=item["id"] + "-l", **item["left"]),
            right=CompanyRecord(record_id=item["id"] + "-r", **item["right"]),
            is_duplicate=item["label"],
            category=item["category"],
        )
        for item in raw
    )


class EntityResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pairs = load_pairs()

    def test_fixture_is_balanced_and_has_hard_negative_categories(self):
        self.assertEqual(len(self.pairs), 54)
        self.assertEqual(sum(p.is_duplicate for p in self.pairs), 27)
        categories = {p.category for p in self.pairs if not p.is_duplicate}
        self.assertTrue({"shared_domain", "shared_phone", "shared_address", "registry_conflict", "similar_name"} <= categories)

    def test_registry_conflict_is_hard_veto(self):
        pair = next(p for p in self.pairs if p.pair_id == "n01")
        decision = resolve_pair(pair.left, pair.right, strategy=Strategy.WEIGHTED, threshold=0.50)
        self.assertFalse(decision.is_match)
        self.assertIn("registry_conflict", decision.reasons)

    def test_exact_registry_is_hard_positive(self):
        pair = next(p for p in self.pairs if p.pair_id == "p01")
        decision = resolve_pair(pair.left, pair.right, strategy=Strategy.WEIGHTED, threshold=0.99)
        self.assertTrue(decision.is_match)
        self.assertEqual(decision.score, 1.0)

    def test_diacritics_and_case_do_not_destroy_name_similarity(self):
        pair = next(p for p in self.pairs if p.pair_id == "p06")
        features = compare_features(pair.left, pair.right)
        self.assertGreater(features.name_similarity, 0.75)
        self.assertTrue(features.location_exact)

    def test_shared_domain_alone_does_not_force_match(self):
        pair = next(p for p in self.pairs if p.pair_id == "n11")
        decision = resolve_pair(pair.left, pair.right, strategy=Strategy.EXACT_EVIDENCE)
        self.assertFalse(decision.is_match)

    def test_blocking_retains_most_positive_pairs(self):
        metrics = evaluate_blocking(self.pairs)
        self.assertGreaterEqual(metrics.blocking_recall, 0.90)

    def test_registry_only_is_high_precision_low_recall(self):
        metrics = evaluate(self.pairs, strategy=Strategy.REGISTRY_ONLY)
        self.assertEqual(metrics.false_positive, 0)
        self.assertLess(metrics.recall, 0.50)

    def test_weighted_threshold_078_is_not_worse_than_registry_only_f1(self):
        registry = evaluate(self.pairs, strategy=Strategy.REGISTRY_ONLY)
        weighted = evaluate(self.pairs, strategy=Strategy.WEIGHTED, threshold=0.78)
        self.assertGreater(weighted.f1, registry.f1)

    def test_metrics_are_in_unit_interval(self):
        for threshold in (0.60, 0.70, 0.75, 0.78, 0.80, 0.85, 0.90):
            metrics = evaluate(self.pairs, strategy=Strategy.WEIGHTED, threshold=threshold)
            for value in (metrics.precision, metrics.recall, metrics.f1, metrics.false_merge_rate):
                self.assertTrue(0.0 <= value <= 1.0)

    def test_corpus_blocking_has_full_recall_and_large_reduction(self):
        metrics = evaluate_blocking_corpus(self.pairs)
        self.assertEqual(metrics.blocking_recall, 1.0)
        self.assertGreater(metrics.reduction_ratio, 0.95)

    def test_operational_triage_only_auto_matches_exact_registry(self):
        auto = next(p for p in self.pairs if p.pair_id == "p01")
        review = next(p for p in self.pairs if p.pair_id == "p03")
        distinct = next(p for p in self.pairs if p.pair_id == "n01")
        uncertain = next(p for p in self.pairs if p.pair_id == "p21")
        self.assertEqual(triage_pair(auto.left, auto.right).disposition, ResolutionDisposition.AUTO_MATCH)
        self.assertEqual(triage_pair(review.left, review.right).disposition, ResolutionDisposition.REVIEW)
        self.assertEqual(triage_pair(distinct.left, distinct.right).disposition, ResolutionDisposition.DISTINCT)
        self.assertEqual(triage_pair(uncertain.left, uncertain.right).disposition, ResolutionDisposition.INSUFFICIENT_EVIDENCE)

    def test_no_negative_pair_is_auto_merged_by_operational_triage(self):
        bad = [
            p.pair_id for p in self.pairs
            if not p.is_duplicate
            and triage_pair(p.left, p.right).disposition is ResolutionDisposition.AUTO_MATCH
        ]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
