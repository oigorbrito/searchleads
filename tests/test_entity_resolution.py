from __future__ import annotations

import json
from pathlib import Path

import pytest

from searchleads.entity_resolution import (
    CompanyRecord,
    LabeledPair,
    ResolutionDisposition,
    Strategy,
    blocking_keys,
    compare_features,
    evaluate,
    evaluate_blocking,
    evaluate_blocking_corpus,
    resolve_pair,
    triage_pair,
)

FIXTURE = Path(__file__).parent / "fixtures" / "company_er_v1.json"


def _record(record_id: str, raw: dict[str, object]) -> CompanyRecord:
    values = dict(raw)
    if values.get("registry_id") is not None:
        values["registry_namespace"] = "br:cnpj"
    return CompanyRecord(record_id=record_id, **values)


def load_pairs() -> tuple[LabeledPair, ...]:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return tuple(
        LabeledPair(
            pair_id=item["id"],
            left=_record(item["id"] + "-l", item["left"]),
            right=_record(item["id"] + "-r", item["right"]),
            is_duplicate=item["label"],
            category=item["category"],
        )
        for item in raw
    )


@pytest.fixture(scope="module")
def pairs() -> tuple[LabeledPair, ...]:
    return load_pairs()


def pair_by_id(pairs: tuple[LabeledPair, ...], pair_id: str) -> LabeledPair:
    return next(pair for pair in pairs if pair.pair_id == pair_id)


def test_fixture_is_balanced_and_contains_hard_negatives(pairs) -> None:
    assert len(pairs) == 54
    assert sum(pair.is_duplicate for pair in pairs) == 27
    categories = {pair.category for pair in pairs if not pair.is_duplicate}
    assert {"shared_domain", "shared_phone", "shared_address", "registry_conflict", "similar_name"} <= categories


def test_record_requires_registry_namespace_and_id_together() -> None:
    with pytest.raises(ValueError):
        CompanyRecord("r", registry_id="12345678000190")
    with pytest.raises(ValueError):
        CompanyRecord("r", registry_namespace="br:cnpj")


def test_record_and_labeled_pair_reject_blank_or_self_pair() -> None:
    with pytest.raises(ValueError):
        CompanyRecord(" ")
    left = CompanyRecord("same")
    with pytest.raises(ValueError):
        LabeledPair("p", left, left, True, "x")
    with pytest.raises(ValueError):
        LabeledPair("", CompanyRecord("a"), CompanyRecord("b"), True, "x")
    with pytest.raises(ValueError):
        LabeledPair("p", CompanyRecord("a"), CompanyRecord("b"), True, " ")


def test_registry_conflict_is_hard_veto(pairs) -> None:
    pair = pair_by_id(pairs, "n01")
    decision = resolve_pair(pair.left, pair.right, strategy=Strategy.WEIGHTED, threshold=0.50)
    assert not decision.is_match
    assert decision.score == 0.0
    assert "registry_conflict" in decision.reasons


def test_exact_namespaced_registry_is_hard_positive(pairs) -> None:
    pair = pair_by_id(pairs, "p01")
    decision = resolve_pair(pair.left, pair.right, strategy=Strategy.WEIGHTED, threshold=0.99)
    assert decision.is_match
    assert decision.score == 1.0
    assert decision.features.registry_comparable


def test_equal_registry_without_supported_namespace_is_not_strong_signal() -> None:
    left = CompanyRecord("l", registry_namespace="other", registry_id="ABC-123", name="Acme")
    right = CompanyRecord("r", registry_namespace="other", registry_id="ABC-123", name="Acme")
    features = compare_features(left, right)
    assert not features.registry_comparable
    assert features.registry_exact is None
    assert triage_pair(left, right).disposition is ResolutionDisposition.INSUFFICIENT_EVIDENCE


def test_different_registry_namespaces_are_not_compared() -> None:
    left = CompanyRecord("l", registry_namespace="br:cnpj", registry_id="12345678000190")
    right = CompanyRecord("r", registry_namespace="other", registry_id="12345678000190")
    features = compare_features(left, right)
    assert not features.registry_comparable
    assert features.registry_exact is None
    assert not features.registry_conflict


def test_invalid_cnpj_shape_is_not_a_registry_signal() -> None:
    left = CompanyRecord("l", registry_namespace="br:cnpj", registry_id="123")
    right = CompanyRecord("r", registry_namespace="br:cnpj", registry_id="123")
    assert compare_features(left, right).registry_exact is None


def test_current_alphanumeric_cnpj_contract_can_be_exact_signal() -> None:
    left = CompanyRecord("l", registry_namespace="br:cnpj", registry_id="12.ABC.678/0001-Z0")
    right = CompanyRecord("r", registry_namespace="br:cnpj", registry_id="12ABC6780001Z0")
    assert compare_features(left, right).registry_exact is True


def test_diacritics_and_case_do_not_destroy_name_similarity(pairs) -> None:
    features = compare_features(pair_by_id(pairs, "p06").left, pair_by_id(pairs, "p06").right)
    assert features.name_similarity is not None and features.name_similarity > 0.75
    assert features.location_exact is True


