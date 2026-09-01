from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Callable

import pytest

pytest.importorskip("rigour")

from rigour.names import normalize_name, remove_org_types
from rigour.text.normalize import Normalize, normalize

from scripts.empirical_observation import write_observation
from searchleads.domain import CandidateFact
from searchleads.normalization import normalize_candidate_fact


FIXTURE_PATH = "tests/fixtures/company_name_normalization_bakeoff_v1.json"
FIXTURE = Path(__file__).parents[1] / "fixtures" / "company_name_normalization_bakeoff_v1.json"


NameKey = Callable[[str], str]


def _fixture_sha256() -> str:
    return hashlib.sha256(FIXTURE.read_bytes()).hexdigest()


def _searchleads_key(value: str) -> str:
    fact = CandidateFact(
        fact_id="fact:normalization-bakeoff",
        subject_id="company:normalization-bakeoff",
        field_name="legal_name",
        raw_value=value,
        normalized_value=None,
        evidence_ids=("evidence:normalization-bakeoff",),
        provenance_id="provenance:normalization-bakeoff",
    )
    result = normalize_candidate_fact(fact)
    assert result.normalized_fact is not None
    return str(result.normalized_fact.normalized_value)


def _rigour_default_key(value: str) -> str:
    return normalize_name(value) or ""


_RIGOUR_FOLDED_FLAGS = Normalize.NFKD | Normalize.CASEFOLD | Normalize.NAME


def _rigour_folded_key(value: str) -> str:
    return normalize(value, _RIGOUR_FOLDED_FLAGS) or ""


def _rigour_folded_without_org_type_key(value: str) -> str:
    prepared = normalize(value, _RIGOUR_FOLDED_FLAGS)
    if not prepared:
        return ""
    stripped = remove_org_types(
        prepared,
        normalize_flags=_RIGOUR_FOLDED_FLAGS,
    )
    return normalize(stripped, _RIGOUR_FOLDED_FLAGS) or ""


def _load_cases() -> list[dict[str, object]]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    return data


def _case_outcomes(cases: list[dict[str, object]], key_fn: NameKey) -> list[dict[str, object]]:
    outcomes: list[dict[str, object]] = []
    for case in cases:
        left_key = key_fn(str(case["left"]))
        right_key = key_fn(str(case["right"]))
        assert left_key
        assert right_key
        outcomes.append(
            {
                "case_id": str(case["id"]),
                "category": str(case["category"]),
                "expected_same": bool(case["same"]),
                "predicted_same": left_key == right_key,
                "left_key": left_key,
                "right_key": right_key,
            }
        )
    return outcomes


def _metrics(cases: list[dict[str, object]], key_fn: NameKey) -> dict[str, float | int]:
    tp = fp = tn = fn = 0
    for outcome in _case_outcomes(cases, key_fn):
        expected_same = bool(outcome["expected_same"])
        predicted_same = bool(outcome["predicted_same"])
        if expected_same and predicted_same:
            tp += 1
        elif expected_same and not predicted_same:
            fn += 1
        elif not expected_same and predicted_same:
            fp += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    beta2 = 0.25
    denom = beta2 * precision + recall
    f05 = (1 + beta2) * precision * recall / denom if denom else 0.0
    collision_rate = fp / (fp + tn) if fp + tn else 0.0

    mcc_denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = ((tp * tn) - (fp * fn)) / mcc_denom if mcc_denom else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f0_5": f05,
        "false_collision_rate": collision_rate,
        "mcc": mcc,
    }


def _category_errors(cases: list[dict[str, object]], key_fn: NameKey) -> dict[str, tuple[int, int]]:
    errors: dict[str, list[int]] = {}
    for outcome in _case_outcomes(cases, key_fn):
        category = str(outcome["category"])
        total, wrong = errors.setdefault(category, [0, 0])
        total += 1
        wrong += int(bool(outcome["predicted_same"]) != bool(outcome["expected_same"]))
        errors[category] = [total, wrong]
    return {category: (counts[0], counts[1]) for category, counts in sorted(errors.items())}


