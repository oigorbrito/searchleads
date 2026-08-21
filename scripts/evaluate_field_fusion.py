#!/usr/bin/env python3
"""Reproduce Work Unit 6 field-fusion benchmark metrics."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from searchleads.domain import CandidateFact, EntityRef, EntityType, Provenance
from searchleads.field_fusion import FusionStatus, fuse_candidate_facts, naive_majority_value

FIXTURE = ROOT / "tests" / "fixtures" / "field_fusion_v1.json"
NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
SUBJECT = EntityRef(EntityType.COMPANY, "benchmark-company")


def load():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def facts_for(scenario):
    result=[]
    for idx, item in enumerate(scenario["candidates"], start=1):
        normalized=item.get("normalized")
        result.append(CandidateFact(
            candidate_fact_id=f'{scenario["scenario_id"]}:cf:{idx}',
            subject=SUBJECT,
            predicate="legal_name",
            raw_value=item["raw"],
            normalized_value=normalized,
            normalization_rule="benchmark_norm_v1" if normalized is not None else None,
            provenance=Provenance((item["evidence"],), "benchmark_extract", generated_at=NOW),
        ))
    return tuple(result)


def main():
    scenarios=load()
    truth_known=sum(s["expected_value"] is not None for s in scenarios)

    conservative_auto=conservative_correct=conservative_false=0
    conservative_conflicts=0
    majority_correct=majority_wrong=majority_overclaims=0

    by_category={}
    for scenario in scenarios:
        facts=facts_for(scenario)
        expected=scenario["expected_value"]
        outcome=fuse_candidate_facts(facts)
        majority_value,_=naive_majority_value(facts)

        cat=by_category.setdefault(scenario["category"], {"n":0,"conservative_auto":0,"majority_correct":0,"majority_wrong":0})
        cat["n"] += 1

        if outcome.status is FusionStatus.CANONICAL:
            conservative_auto += 1
            cat["conservative_auto"] += 1
            if expected is not None and outcome.canonical_fact.value == expected:
                conservative_correct += 1
            else:
                conservative_false += 1
        else:
            conservative_conflicts += 1

        if expected is None:
            majority_overclaims += 1
            majority_wrong += 1
            cat["majority_wrong"] += 1
        elif majority_value == expected:
            majority_correct += 1
            cat["majority_correct"] += 1
        else:
            majority_wrong += 1
            cat["majority_wrong"] += 1

    auto_precision = conservative_correct / conservative_auto if conservative_auto else 0.0
    truth_coverage = conservative_correct / truth_known if truth_known else 0.0
    majority_accuracy = majority_correct / len(scenarios) if scenarios else 0.0
    majority_known_truth_accuracy = majority_correct / truth_known if truth_known else 0.0

    print(f"SCENARIOS={len(scenarios)}")
    print(f"TRUTH_KNOWN={truth_known}")
    print("\nCONSERVATIVE_UNANIMOUS")
    print(f"auto_canonical={conservative_auto}")
    print(f"correct_auto={conservative_correct}")
    print(f"false_auto={conservative_false}")
    print(f"open_conflicts={conservative_conflicts}")
    print(f"auto_precision={auto_precision:.4f}")
    print(f"known_truth_coverage={truth_coverage:.4f}")
    print("\nNAIVE_MAJORITY_DIAGNOSTIC")
    print(f"correct={majority_correct}")
    print(f"wrong_or_overclaim={majority_wrong}")
    print(f"overall_accuracy={majority_accuracy:.4f}")
    print(f"known_truth_accuracy={majority_known_truth_accuracy:.4f}")
    print(f"unresolved_conflict_overclaims={majority_overclaims}")
    print("\nBY_CATEGORY")
    for name in sorted(by_category):
        print(name, by_category[name])


if __name__ == "__main__":
    main()