def test_missing_names_produce_no_name_similarity() -> None:
    assert compare_features(CompanyRecord("a"), CompanyRecord("b")).name_similarity is None


def test_shared_domain_alone_does_not_force_exact_evidence_match(pairs) -> None:
    pair = pair_by_id(pairs, "n11")
    decision = resolve_pair(pair.left, pair.right, strategy=Strategy.EXACT_EVIDENCE)
    assert not decision.is_match


def test_wu4_strict_invalid_domain_is_ignored_as_er_signal() -> None:
    left = CompanyRecord("l", name="Acme", domain="foo_bar.example")
    right = CompanyRecord("r", name="Acme", domain="foo_bar.example")
    assert compare_features(left, right).domain_exact is None
    assert not any(key.startswith("domain:") for key in blocking_keys(left))


def test_phone_and_domain_features_follow_wu4_representation() -> None:
    left = CompanyRecord("l", domain="HTTPS://Example.COM/a", phone="+55 (11) 99999-0000")
    right = CompanyRecord("r", domain="example.com", phone="+5511999990000")
    features = compare_features(left, right)
    assert features.domain_exact is True
    assert features.phone_exact is True


def test_address_similarity_and_location_and_cnae_features() -> None:
    left = CompanyRecord("l", address="Rua A 100", city="São Paulo", state="SP", cnae="6204-0/00")
    right = CompanyRecord("r", address="Rua A, 100", city="SAO PAULO", state="sp", cnae=6204000)
    features = compare_features(left, right)
    assert features.address_similarity == 1.0
    assert features.location_exact is True
    assert features.cnae_exact is True


def test_missing_address_or_location_or_cnae_is_not_false_signal() -> None:
    features = compare_features(CompanyRecord("l"), CompanyRecord("r"))
    assert features.address_similarity is None
    assert features.location_exact is None
    assert features.cnae_exact is None


def test_registry_only_is_high_precision_low_recall(pairs) -> None:
    metrics = evaluate(pairs, strategy=Strategy.REGISTRY_ONLY)
    assert metrics.false_positive == 0
    assert metrics.precision == 1.0
    assert metrics.recall < 0.50


def test_exact_evidence_strategy_has_nonzero_recall_but_is_not_auto_merge_policy(pairs) -> None:
    metrics = evaluate(pairs, strategy=Strategy.EXACT_EVIDENCE)
    assert metrics.true_positive > 0
    assert metrics.false_positive > 0
    assert metrics.recall > evaluate(pairs, strategy=Strategy.REGISTRY_ONLY).recall


def test_weighted_threshold_validation_and_unknown_strategy(pairs) -> None:
    pair = pairs[0]
    with pytest.raises(ValueError):
        resolve_pair(pair.left, pair.right, strategy=Strategy.WEIGHTED, threshold=-0.01)
    with pytest.raises(ValueError):
        resolve_pair(pair.left, pair.right, strategy=Strategy.WEIGHTED, threshold=1.01)
    with pytest.raises(ValueError):
        resolve_pair(pair.left, pair.right, strategy="bogus")  # type: ignore[arg-type]


def test_weighted_strategy_with_no_features_scores_zero() -> None:
    decision = resolve_pair(CompanyRecord("a"), CompanyRecord("b"), strategy=Strategy.WEIGHTED)
    assert decision.score == 0.0
    assert not decision.is_match


def test_weighted_metrics_stay_in_unit_interval(pairs) -> None:
    for threshold in (0.60, 0.70, 0.76, 0.78, 0.85, 0.92, 0.96):
        metrics = evaluate(pairs, strategy=Strategy.WEIGHTED, threshold=threshold)
        for value in (metrics.precision, metrics.recall, metrics.f1, metrics.false_merge_rate):
            assert 0.0 <= value <= 1.0


def test_pairwise_blocking_retains_at_least_90_percent_positive_pairs(pairs) -> None:
    metrics = evaluate_blocking(pairs)
    assert metrics.blocking_recall >= 0.90
    assert metrics.total_pairs == 54


def test_corpus_blocking_has_full_recall_and_large_reduction(pairs) -> None:
    metrics = evaluate_blocking_corpus(pairs)
    assert metrics.blocking_recall == 1.0
    assert metrics.total_pairs == 5778
    assert metrics.reduction_ratio > 0.95


def test_blocking_empty_input_is_well_defined() -> None:
    pairwise = evaluate_blocking(())
    corpus = evaluate_blocking_corpus(())
    assert pairwise.blocking_recall == 0.0 and pairwise.reduction_ratio == 0.0
    assert corpus.blocking_recall == 0.0 and corpus.reduction_ratio == 0.0


