from __future__ import annotations

import csv
from dataclasses import dataclass
from itertools import product
from math import sqrt
from pathlib import Path
from time import perf_counter

import pytest

pytest.importorskip("followthemoney")
pytest.importorskip("nomenklatura")

from followthemoney import EntityProxy
from nomenklatura.matching.logic_v2.model import LogicV2

from searchleads.entity_resolution import CompanyRecord, Strategy, resolve_pair


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / ".external" / "dedupe" / "benchmarks" / "benchmarks" / "datasets"
DATA1 = DATASET / "restaurant-1.csv"
DATA2 = DATASET / "restaurant-2.csv"

if not DATA1.exists() or not DATA2.exists():
    pytest.skip("pinned Dedupe canonical dataset is only checked out in the chassis workflow", allow_module_level=True)


@dataclass(frozen=True, slots=True)
class Metrics:
    tp: int
    fp: int
    tn: int
    fn: int
    precision: float
    recall: float
    f05: float
    false_merge_rate: float
    mcc: float


def _clean(value: str | None) -> str:
    return (value or "").strip().strip("\"").strip("'").strip()


def _load(path: Path, prefix: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            records.append(
                {
                    "record_id": f"{prefix}:{index}",
                    "name": _clean(row.get("name")),
                    "address": _clean(row.get("address")),
                    "city": _clean(row.get("city")),
                    "unique_id": _clean(row.get("unique_id")),
                }
            )
    return records


def _combined_address(record: dict[str, str]) -> str | None:
    parts = [record["address"], record["city"]]
    values = [part for part in parts if part]
    return ", ".join(values) if values else None


def _searchleads_record(record: dict[str, str]) -> CompanyRecord:
    return CompanyRecord(
        record_id=record["record_id"],
        name=record["name"] or None,
        address=_combined_address(record),
        city=record["city"] or None,
    )


def _ftm_record(record: dict[str, str]) -> EntityProxy:
    properties: dict[str, list[str]] = {"name": [record["name"]]}
    if address := _combined_address(record):
        properties["address"] = [address]
    return EntityProxy.from_dict(
        {"id": record["record_id"], "schema": "Company", "properties": properties},
        cleaned=False,
    )


def _metrics(labels: list[bool], predictions: list[bool]) -> Metrics:
    tp = fp = tn = fn = 0
    for label, prediction in zip(labels, predictions, strict=True):
        if label and prediction:
            tp += 1
        elif label:
            fn += 1
        elif prediction:
            fp += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    beta2 = 0.25
    f05 = (
        (1 + beta2) * precision * recall / (beta2 * precision + recall)
        if precision + recall
        else 0.0
    )
    false_merge_rate = fp / (fp + tn) if fp + tn else 0.0
    denominator = sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = (tp * tn - fp * fn) / denominator if denominator else 0.0
    return Metrics(tp, fp, tn, fn, precision, recall, f05, false_merge_rate, mcc)


def _fmt(metrics: Metrics) -> str:
    return (
        f"TP={metrics.tp} FP={metrics.fp} TN={metrics.tn} FN={metrics.fn} "
        f"precision={metrics.precision:.4f} recall={metrics.recall:.4f} "
        f"f05={metrics.f05:.4f} false_merge_rate={metrics.false_merge_rate:.6f} "
        f"mcc={metrics.mcc:.4f}"
    )


def test_external_canonical_record_linkage_generalization() -> None:
    left_raw = _load(DATA1, "r1")
    right_raw = _load(DATA2, "r2")
    assert left_raw and right_raw
    assert all(record["unique_id"] for record in left_raw + right_raw)

    left_sl = {record["record_id"]: _searchleads_record(record) for record in left_raw}
    right_sl = {record["record_id"]: _searchleads_record(record) for record in right_raw}
    left_ftm = {record["record_id"]: _ftm_record(record) for record in left_raw}
    right_ftm = {record["record_id"]: _ftm_record(record) for record in right_raw}

    labels: list[bool] = []
    sl_predictions: list[bool] = []
    nk_predictions: list[bool] = []

    sl_started = perf_counter()
    pair_keys: list[tuple[str, str, bool]] = []
    for left, right in product(left_raw, right_raw):
        label = left["unique_id"] == right["unique_id"]
        pair_keys.append((left["record_id"], right["record_id"], label))
        labels.append(label)
        sl_predictions.append(
            resolve_pair(
                left_sl[left["record_id"]],
                right_sl[right["record_id"]],
                strategy=Strategy.WEIGHTED,
                threshold=0.78,
            ).is_match
        )
    sl_elapsed = perf_counter() - sl_started

    model = LogicV2()
    config = model.default_config()
    nk_started = perf_counter()
    for left_id, right_id, _ in pair_keys:
        score = float(model.compare(left_ftm[left_id], right_ftm[right_id], config).score)
        nk_predictions.append(score >= 0.70)
    nk_elapsed = perf_counter() - nk_started

    sl_metrics = _metrics(labels, sl_predictions)
    nk_metrics = _metrics(labels, nk_predictions)
    pair_count = len(labels)
    positive_count = sum(labels)

    assert pair_count == len(left_raw) * len(right_raw)
    assert positive_count > 0
    assert sl_metrics.tp + sl_metrics.fn == positive_count
    assert nk_metrics.tp + nk_metrics.fn == positive_count

    print("EXTERNAL_CANONICAL_ER_BAKEOFF_V1")
    print("source=dedupeio/dedupe canonical restaurant linkage dataset")
    print("source_commit=3f61e79102910bd355e920a2df7e44c14c9cb247")
    print("ground_truth=unique_id (never supplied to either matcher)")
    print(f"left={len(left_raw)} right={len(right_raw)} pairs={pair_count} positives={positive_count}")
    print(f"searchleads_weighted_0.78 {_fmt(sl_metrics)} elapsed_s={sl_elapsed:.3f} pairs_s={pair_count / sl_elapsed:.1f}")
    print(f"nomenklatura_logic_v2_0.70 {_fmt(nk_metrics)} elapsed_s={nk_elapsed:.3f} pairs_s={pair_count / nk_elapsed:.1f}")
    print("scope=external generic organization linkage; not Brazil-specific commercial validation")
