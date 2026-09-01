from __future__ import annotations

from dataclasses import replace
from difflib import SequenceMatcher
import hashlib
import json
from math import sqrt
from pathlib import Path
from typing import Callable

import pytest

pytest.importorskip("rigour")

from rigour.names import normalize_name, remove_org_types
from rigour.text.normalize import Normalize, normalize

from scripts.empirical_observation import write_observation
from searchleads.entity_resolution import CompanyRecord, LabeledPair
from searchleads.entity_resolution import company as company_er


FIXTURE_PATH = "tests/fixtures/company_er_v1.json"
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "company_er_v1.json"
THRESHOLDS = tuple(value / 100 for value in range(50, 96, 2))
NameKey = Callable[[str], str]


_RIGOUR_FLAGS = Normalize.NFKD | Normalize.CASEFOLD | Normalize.NAME


def _fixture_sha256() -> str:
    return hashlib.sha256(FIXTURE.read_bytes()).hexdigest()


def _rigour_default(value: str) -> str:
    return normalize_name(value) or ""


def _rigour_folded(value: str) -> str:
    return normalize(value, _RIGOUR_FLAGS) or ""


def _rigour_strip_org(value: str) -> str:
    prepared = normalize(value, _RIGOUR_FLAGS)
    if not prepared:
        return ""
    stripped = remove_org_types(prepared, normalize_flags=_RIGOUR_FLAGS)
    return normalize(stripped, _RIGOUR_FLAGS) or ""


def _similarity_from_key(left: str | None, right: str | None, key_fn: NameKey) -> float | None:
    if not left or not right:
        return None
    a, b = key_fn(left), key_fn(right)
    if not a or not b:
        return None
    ta, tb = set(a.split()), set(b.split())
    jaccard = len(ta & tb) / len(ta | tb) if ta and tb else 0.0
    return max(SequenceMatcher(None, a, b).ratio(), jaccard)


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
            left=_record(f"{item['id']}-l", item["left"]),
            right=_record(f"{item['id']}-r", item["right"]),
            is_duplicate=item["label"],
            category=item["category"],
        )
        for item in raw
    )


def _split(pairs: tuple[LabeledPair, ...]) -> tuple[tuple[LabeledPair, ...], tuple[LabeledPair, ...]]:
    calibration = tuple(pair for pair in pairs if int(pair.pair_id[1:]) % 3 == 0)
    holdout = tuple(pair for pair in pairs if int(pair.pair_id[1:]) % 3 != 0)
    return calibration, holdout


def _features(pair: LabeledPair, key_fn: NameKey | None):
    features = company_er.compare_features(pair.left, pair.right)
    if key_fn is not None:
        features = replace(
            features,
            name_similarity=_similarity_from_key(pair.left.name, pair.right.name, key_fn),
        )
    return features


def _pair_signal(pair: LabeledPair, key_fn: NameKey | None) -> dict[str, object]:
    features = _features(pair, key_fn)
    return {
        "pair_id": pair.pair_id,
        "category": pair.category,
        "expected_duplicate": pair.is_duplicate,
        "registry_conflict": bool(features.registry_conflict),
        "registry_exact": features.registry_exact,
        "name_similarity": features.name_similarity,
        "weighted_score": company_er._weighted(features),
    }


def _predict(pair: LabeledPair, *, threshold: float, key_fn: NameKey | None) -> bool:
    features = _features(pair, key_fn)
    if features.registry_conflict:
        return False
    if features.registry_exact is True:
        return True
    return company_er._weighted(features) >= threshold


def _metrics(pairs: tuple[LabeledPair, ...], *, threshold: float, key_fn: NameKey | None) -> dict[str, float | int]:
    tp = fp = tn = fn = 0
    for pair in pairs:
        predicted = _predict(pair, threshold=threshold, key_fn=key_fn)
        if pair.is_duplicate and predicted:
            tp += 1
        elif pair.is_duplicate:
            fn += 1
        elif predicted:
            fp += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    beta2 = 0.25
    denom = beta2 * precision + recall
    f05 = (1 + beta2) * precision * recall / denom if denom else 0.0
    false_merge_rate = fp / (fp + tn) if fp + tn else 0.0
    mcc_denom = sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = (tp * tn - fp * fn) / mcc_denom if mcc_denom else 0.0
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": precision, "recall": recall, "f0_5": f05,
        "false_merge_rate": false_merge_rate, "mcc": mcc,
    }


def _select_threshold(calibration: tuple[LabeledPair, ...], key_fn: NameKey | None) -> tuple[float, dict[str, float | int]]:
    candidates = [
        (threshold, _metrics(calibration, threshold=threshold, key_fn=key_fn))
        for threshold in THRESHOLDS
    ]
    return max(
        candidates,
        key=lambda item: (
            float(item[1]["f0_5"]),
            float(item[1]["precision"]),
            float(item[1]["recall"]),
            item[0],
        ),
    )


def _fmt(metrics: dict[str, float | int]) -> str:
    return (
        f"TP={metrics['tp']} FP={metrics['fp']} TN={metrics['tn']} FN={metrics['fn']} "
        f"precision={float(metrics['precision']):.4f} recall={float(metrics['recall']):.4f} "
        f"f0.5={float(metrics['f0_5']):.4f} "
        f"false_merge_rate={float(metrics['false_merge_rate']):.4f} mcc={float(metrics['mcc']):.4f}"
    )


