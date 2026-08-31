from __future__ import annotations

from dataclasses import dataclass
import json
from math import sqrt
from pathlib import Path

import pytest

pytest.importorskip("followthemoney")
pytest.importorskip("nomenklatura")

from followthemoney import EntityProxy
from nomenklatura.matching.logic_v2.model import LogicV2

from searchleads.entity_resolution import CompanyRecord, LabeledPair, Strategy, resolve_pair


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "company_er_v1.json"
THRESHOLDS = tuple(value / 100 for value in range(50, 96, 2))


@dataclass(frozen=True, slots=True)
class BinaryMetrics:
    tp: int
    fp: int
    tn: int
    fn: int
    precision: float
    recall: float
    f1: float
    f05: float
    false_merge_rate: float
    mcc: float


def _record(record_id: str, raw: dict[str, object]) -> CompanyRecord:
    values = dict(raw)
    if values.get("registry_id") is not None:
        values["registry_namespace"] = "br:cnpj"
    return CompanyRecord(record_id=record_id, **values)


def _load_pairs() -> tuple[LabeledPair, ...]:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return tuple(
        LabeledPair(
            pair_id=item["id"],
            left=_record(f"{item['id']}-l", item["left"]),
            right=_record(f"{item['id']}-r", item["right"]),
            is_duplicate=item["label"],
            category=item["category"],
        )
        for item in raw
    )


