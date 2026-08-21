from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from searchleads.entity_resolution import (
    CompanyRecord,
    LabeledPair,
    ResolutionDisposition,
    Strategy,
    evaluate,
    evaluate_blocking_corpus,
    triage_pair,
)

FIXTURE = ROOT / "tests" / "fixtures" / "company_er_v1.json"


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


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def main() -> None:
    pairs = load_pairs()
    positives = sum(pair.is_duplicate for pair in pairs)
    negatives = len(pairs) - positives
    blocking = evaluate_blocking_corpus(pairs)

    print(f"benchmark_pairs={len(pairs)} positives={positives} negatives={negatives}")
    print(
        "blocking "
        f"recall={pct(blocking.blocking_recall)} "
        f"candidate_pairs={blocking.candidate_pairs}/{blocking.total_pairs} "
        f"reduction={pct(blocking.reduction_ratio)}"
    )

    for strategy in (Strategy.REGISTRY_ONLY, Strategy.EXACT_EVIDENCE):
        m = evaluate(pairs, strategy=strategy)
        print(
            f"{strategy.value} TP={m.true_positive} FP={m.false_positive} "
            f"TN={m.true_negative} FN={m.false_negative} "
            f"precision={pct(m.precision)} recall={pct(m.recall)} "
            f"f1={pct(m.f1)} false_merge_rate={pct(m.false_merge_rate)}"
        )

    print("weighted_threshold_sweep")
    for threshold in (0.70, 0.72, 0.74, 0.76, 0.78, 0.80, 0.82, 0.84, 0.86, 0.88, 0.90, 0.92, 0.94, 0.96):
        m = evaluate(pairs, strategy=Strategy.WEIGHTED, threshold=threshold)
        print(
            f"threshold={threshold:.2f} TP={m.true_positive} FP={m.false_positive} "
            f"TN={m.true_negative} FN={m.false_negative} "
            f"precision={pct(m.precision)} recall={pct(m.recall)} "
            f"f1={pct(m.f1)} false_merge_rate={pct(m.false_merge_rate)}"
        )

    counts = {disposition: [0, 0] for disposition in ResolutionDisposition}
    for pair in pairs:
        disposition = triage_pair(pair.left, pair.right).disposition
        counts[disposition][0 if pair.is_duplicate else 1] += 1
    print("operational_triage duplicate_count negative_count")
    for disposition in ResolutionDisposition:
        dup, neg = counts[disposition]
        print(f"{disposition.value} {dup} {neg}")

    review_tp, review_fp = counts[ResolutionDisposition.REVIEW]
    review_yield = review_tp / (review_tp + review_fp) if review_tp + review_fp else 0.0
    auto_tp, auto_fp = counts[ResolutionDisposition.AUTO_MATCH]
    auto_precision = auto_tp / (auto_tp + auto_fp) if auto_tp + auto_fp else 0.0
    auto_recall = auto_tp / positives if positives else 0.0
    covered = auto_tp + review_tp
    print(
        "recommended_policy "
        f"auto_precision={pct(auto_precision)} auto_recall={pct(auto_recall)} "
        f"review_yield={pct(review_yield)} duplicate_coverage_with_review={pct(covered / positives)}"
    )


if __name__ == "__main__":
    main()
