from __future__ import annotations

from dataclasses import dataclass
import json
from math import isfinite, sqrt
from pathlib import Path

import pytest

pytest.importorskip("followthemoney")
pytest.importorskip("nomenklatura")

from followthemoney import EntityProxy
from nomenklatura.matching import (
    DefaultAlgorithm,
    DedupeAlgorithm,
    EntityResolveRegression,
    LogicV2,
    RegressionV1,
)

from searchleads.entity_resolution import CompanyRecord, LabeledPair, Strategy, resolve_pair


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "company_er_v1.json"
THRESHOLDS = tuple(value / 100 for value in range(30, 96, 2))


@dataclass(frozen=True, slots=True)
class Metrics:
    tp: int
    fp: int
    tn: int
    fn: int
    precision: float
    recall: float
    f05: float
    f1: float
    false_merge_rate: float
    mcc: float


def _record(record_id: str, raw: dict[str, object]) -> CompanyRecord:
    values = dict(raw)
    if values.get("registry_id") is not None:
        values["registry_namespace"] = "br:cnpj"
    return CompanyRecord(record_id=record_id, **values)


def _pairs() -> tuple[LabeledPair, ...]:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return tuple(
        LabeledPair(
            pair_id=item["id"],
            left=_record(f"{item['id']}:left", item["left"]),
            right=_record(f"{item['id']}:right", item["right"]),
            is_duplicate=item["label"],
            category=item["category"],
        )
        for item in raw
    )


def _website(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    return value if value.startswith(("http://", "https://")) else f"https://{value}"


def _entity(record: CompanyRecord) -> EntityProxy:
    props: dict[str, list[str]] = {"name": [record.name or record.record_id]}
    if record.registry_id:
        props["registrationNumber"] = [record.registry_id]
    if website := _website(record.domain):
        props["website"] = [website]
    if record.phone:
        props["phone"] = [record.phone]
    address = ", ".join(
        str(value).strip()
        for value in (record.address, record.city, record.state)
        if value is not None and str(value).strip()
    )
    if address:
        props["address"] = [address]
    return EntityProxy.from_dict(
        {"id": record.record_id, "schema": "Company", "properties": props},
        cleaned=False,
    )


def _split(pairs: tuple[LabeledPair, ...]) -> tuple[tuple[LabeledPair, ...], tuple[LabeledPair, ...]]:
    calibration = tuple(pair for pair in pairs if int(pair.pair_id[1:]) % 3 == 0)
    holdout = tuple(pair for pair in pairs if int(pair.pair_id[1:]) % 3 != 0)
    assert len(calibration) == 18
    assert len(holdout) == 36
    return calibration, holdout


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
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    beta2 = 0.25
    f05 = (
        (1 + beta2) * precision * recall / (beta2 * precision + recall)
        if precision + recall
        else 0.0
    )
    false_merge_rate = fp / (fp + tn) if fp + tn else 0.0
    denominator = sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = (tp * tn - fp * fn) / denominator if denominator else 0.0
    return Metrics(tp, fp, tn, fn, precision, recall, f05, f1, false_merge_rate, mcc)


def _scores(algorithm, pairs: tuple[LabeledPair, ...]) -> dict[str, float]:
    config = algorithm.default_config()
    values: dict[str, float] = {}
    for pair in pairs:
        score = float(algorithm.compare(_entity(pair.left), _entity(pair.right), config).score)
        assert isfinite(score)
        values[pair.pair_id] = score
    return values


def _at_threshold(
    pairs: tuple[LabeledPair, ...], scores: dict[str, float], threshold: float
) -> Metrics:
    labels = [pair.is_duplicate for pair in pairs]
    predictions = [scores[pair.pair_id] >= threshold for pair in pairs]
    return _metrics(labels, predictions)


def _choose(calibration: tuple[LabeledPair, ...], scores: dict[str, float]) -> tuple[float, Metrics]:
    candidates = [(threshold, _at_threshold(calibration, scores, threshold)) for threshold in THRESHOLDS]
    return max(
        candidates,
        key=lambda item: (
            item[1].f05,
            item[1].precision,
            item[1].mcc,
            item[1].recall,
            item[0],
        ),
    )


def _searchleads(pairs: tuple[LabeledPair, ...]) -> Metrics:
    labels = [pair.is_duplicate for pair in pairs]
    predictions = [
        resolve_pair(pair.left, pair.right, strategy=Strategy.WEIGHTED, threshold=0.78).is_match
        for pair in pairs
    ]
    return _metrics(labels, predictions)


def _fmt(metrics: Metrics) -> str:
    return (
        f"TP={metrics.tp} FP={metrics.fp} TN={metrics.tn} FN={metrics.fn} "
        f"precision={metrics.precision:.4f} recall={metrics.recall:.4f} "
        f"f05={metrics.f05:.4f} f1={metrics.f1:.4f} "
        f"false_merge_rate={metrics.false_merge_rate:.4f} mcc={metrics.mcc:.4f}"
    )


def test_upstream_algorithm_roles_are_verified_from_installed_package() -> None:
    assert DefaultAlgorithm is RegressionV1
    assert DedupeAlgorithm is EntityResolveRegression
    assert LogicV2.NAME == "logic-v2"
    assert RegressionV1.NAME == "regression-v1"
    assert EntityResolveRegression.NAME == "er-unstable"


def test_nomenklatura_algorithm_bakeoff_uses_common_calibration_and_holdout() -> None:
    pairs = _pairs()
    calibration, holdout = _split(pairs)

    print("NOMENKLATURA_ALGORITHM_BAKEOFF_V1")
    print("ground_truth=company_er_v1 pairs=54 calibration=18 holdout=36")
    print("selection_metric=F0.5 then precision then MCC then recall")
    print("searchleads_baseline_holdout_independence=NOT_CERTIFIED")
    print(f"searchleads_weighted_0.78 {_fmt(_searchleads(holdout))}")

    for algorithm in (LogicV2, RegressionV1, EntityResolveRegression):
        scores = _scores(algorithm, pairs)
        threshold, calibration_metrics = _choose(calibration, scores)
        holdout_metrics = _at_threshold(holdout, scores, threshold)
        neutral_threshold = 0.70 if algorithm is LogicV2 else 0.50
        neutral_metrics = _at_threshold(holdout, scores, neutral_threshold)

        print(
            f"algorithm={algorithm.NAME} selected_threshold={threshold:.2f} "
            f"calibration={_fmt(calibration_metrics)}"
        )
        print(f"algorithm={algorithm.NAME} tuned_holdout={_fmt(holdout_metrics)}")
        print(
            f"algorithm={algorithm.NAME} neutral_threshold={neutral_threshold:.2f} "
            f"neutral_holdout={_fmt(neutral_metrics)}"
        )

        assert set(scores) == {pair.pair_id for pair in pairs}
        assert threshold in THRESHOLDS


def test_regression_models_expose_feature_documentation() -> None:
    default_docs = RegressionV1.get_feature_docs()
    er_docs = EntityResolveRegression.get_feature_docs()

    assert "phone_match" in default_docs
    assert "identifier_match" in default_docs
    assert "address_match" in default_docs
    assert "contact_match" in er_docs
    assert "strong_identifier_match" in er_docs
    assert "address_match" in er_docs

    print("NOMENKLATURA_FEATURE_EVIDENCE_V1")
    print("regression_v1_features=" + ",".join(default_docs))
    print("entity_resolve_features=" + ",".join(er_docs))
