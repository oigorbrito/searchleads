from __future__ import annotations

import re

import pytest

pytest.importorskip("rigour")

from rigour.ids import CNPJ

from scripts.empirical_observation import write_observation
from searchleads.gap_automation.planning import (
    ActionDisposition,
    ActionKind,
    AutomationInputs,
    GapRequirements,
    _normalize_cnpj as searchleads_normalize_cnpj,
    plan_gap_actions,
)


_COMPACT = re.compile(r"[.\-/\s]")
_BASE = re.compile(r"^[0-9A-Z]{12}$")
_DV = re.compile(r"^[0-9]{2}$")


def _compact(value: str) -> str:
    return _COMPACT.sub("", value).upper()


def _official_digit(values: list[int], weights: list[int]) -> int:
    remainder = sum(value * weight for value, weight in zip(values, weights, strict=True)) % 11
    return 0 if remainder in {0, 1} else 11 - remainder


def _official_cnpj_is_valid(value: str) -> bool:
    """Reference implementation from Receita/Serpro's alphanumeric CNPJ DV spec."""
    compact = _compact(value)
    if len(compact) != 14:
        return False
    base, supplied_dv = compact[:12], compact[12:]
    if _BASE.fullmatch(base) is None or _DV.fullmatch(supplied_dv) is None:
        return False

    values = [ord(character) - 48 for character in base]
    first = _official_digit(values, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    second = _official_digit(values + [first], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return supplied_dv == f"{first}{second}"


CASES = (
    ("00.000.000/E08G-12", True, "official_first_alphanumeric"),
    ("12.ABC.345/01DE-35", True, "official_alphanumeric_example"),
    ("00.000.000/0001-91", True, "legacy_numeric"),
    ("00.000.000/E08G-13", False, "bad_dv_alphanumeric"),
    ("12.ABC.345/01DE-36", False, "bad_dv_alphanumeric"),
    ("00.000.000/0001-92", False, "bad_dv_numeric"),
)


def _searchleads_accepts(value: str) -> bool:
    try:
        searchleads_normalize_cnpj(value)
    except ValueError:
        return False
    return True


def _confusion(results: list[tuple[bool, bool]]) -> tuple[int, int, int, int]:
    tp = fp = tn = fn = 0
    for expected, predicted in results:
        if expected and predicted:
            tp += 1
        elif expected and not predicted:
            fn += 1
        elif not expected and predicted:
            fp += 1
        else:
            tn += 1
    return tp, fp, tn, fn


def test_official_reference_matches_published_valid_and_invalid_cases() -> None:
    for value, expected, _category in CASES:
        assert _official_cnpj_is_valid(value) is expected


def test_cnpj_challengers_are_compared_against_current_official_format() -> None:
    searchleads_results: list[tuple[bool, bool]] = []
    rigour_results: list[tuple[bool, bool]] = []
    case_observations: list[dict[str, object]] = []

    print("CNPJ_VALIDATION_BAKEOFF_V1")
    for value, expected, category in CASES:
        compact = _compact(value)
        searchleads_accepts = _searchleads_accepts(value)
        rigour_normalized = CNPJ.normalize(value)
        rigour_accepts = rigour_normalized is not None
        official_accepts = _official_cnpj_is_valid(value)

        searchleads_results.append((expected, searchleads_accepts))
        rigour_results.append((expected, rigour_accepts))
        case_observations.append(
            {
                "category": category,
                "compact": compact,
                "expected_valid": expected,
                "official_accepts": official_accepts,
                "searchleads_format_accepts": searchleads_accepts,
                "rigour_validates": rigour_accepts,
                "rigour_normalized": rigour_normalized,
            }
        )
        print(
            f"case={category} compact={compact} expected_valid={int(expected)} "
            f"official={int(official_accepts)} searchleads_format_accepts={int(searchleads_accepts)} "
            f"rigour_validates={int(rigour_accepts)} rigour_normalized={rigour_normalized!r}"
        )

    sl_tp, sl_fp, sl_tn, sl_fn = _confusion(searchleads_results)
    rg_tp, rg_fp, rg_tn, rg_fn = _confusion(rigour_results)

    write_observation(
        observation_id="cnpj-validation-oracle-comparison-v1",
        research_question="How do current SearchLeads CNPJ format acceptance and the pinned Rigour validator compare with the declared Receita/Serpro acceptance oracle on frozen official/adversarial cases?",
        method="controlled oracle comparison on frozen official and checksum-invalid cases",
        evidence_class="CONTROLLED_BENCHMARK",
        payload={
            "case_count": len(CASES),
            "cases": case_observations,
            "searchleads_against_official": {"tp": sl_tp, "fp": sl_fp, "tn": sl_tn, "fn": sl_fn},
            "rigour_against_official": {"tp": rg_tp, "fp": rg_fp, "tn": rg_tn, "fn": rg_fn},
            "searchleads_behavior_under_test": "FORMAT_CANONICALIZATION_NOT_CHECKSUM_VALIDATION",
            "acceptance_oracle": "Receita/Serpro alphanumeric CNPJ DV specification as encoded by the reference function",
            "decision_state": "DEFER",
        },
        validity_limits=[
            "six frozen cases do not establish exhaustive conformance",
            "reference implementation must remain traceable to the current official specification",
            "library agreement on this corpus does not by itself authorize production replacement",
        ],
    )

    print(f"searchleads_against_official tp={sl_tp} fp={sl_fp} tn={sl_tn} fn={sl_fn}")
    print(f"rigour_against_official tp={rg_tp} fp={rg_fp} tn={rg_tn} fn={rg_fn}")
    print("searchleads_current_behavior=FORMAT_CANONICALIZATION_NOT_CHECKSUM_VALIDATION")
    print("decision_state=DEFER; official algorithm is the acceptance oracle")

    assert len(searchleads_results) == len(CASES)
    assert len(rigour_results) == len(CASES)


def test_searchleads_compaction_preserves_official_alphanumeric_identifier() -> None:
    assert searchleads_normalize_cnpj("00.000.000/E08G-12") == "00000000E08G12"
    assert searchleads_normalize_cnpj("12.ABC.345/01DE-35") == "12ABC34501DE35"


def test_current_planner_can_schedule_network_acquisition_for_checksum_invalid_cnpj() -> None:
    invalid = "00.000.000/0001-92"
    assert _official_cnpj_is_valid(invalid) is False

    inputs = AutomationInputs(known_cnpj=invalid)
    plan = plan_gap_actions(
        "company:invalid-cnpj-routing-probe",
        GapRequirements(company_fields=("legal_name",)),
        inputs=inputs,
    )

    assert len(plan.actions) == 1
    action = plan.actions[0]
    assert action.disposition is ActionDisposition.READY
    assert action.action_kind is ActionKind.BRASILAPI_POINT_LOOKUP
    assert action.locator == "https://brasilapi.com.br/api/cnpj/v1/00000000000192"

    write_observation(
        observation_id="cnpj-planner-admission-guard-v1",
        research_question="Can the current planner schedule network acquisition for a checksum-invalid but shape-valid CNPJ?",
        method="deterministic planner admission functional probe",
        evidence_class="FUNCTIONAL_PROBE",
        payload={
            "input": invalid,
            "official_checksum_valid": False,
            "searchleads_routing_accepts": True,
            "network_action_ready": True,
            "action_kind": action.action_kind.value,
            "locator": action.locator,
        },
        validity_limits=[
            "single frozen checksum-invalid routing case",
            "does not measure prevalence or network cost in production",
        ],
    )

    print("CNPJ_ACQUISITION_GUARD_BAKEOFF_V1")
    print("official_checksum_valid=NO")
    print("current_searchleads_routing_accepts=YES")
    print("current_searchleads_network_action_ready=YES")
    print("candidate_improvement=validate_identifier_before_network_dispatch")
    print("raw_evidence_and_normalization_must_remain_separate=YES")