def test_blocking_keys_are_transparent_and_include_available_signals() -> None:
    record = CompanyRecord(
        "r",
        name="Acme Tecnologia",
        registry_namespace="br:cnpj",
        registry_id="12.345.678/0001-90",
        domain="EXAMPLE.com",
        phone="(11) 99999-0000",
        city="São Paulo",
    )
    keys = blocking_keys(record)
    assert "registry:br:cnpj:12345678000190" in keys
    assert "domain:example.com" in keys
    assert "phone:11999990000" in keys
    assert any(key.startswith("name0:acme") for key in keys)
    assert any(key.startswith("name0_city:acme:sao paulo") for key in keys)


def test_operational_triage_only_auto_matches_exact_registry(pairs) -> None:
    assert triage_pair(pair_by_id(pairs, "p01").left, pair_by_id(pairs, "p01").right).disposition is ResolutionDisposition.AUTO_MATCH
    assert triage_pair(pair_by_id(pairs, "p03").left, pair_by_id(pairs, "p03").right).disposition is ResolutionDisposition.REVIEW
    assert triage_pair(pair_by_id(pairs, "n01").left, pair_by_id(pairs, "n01").right).disposition is ResolutionDisposition.DISTINCT
    assert triage_pair(pair_by_id(pairs, "p21").left, pair_by_id(pairs, "p21").right).disposition is ResolutionDisposition.INSUFFICIENT_EVIDENCE


def test_no_negative_pair_is_auto_merged_by_operational_triage(pairs) -> None:
    bad = [
        pair.pair_id
        for pair in pairs
        if not pair.is_duplicate
        and triage_pair(pair.left, pair.right).disposition is ResolutionDisposition.AUTO_MATCH
    ]
    assert bad == []


def test_no_weighted_score_is_used_by_operational_triage(pairs) -> None:
    for pair in pairs:
        decision = triage_pair(pair.left, pair.right)
        assert all(not reason.startswith("weighted_score=") for reason in decision.reasons)


def test_evaluation_empty_input_is_zeroed() -> None:
    metrics = evaluate((), strategy=Strategy.REGISTRY_ONLY)
    assert metrics.true_positive == metrics.false_positive == metrics.true_negative == metrics.false_negative == 0
    assert metrics.precision == metrics.recall == metrics.f1 == metrics.false_merge_rate == 0.0

def test_blank_text_features_are_treated_as_missing() -> None:
    features = compare_features(CompanyRecord("l", name="   "), CompanyRecord("r", name="\t"))
    assert features.name_similarity is None
    assert blocking_keys(CompanyRecord("b", name="   ")) == frozenset()

def test_clean_benchmark_metrics_are_reproducible_exactly(pairs) -> None:
    registry = evaluate(pairs, strategy=Strategy.REGISTRY_ONLY)
    exact = evaluate(pairs, strategy=Strategy.EXACT_EVIDENCE)
    weighted_076 = evaluate(pairs, strategy=Strategy.WEIGHTED, threshold=0.76)
    weighted_092 = evaluate(pairs, strategy=Strategy.WEIGHTED, threshold=0.92)

    assert (registry.true_positive, registry.false_positive, registry.true_negative, registry.false_negative) == (5, 0, 27, 22)
    assert registry.precision == pytest.approx(1.0)
    assert registry.recall == pytest.approx(5 / 27)

    assert (exact.true_positive, exact.false_positive, exact.true_negative, exact.false_negative) == (19, 4, 23, 8)
    assert exact.precision == pytest.approx(19 / 23)
    assert exact.recall == pytest.approx(19 / 27)

    assert (weighted_076.true_positive, weighted_076.false_positive, weighted_076.true_negative, weighted_076.false_negative) == (26, 13, 14, 1)
    assert weighted_076.f1 == pytest.approx(0.7878787878787878)
    assert weighted_076.false_merge_rate == pytest.approx(13 / 27)

    assert (weighted_092.true_positive, weighted_092.false_positive, weighted_092.true_negative, weighted_092.false_negative) == (14, 2, 25, 13)
    assert weighted_092.false_merge_rate == pytest.approx(2 / 27)


def test_clean_blocking_metrics_are_reproducible_exactly(pairs) -> None:
    metrics = evaluate_blocking_corpus(pairs)
    assert metrics.true_duplicate_pairs == 27
    assert metrics.candidate_duplicate_pairs == 27
    assert metrics.blocking_recall == 1.0
    assert metrics.total_pairs == 5778
    assert metrics.candidate_pairs == 117
    assert metrics.reduction_ratio == pytest.approx(1 - 117 / 5778)


def test_clean_operational_triage_counts_are_reproducible_exactly(pairs) -> None:
    counts = {disposition: [0, 0] for disposition in ResolutionDisposition}
    for pair in pairs:
        disposition = triage_pair(pair.left, pair.right).disposition
        counts[disposition][0 if pair.is_duplicate else 1] += 1
    assert counts[ResolutionDisposition.AUTO_MATCH] == [5, 0]
    assert counts[ResolutionDisposition.REVIEW] == [14, 4]
    assert counts[ResolutionDisposition.DISTINCT] == [0, 3]
    assert counts[ResolutionDisposition.INSUFFICIENT_EVIDENCE] == [8, 20]
