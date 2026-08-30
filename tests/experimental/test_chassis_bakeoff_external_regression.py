from __future__ import annotations

import csv
from dataclasses import dataclass
from hashlib import sha256
from itertools import product
from math import sqrt
from pathlib import Path
from time import perf_counter

import numpy as np
import pytest

pytest.importorskip("followthemoney")
pytest.importorskip("nomenklatura")

from followthemoney import EntityProxy
from nomenklatura.matching import EntityResolveRegression, RegressionV1

from searchleads.entity_resolution import CompanyRecord, Strategy, resolve_pair


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / ".external" / "dedupe" / "benchmarks" / "benchmarks" / "datasets"
DATA1 = DATASET / "restaurant-1.csv"
DATA2 = DATASET / "restaurant-2.csv"
NEGATIVE_SAMPLE_SIZE = 10_000

if not DATA1.exists() or not DATA2.exists():
    pytest.skip(
        "pinned Dedupe canonical dataset is only checked out in the chassis workflow",
        allow_module_level=True,
    )


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
    return (value or "").strip().strip('"').strip("'").strip()


def _load(path: Path, prefix: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            rows.append(
                {
                    "record_id": f"{prefix}:{index}",
                    "name": _clean(row.get("name")),
                    "address": _clean(row.get("address")),
                    "city": _clean(row.get("city")),
                    "unique_id": _clean(row.get("unique_id")),
                }
            )
    return rows


def _address(row: dict[str, str]) -> str | None:
    values = [value for value in (row["address"], row["city"]) if value]
    return ", ".join(values) if values else None


def _sl(row: dict[str, str]) -> CompanyRecord:
    return CompanyRecord(
        record_id=row["record_id"],
        name=row["name"] or None,
        address=_address(row),
        city=row["city"] or None,
    )


def _ftm(row: dict[str, str]) -> EntityProxy:
    props: dict[str, list[str]] = {"name": [row["name"]]}
    if address := _address(row):
        props["address"] = [address]
    return EntityProxy.from_dict(
        {"id": row["record_id"], "schema": "Company", "properties": props},
        cleaned=False,
    )


def _stable_rank(left_id: str, right_id: str) -> bytes:
    return sha256(f"{left_id}|{right_id}".encode()).digest()


def _evaluation_pairs(
    left: list[dict[str, str]], right: list[dict[str, str]]
) -> list[tuple[dict[str, str], dict[str, str], bool]]:
    positives: list[tuple[dict[str, str], dict[str, str], bool]] = []
    negatives: list[tuple[bytes, dict[str, str], dict[str, str], bool]] = []
    for lrow, rrow in product(left, right):
        label = lrow["unique_id"] == rrow["unique_id"]
        if label:
            positives.append((lrow, rrow, True))
        else:
            negatives.append((_stable_rank(lrow["record_id"], rrow["record_id"]), lrow, rrow, False))
    negatives.sort(key=lambda item: item[0])
    sampled = [(lrow, rrow, label) for _, lrow, rrow, label in negatives[:NEGATIVE_SAMPLE_SIZE]]
    return positives + sampled


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


def _regression_predictions(algorithm, entities, threshold: float = 0.50) -> tuple[list[bool], float]:
    started = perf_counter()
    encoded = [algorithm.encode_pair(left, right) for left, right in entities]
    pipe, _ = algorithm.load()
    probabilities = pipe.predict_proba(np.asarray(encoded))[:, 1]
    elapsed = perf_counter() - started
    return [bool(score >= threshold) for score in probabilities], elapsed


def test_external_ground_truth_compares_default_and_dedupe_regression_models() -> None:
    left = _load(DATA1, "r1")
    right = _load(DATA2, "r2")
    pairs = _evaluation_pairs(left, right)
    labels = [label for _, _, label in pairs]
    positives = sum(labels)
    negatives = len(labels) - positives

    sl_left = {row["record_id"]: _sl(row) for row in left}
    sl_right = {row["record_id"]: _sl(row) for row in right}
    ftm_left = {row["record_id"]: _ftm(row) for row in left}
    ftm_right = {row["record_id"]: _ftm(row) for row in right}

    sl_started = perf_counter()
    sl_predictions = [
        resolve_pair(
            sl_left[lrow["record_id"]],
            sl_right[rrow["record_id"]],
            strategy=Strategy.WEIGHTED,
            threshold=0.78,
        ).is_match
        for lrow, rrow, _ in pairs
    ]
    sl_elapsed = perf_counter() - sl_started

    entity_pairs = [
        (ftm_left[lrow["record_id"]], ftm_right[rrow["record_id"]])
        for lrow, rrow, _ in pairs
    ]
    default_predictions, default_elapsed = _regression_predictions(RegressionV1, entity_pairs)
    er_predictions, er_elapsed = _regression_predictions(EntityResolveRegression, entity_pairs)

    sl_metrics = _metrics(labels, sl_predictions)
    default_metrics = _metrics(labels, default_predictions)
    er_metrics = _metrics(labels, er_predictions)

    assert positives > 0
    assert negatives == min(NEGATIVE_SAMPLE_SIZE, len(left) * len(right) - positives)

    print("EXTERNAL_REGRESSION_ER_BAKEOFF_V1")
    print("source=dedupeio/dedupe canonical restaurant linkage dataset")
    print("source_commit=3f61e79102910bd355e920a2df7e44c14c9cb247")
    print("ground_truth=unique_id never supplied to matchers")
    print(f"positives=ALL:{positives} negatives=DETERMINISTIC_SAMPLE:{negatives}")
    print("no_local_training=true neutral_probability_threshold=0.50")
    print(
        f"searchleads_weighted_0.78 {_fmt(sl_metrics)} "
        f"elapsed_s={sl_elapsed:.3f} pairs_s={len(pairs) / sl_elapsed:.1f}"
    )
    print(
        f"nomenklatura_regression_v1_0.50 {_fmt(default_metrics)} "
        f"elapsed_s={default_elapsed:.3f} pairs_s={len(pairs) / default_elapsed:.1f}"
    )
    print(
        f"nomenklatura_entity_resolve_0.50 {_fmt(er_metrics)} "
        f"elapsed_s={er_elapsed:.3f} pairs_s={len(pairs) / er_elapsed:.1f}"
    )
    print("false_merge_rate_for_regression_test=estimated_on_deterministic_negative_sample")
    print("scope=external generic organization linkage; not Brazil-specific commercial validation")