def test_company_name_normalization_scorecard_does_not_encode_a_winner() -> None:
    cases = _load_cases()
    assert len(cases) == 44
    assert sum(bool(case["same"]) for case in cases) == 20
    assert sum(not bool(case["same"]) for case in cases) == 24

    strategies: dict[str, NameKey] = {
        "searchleads_nfkc_whitespace_v1": _searchleads_key,
        "rigour_normalize_name_2_3_1": _rigour_default_key,
        "rigour_nfkd_casefold_name_2_3_1": _rigour_folded_key,
        "rigour_nfkd_casefold_name_strip_org_type_2_3_1": _rigour_folded_without_org_type_key,
    }

    structured_results: dict[str, object] = {}
    print("COMPANY_NAME_NORMALIZATION_BAKEOFF_V1")
    print("corpus=44 positive=20 negative=24 curated_adversarial=YES")
    for name, key_fn in strategies.items():
        outcomes = _case_outcomes(cases, key_fn)
        metrics = _metrics(cases, key_fn)
        category_errors = _category_errors(cases, key_fn)
        structured_results[name] = {
            "case_outcomes": outcomes,
            "metrics": metrics,
            "category_errors": {
                category: {"total": total, "errors": wrong}
                for category, (total, wrong) in category_errors.items()
            },
        }
        print(
            f"strategy={name} tp={metrics['tp']} fp={metrics['fp']} "
            f"tn={metrics['tn']} fn={metrics['fn']} "
            f"precision={metrics['precision']:.6f} recall={metrics['recall']:.6f} "
            f"f0.5={metrics['f0_5']:.6f} false_collision_rate={metrics['false_collision_rate']:.6f} "
            f"mcc={metrics['mcc']:.6f}"
        )
        for category, (total, wrong) in category_errors.items():
            print(f"category strategy={name} category={category} total={total} errors={wrong}")

    write_observation(
        observation_id="normalization-key-comparison-v1",
        research_question="How do the declared company-name normalization strategies behave on the frozen adversarial equivalence/collision corpus?",
        method="controlled deterministic benchmark on a frozen curated adversarial corpus",
        evidence_class="CONTROLLED_BENCHMARK",
        payload={
            "corpus": {
                "path": FIXTURE_PATH,
                "sha256": _fixture_sha256(),
                "cases": len(cases),
                "positive": sum(bool(case["same"]) for case in cases),
                "negative": sum(not bool(case["same"]) for case in cases),
                "curated_adversarial": True,
            },
            "repetition_justification": "Strategies are deterministic pure transformations over a fixed corpus; repeated identical executions do not estimate stochastic variance.",
            "strategies": structured_results,
            "decision_state": "DEFER",
        },
        validity_limits=[
            "curated corpus is not a market-representative sample",
            "normalized-key equality is a feature comparison, not entity identity",
            "baseline independence is not established by this corpus alone",
        ],
    )

    print("decision_state=DEFER; outcome must be interpreted with collision cost and downstream ER")
    print("normalized_string_equality_is_not_entity_identity=YES")


def test_legal_form_removal_is_measured_as_a_collision_tradeoff() -> None:
    cases = [case for case in _load_cases() if case["category"] == "legal_form_collision_guard"]
    assert len(cases) == 4
    assert all(not bool(case["same"]) for case in cases)

    folded_outcomes = _case_outcomes(cases, _rigour_folded_key)
    stripped_outcomes = _case_outcomes(cases, _rigour_folded_without_org_type_key)
    folded = _metrics(cases, _rigour_folded_key)
    stripped = _metrics(cases, _rigour_folded_without_org_type_key)

    write_observation(
        observation_id="normalization-legal-form-collision-guard-v1",
        research_question="Does organization-type removal change false collisions on the frozen legal-form collision guards?",
        method="controlled deterministic feature-ablation benchmark",
        evidence_class="CONTROLLED_BENCHMARK",
        payload={
            "fixture": {"path": FIXTURE_PATH, "sha256": _fixture_sha256()},
            "case_count": len(cases),
            "all_cases_are_negative_controls": True,
            "repetition_justification": "Both transformations are deterministic on the fixed four-case guard corpus.",
            "rigour_folded": {
                "case_outcomes": folded_outcomes,
                "false_collisions": int(folded["fp"]),
            },
            "rigour_strip_org_type": {
                "case_outcomes": stripped_outcomes,
                "false_collisions": int(stripped["fp"]),
            },
        },
        validity_limits=[
            "four curated collision guards only",
            "does not estimate production false-merge rate",
        ],
    )

    print("LEGAL_FORM_REMOVAL_COLLISION_GUARD_V1")
    print(f"rigour_folded_false_collisions={folded['fp']}/4")
    print(f"rigour_strip_org_type_false_collisions={stripped['fp']}/4")
    print("interpretation=legal-form stripping is optional feature engineering, never merge authority")

    assert 0 <= int(folded["fp"]) <= 4
    assert 0 <= int(stripped["fp"]) <= 4