def _website(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return value
    return f"https://{value}"


def _address(record: CompanyRecord) -> str | None:
    parts = [record.address, record.city, record.state]
    compact = [str(part).strip() for part in parts if part is not None and str(part).strip()]
    return ", ".join(compact) if compact else None


def _ftm_company(record: CompanyRecord) -> EntityProxy:
    props: dict[str, list[str]] = {"name": [record.name or record.record_id]}
    if record.registry_id:
        props["registrationNumber"] = [record.registry_id]
    if website := _website(record.domain):
        props["website"] = [website]
    if record.phone:
        props["phone"] = [record.phone]
    if address := _address(record):
        props["address"] = [address]
    data = {"id": record.record_id, "schema": "Company", "properties": props}
    return EntityProxy.from_dict(data, cleaned=False)


def _metrics(labels: list[bool], predictions: list[bool]) -> BinaryMetrics:
    tp = fp = tn = fn = 0
    for label, predicted in zip(labels, predictions, strict=True):
        if label and predicted:
            tp += 1
        elif label:
            fn += 1
        elif predicted:
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
    return BinaryMetrics(tp, fp, tn, fn, precision, recall, f1, f05, false_merge_rate, mcc)


def _wilson(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    radius = z * sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return max(0.0, centre - radius), min(1.0, centre + radius)


def _nomenklatura_scores(pairs: tuple[LabeledPair, ...]) -> dict[str, float]:
    model = LogicV2()
    config = model.default_config()
    scores: dict[str, float] = {}
    for pair in pairs:
        result = model.compare(_ftm_company(pair.left), _ftm_company(pair.right), config)
        score = float(result.score)
        assert -1.0 <= score <= 1.5
        scores[pair.pair_id] = score
    return scores


def _split(pairs: tuple[LabeledPair, ...]) -> tuple[tuple[LabeledPair, ...], tuple[LabeledPair, ...]]:
    calibration = tuple(pair for pair in pairs if int(pair.pair_id[1:]) % 3 == 0)
    holdout = tuple(pair for pair in pairs if int(pair.pair_id[1:]) % 3 != 0)
    assert {pair.pair_id for pair in calibration}.isdisjoint(pair.pair_id for pair in holdout)
    assert len(calibration) + len(holdout) == len(pairs)
    assert any(pair.is_duplicate for pair in calibration)
    assert any(not pair.is_duplicate for pair in calibration)
    assert any(pair.is_duplicate for pair in holdout)
    assert any(not pair.is_duplicate for pair in holdout)
    return calibration, holdout


def _at_threshold(
    pairs: tuple[LabeledPair, ...], scores: dict[str, float], threshold: float
) -> BinaryMetrics:
    labels = [pair.is_duplicate for pair in pairs]
    predictions = [scores[pair.pair_id] >= threshold for pair in pairs]
    return _metrics(labels, predictions)


def _select_threshold(calibration: tuple[LabeledPair, ...], scores: dict[str, float]) -> tuple[float, BinaryMetrics]:
    candidates = [(threshold, _at_threshold(calibration, scores, threshold)) for threshold in THRESHOLDS]
    # F0.5 deliberately weights precision more than recall because false company
    # merges contaminate all downstream evidence, contacts and qualification.
    return max(candidates, key=lambda item: (item[1].f05, item[1].precision, item[1].recall, item[0]))


def _searchleads_metrics(pairs: tuple[LabeledPair, ...], strategy: Strategy, threshold: float = 0.78) -> BinaryMetrics:
    labels = [pair.is_duplicate for pair in pairs]
    predictions = [
        resolve_pair(pair.left, pair.right, strategy=strategy, threshold=threshold).is_match
        for pair in pairs
    ]
    return _metrics(labels, predictions)


def _fmt(metrics: BinaryMetrics) -> str:
    p_ci = _wilson(metrics.tp, metrics.tp + metrics.fp)
    r_ci = _wilson(metrics.tp, metrics.tp + metrics.fn)
    return (
        f"TP={metrics.tp} FP={metrics.fp} TN={metrics.tn} FN={metrics.fn} "
        f"precision={metrics.precision:.4f} precision95=[{p_ci[0]:.4f},{p_ci[1]:.4f}] "
        f"recall={metrics.recall:.4f} recall95=[{r_ci[0]:.4f},{r_ci[1]:.4f}] "
        f"f05={metrics.f05:.4f} f1={metrics.f1:.4f} "
        f"false_merge_rate={metrics.false_merge_rate:.4f} mcc={metrics.mcc:.4f}"
    )


def test_company_er_challenger_uses_same_labels_and_calibrates_without_holdout_labels() -> None:
    pairs = _load_pairs()
    calibration, holdout = _split(pairs)
    scores = _nomenklatura_scores(pairs)

    selected_threshold, calibration_metrics = _select_threshold(calibration, scores)
    challenger_holdout = _at_threshold(holdout, scores, selected_threshold)
    upstream_default_holdout = _at_threshold(holdout, scores, 0.70)
    searchleads_weighted = _searchleads_metrics(holdout, Strategy.WEIGHTED, threshold=0.78)
    searchleads_exact = _searchleads_metrics(holdout, Strategy.EXACT_EVIDENCE)

    assert len(pairs) == 54
    assert len(calibration) == 18
    assert len(holdout) == 36
    assert selected_threshold in THRESHOLDS
    assert set(scores) == {pair.pair_id for pair in pairs}

    print("CHASSIS_ER_BAKEOFF_V1")
    print("ground_truth=tests/fixtures/company_er_v1.json pairs=54 calibration=18 holdout=36")
    print("challenger=Nomenklatura LogicV2 4.14.0 local_training=none")
    print("baseline_holdout_independence=NOT_CERTIFIED (SearchLeads fixture predates this split)")
    print(f"nomenklatura_selected_threshold={selected_threshold:.2f}")
    print(f"nomenklatura_calibration {_fmt(calibration_metrics)}")
    print(f"nomenklatura_holdout_tuned {_fmt(challenger_holdout)}")
    print(f"nomenklatura_holdout_upstream_0.70 {_fmt(upstream_default_holdout)}")
    print(f"searchleads_holdout_weighted_0.78 {_fmt(searchleads_weighted)}")
    print(f"searchleads_holdout_exact_evidence {_fmt(searchleads_exact)}")


def test_company_er_challenger_reports_error_categories_without_asserting_a_winner() -> None:
    pairs = _load_pairs()
    calibration, holdout = _split(pairs)
    scores = _nomenklatura_scores(pairs)
    selected_threshold, _ = _select_threshold(calibration, scores)

    external_errors: list[str] = []
    baseline_errors: list[str] = []
    for pair in holdout:
        external = scores[pair.pair_id] >= selected_threshold
        baseline = resolve_pair(
            pair.left, pair.right, strategy=Strategy.WEIGHTED, threshold=0.78
        ).is_match
        if external != pair.is_duplicate:
            external_errors.append(f"{pair.pair_id}:{pair.category}:{'FP' if external else 'FN'}")
        if baseline != pair.is_duplicate:
            baseline_errors.append(f"{pair.pair_id}:{pair.category}:{'FP' if baseline else 'FN'}")

    print("CHASSIS_ER_ERROR_ANALYSIS_V1")
    print("nomenklatura_errors=" + (",".join(external_errors) if external_errors else "NONE"))
    print("searchleads_errors=" + (",".join(baseline_errors) if baseline_errors else "NONE"))

    # The experiment is discovery-oriented. It must not encode the desired winner
    # into the test assertions; numerical results decide later architecture work.
    assert len(external_errors) <= len(holdout)
    assert len(baseline_errors) <= len(holdout)