def test_name_normalization_is_measured_as_an_er_feature_ablation() -> None:
    pairs = _pairs()
    calibration, holdout = _split(pairs)
    assert len(pairs) == 54
    assert len(calibration) == 18
    assert len(holdout) == 36

    strategies: dict[str, NameKey | None] = {
        "searchleads_embedded_fold_v1": None,
        "rigour_normalize_name_2_3_1": _rigour_default,
        "rigour_nfkd_casefold_name_2_3_1": _rigour_folded,
        "rigour_nfkd_casefold_name_strip_org_type_2_3_1": _rigour_strip_org,
    }

    structured_results: dict[str, object] = {}
    print("NORMALIZATION_ER_ABLATION_V1")
    print("all_non_name_features_weights_and_rules=UNCHANGED")
    print("holdout=36 calibration=18 baseline_independence=NOT_CERTIFIED")

    for name, key_fn in strategies.items():
        fixed = _metrics(holdout, threshold=0.78, key_fn=key_fn)
        tuned_threshold, calibration_metrics = _select_threshold(calibration, key_fn)
        tuned = _metrics(holdout, threshold=tuned_threshold, key_fn=key_fn)
        threshold_metrics = {
            f"{threshold:.2f}": _metrics(calibration, threshold=threshold, key_fn=key_fn)
            for threshold in THRESHOLDS
        }
        structured_results[name] = {
            "calibration_pair_signals": [_pair_signal(pair, key_fn) for pair in calibration],
            "holdout_pair_signals": [_pair_signal(pair, key_fn) for pair in holdout],
            "fixed_threshold": 0.78,
            "fixed_holdout_metrics": fixed,
            "calibration_metrics_by_threshold": threshold_metrics,
            "calibrated_threshold": tuned_threshold,
            "calibration_metrics_at_selected_threshold": calibration_metrics,
            "tuned_holdout_metrics": tuned,
        }
        print(f"strategy={name} fixed_0.78 {_fmt(fixed)}")
        print(
            f"strategy={name} calibrated_threshold={tuned_threshold:.2f} "
            f"calibration {_fmt(calibration_metrics)}"
        )
        print(f"strategy={name} tuned_holdout {_fmt(tuned)}")

    write_observation(
        observation_id="normalization-er-ablation-v1",
        research_question="How does changing only company-name normalization affect the existing company ER benchmark under fixed and calibration-selected thresholds?",
        method="controlled deterministic feature ablation with calibration/holdout separation",
        evidence_class="CONTROLLED_BENCHMARK",
        payload={
            "fixture": {"path": FIXTURE_PATH, "sha256": _fixture_sha256()},
            "total_pairs": len(pairs),
            "calibration_pairs": len(calibration),
            "holdout_pairs": len(holdout),
            "non_name_features_held_constant": True,
            "threshold_candidates": list(THRESHOLDS),
            "repetition_justification": "The matcher, fixtures, thresholds, and normalization functions are deterministic; raw per-pair signals are retained instead of using repeated identical runs to estimate nonexistent stochastic variance.",
            "strategies": structured_results,
            "decision_state": "DEFER",
        },
        validity_limits=[
            "fixture predates this experiment but baseline independence is not certified",
            "holdout is an internal curated benchmark rather than market-representative data",
            "results do not authorize a production ER replacement without broader validity evidence",
        ],
    )

    print("decision_state=DEFER; normalization effect must be interpreted with false-merge constraints")


def test_normalization_ablation_keeps_registry_conflict_as_hard_negative() -> None:
    pairs = _pairs()
    conflict_pairs = [
        pair for pair in pairs
        if company_er.compare_features(pair.left, pair.right).registry_conflict
    ]
    assert conflict_pairs

    pair_outcomes: list[dict[str, object]] = []
    for pair in conflict_pairs:
        predicted = _predict(pair, threshold=0.50, key_fn=_rigour_strip_org)
        assert predicted is False
        pair_outcomes.append(
            {
                **_pair_signal(pair, _rigour_strip_org),
                "threshold": 0.50,
                "predicted_duplicate": predicted,
            }
        )

    write_observation(
        observation_id="normalization-er-registry-conflict-guard-v1",
        research_question="Can aggressive name normalization override an explicit registry conflict in the current ER rule set?",
        method="deterministic invariant functional probe",
        evidence_class="FUNCTIONAL_PROBE",
        payload={
            "fixture": {"path": FIXTURE_PATH, "sha256": _fixture_sha256()},
            "registry_conflict_pair_count": len(conflict_pairs),
            "threshold": 0.50,
            "strategy": "rigour_nfkd_casefold_name_strip_org_type_2_3_1",
            "registry_conflict_overridden": False,
            "pair_outcomes": pair_outcomes,
        },
        validity_limits=[
            "valid only for the current rule set and frozen fixture",
            "does not estimate registry-data quality in production",
        ],
    )

    print("NORMALIZATION_ER_REGISTRY_GUARD_V1")
    print(f"registry_conflict_pairs={len(conflict_pairs)}")
    print("aggressive_name_normalization_can_override_registry_conflict=NO")
