from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from searchleads.domain import CandidateFact, Company, EntityRef, EntityType, Evidence, Provenance, Source, SourceType
from searchleads.field_fusion import (
    FusionStatus,
    fuse_candidate_facts,
    fuse_persisted_candidates,
    naive_majority_value,
    persist_fusion_outcome,
)
from searchleads.persistence import SQLiteLeadStore


T1 = datetime(2026, 8, 21, 10, 0, tzinfo=timezone.utc)
T2 = datetime(2026, 8, 21, 11, 0, tzinfo=timezone.utc)
SUBJECT = EntityRef(EntityType.COMPANY, "company-1")


def fact(fid: str, value, *, normalized=None, evidence="ev-1", generated_at=T1, predicate="legal_name"):
    return CandidateFact(
        candidate_fact_id=fid,
        subject=SUBJECT,
        predicate=predicate,
        raw_value=value,
        normalized_value=normalized,
        normalization_rule="test_norm_v1" if normalized is not None else None,
        provenance=Provenance((evidence,), "extract", generated_at=generated_at, agent="test"),
    )


class FieldFusionTests(unittest.TestCase):
    def test_empty_is_explicit(self):
        outcome = fuse_candidate_facts([])
        self.assertEqual(outcome.status, FusionStatus.EMPTY)
        self.assertIsNone(outcome.canonical_fact)
        self.assertIsNone(outcome.conflict)

    def test_single_candidate_becomes_canonical_with_same_value(self):
        source = fact("cf-1", "ACME Ltda.")
        outcome = fuse_candidate_facts([source])
        self.assertEqual(outcome.status, FusionStatus.CANONICAL)
        self.assertEqual(outcome.canonical_fact.value, "ACME Ltda.")
        self.assertEqual(outcome.canonical_fact.candidate_fact_ids, ("cf-1",))

    def test_unanimous_candidates_fuse_and_union_provenance(self):
        outcome = fuse_candidate_facts([
            fact("cf-1", "ACME", evidence="ev-1", generated_at=T1),
            fact("cf-2", "ACME", evidence="ev-2", generated_at=T2),
        ])
        self.assertEqual(outcome.status, FusionStatus.CANONICAL)
        self.assertEqual(outcome.canonical_fact.provenance.evidence_ids, ("ev-1", "ev-2"))
        self.assertEqual(outcome.canonical_fact.provenance.generated_at, T2)

    def test_normalized_equivalence_can_fuse_without_changing_raw_values(self):
        a = fact("cf-1", " ACME  Ltda. ", normalized="ACME Ltda.", evidence="ev-1")
        b = fact("cf-2", "ACME Ltda.", normalized="ACME Ltda.", evidence="ev-2")
        outcome = fuse_candidate_facts([a, b])
        self.assertEqual(outcome.status, FusionStatus.CANONICAL)
        self.assertEqual(outcome.canonical_fact.value, "ACME Ltda.")
        self.assertEqual(a.raw_value, " ACME  Ltda. ")

    def test_disagreement_remains_open_conflict(self):
        outcome = fuse_candidate_facts([
            fact("cf-1", "ACME Tecnologia", evidence="ev-1"),
            fact("cf-2", "ACME Tech", evidence="ev-2"),
        ])
        self.assertEqual(outcome.status, FusionStatus.CONFLICT)
        self.assertIsNone(outcome.canonical_fact)
        self.assertEqual(len(outcome.supports), 2)
        self.assertEqual(outcome.conflict.candidate_fact_ids, ("cf-1", "cf-2"))

    def test_majority_is_diagnostic_not_automatic_truth(self):
        facts = [
            fact("cf-1", "OLD NAME", evidence="ev-1"),
            fact("cf-2", "OLD NAME", evidence="ev-2"),
            fact("cf-3", "OLD NAME", evidence="ev-3"),
            fact("cf-4", "NEW NAME", evidence="ev-4"),
        ]
        outcome = fuse_candidate_facts(facts)
        self.assertEqual(outcome.status, FusionStatus.CONFLICT)
        self.assertEqual(outcome.diagnostic_majority_value, "OLD NAME")
        self.assertEqual(outcome.diagnostic_majority_ratio, 0.75)
        self.assertIsNone(outcome.canonical_fact)

    def test_naive_majority_reports_ratio_but_does_not_persist(self):
        value, ratio = naive_majority_value([
            fact("cf-1", "A", evidence="ev-1"),
            fact("cf-2", "A", evidence="ev-2"),
            fact("cf-3", "B", evidence="ev-3"),
        ])
        self.assertEqual(value, "A")
        self.assertAlmostEqual(ratio, 2 / 3)

    def test_heterogeneous_predicates_are_rejected(self):
        with self.assertRaises(ValueError):
            fuse_candidate_facts([
                fact("cf-1", "ACME", predicate="legal_name"),
                fact("cf-2", "SP", predicate="state"),
            ])

    def test_heterogeneous_subjects_are_rejected(self):
        other = CandidateFact(
            candidate_fact_id="cf-2",
            subject=EntityRef(EntityType.COMPANY, "company-2"),
            predicate="legal_name",
            raw_value="ACME",
            provenance=Provenance(("ev-2",), "extract", generated_at=T1),
        )
        with self.assertRaises(ValueError):
            fuse_candidate_facts([fact("cf-1", "ACME"), other])

    def test_ids_are_deterministic_across_input_order(self):
        a = fact("cf-1", "ACME", evidence="ev-1")
        b = fact("cf-2", "ACME", evidence="ev-2")
        first = fuse_candidate_facts([a, b])
        second = fuse_candidate_facts([b, a])
        self.assertEqual(first.canonical_fact.canonical_fact_id, second.canonical_fact.canonical_fact_id)

    def test_persisted_unanimous_outcome_roundtrips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fusion.sqlite3"
            source = Source("src-1", SourceType.DATASET, "https://example.test")
            company = Company("company-1", created_at=T1)
            f1 = fact("cf-1", "ACME", evidence="ev-1")
            f2 = fact("cf-2", "ACME", evidence="ev-2")
            with SQLiteLeadStore(path) as store:
                store.save_source(source)
                store.save_evidence(Evidence("ev-1", "src-1", T1, {"name": "ACME"}))
                store.save_evidence(Evidence("ev-2", "src-1", T2, {"name": "ACME"}))
                store.save_company(company)
                store.save_candidate_fact(f1)
                store.save_candidate_fact(f2)
                outcome = fuse_persisted_candidates(store, ["cf-1", "cf-2"])
                persist_fusion_outcome(store, outcome)
                cid = outcome.canonical_fact.canonical_fact_id
            with SQLiteLeadStore(path) as reopened:
                loaded = reopened.get_canonical_fact(cid)
                self.assertEqual(loaded.value, "ACME")
                self.assertEqual(loaded.candidate_fact_ids, ("cf-1", "cf-2"))

    def test_persisted_conflict_roundtrips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fusion.sqlite3"
            source = Source("src-1", SourceType.DATASET, "https://example.test")
            company = Company("company-1", created_at=T1)
            f1 = fact("cf-1", "ACME", evidence="ev-1")
            f2 = fact("cf-2", "ACME BRASIL", evidence="ev-2")
            with SQLiteLeadStore(path) as store:
                store.save_source(source)
                store.save_evidence(Evidence("ev-1", "src-1", T1, {"name": "ACME"}))
                store.save_evidence(Evidence("ev-2", "src-1", T2, {"name": "ACME BRASIL"}))
                store.save_company(company)
                store.save_candidate_fact(f1)
                store.save_candidate_fact(f2)
                outcome = fuse_persisted_candidates(store, ["cf-1", "cf-2"])
                persist_fusion_outcome(store, outcome)
                conflict_id = outcome.conflict.conflict_id
            with SQLiteLeadStore(path) as reopened:
                loaded = reopened.get_conflict(conflict_id)
                self.assertEqual(loaded.status.value, "OPEN")
                self.assertEqual(loaded.candidate_fact_ids, ("cf-1", "cf-2"))

    def test_benchmark_conservative_policy_has_zero_false_auto_and_expected_coverage(self):
        scenarios = json.loads((Path(__file__).parent / "fixtures" / "field_fusion_v1.json").read_text(encoding="utf-8"))
        auto = correct = false = truth_known = 0
        for scenario in scenarios:
            expected = scenario["expected_value"]
            if expected is not None:
                truth_known += 1
            facts = []
            for idx, item in enumerate(scenario["candidates"], start=1):
                normalized = item.get("normalized")
                facts.append(CandidateFact(
                    candidate_fact_id=f'{scenario["scenario_id"]}:cf:{idx}',
                    subject=SUBJECT,
                    predicate="legal_name",
                    raw_value=item["raw"],
                    normalized_value=normalized,
                    normalization_rule="benchmark_norm_v1" if normalized is not None else None,
                    provenance=Provenance((item["evidence"],), "benchmark", generated_at=T1),
                ))
            outcome = fuse_candidate_facts(facts)
            if outcome.status is FusionStatus.CANONICAL:
                auto += 1
                if expected is not None and outcome.canonical_fact.value == expected:
                    correct += 1
                else:
                    false += 1
        self.assertEqual(len(scenarios), 32)
        self.assertEqual(truth_known, 28)
        self.assertEqual((auto, correct, false), (18, 18, 0))
        self.assertAlmostEqual(correct / truth_known, 18 / 28)

    def test_benchmark_naive_majority_exposes_correlated_and_unresolved_failures(self):
        scenarios = json.loads((Path(__file__).parent / "fixtures" / "field_fusion_v1.json").read_text(encoding="utf-8"))
        correct = wrong = unresolved_overclaims = 0
        for scenario in scenarios:
            facts = []
            for idx, item in enumerate(scenario["candidates"], start=1):
                normalized = item.get("normalized")
                facts.append(CandidateFact(
                    candidate_fact_id=f'{scenario["scenario_id"]}:cf:{idx}',
                    subject=SUBJECT,
                    predicate="legal_name",
                    raw_value=item["raw"],
                    normalized_value=normalized,
                    normalization_rule="benchmark_norm_v1" if normalized is not None else None,
                    provenance=Provenance((item["evidence"],), "benchmark", generated_at=T1),
                ))
            value, _ = naive_majority_value(facts)
            expected = scenario["expected_value"]
            if expected is None:
                unresolved_overclaims += 1
                wrong += 1
            elif value == expected:
                correct += 1
            else:
                wrong += 1
        self.assertEqual((correct, wrong, unresolved_overclaims), (24, 8, 4))


if __name__ == "__main__":
    unittest.main()
