from __future__ import annotations

from searchleads.entity_resolution import (
    CompanyIdentity,
    ResolutionDecision,
    all_pairs_count,
    candidate_pairs,
    reduction_ratio,
    resolve_company_pair,
)


def test_exact_cik_matches() -> None:
    left = CompanyIdentity("left", external_ids={"sec_cik": "0001045810"})
    right = CompanyIdentity("right", external_ids={"sec_cik": "0001045810"})

    assert resolve_company_pair(left, right).decision is ResolutionDecision.MATCH


def test_conflicting_ids_in_same_namespace_do_not_match() -> None:
    left = CompanyIdentity("left", external_ids={"sec_cik": "0001045810"})
    right = CompanyIdentity("right", external_ids={"sec_cik": "0000320193"})

    result = resolve_company_pair(left, right)

    assert result.decision is ResolutionDecision.NO_MATCH
    assert result.reasons == ("conflicting_external_id:sec_cik",)


def test_domain_exact_alone_is_unresolved() -> None:
    left = CompanyIdentity("left", domain="example.com")
    right = CompanyIdentity("right", domain="EXAMPLE.COM")

    assert resolve_company_pair(left, right).decision is ResolutionDecision.UNRESOLVED


def test_exact_name_with_conflicting_city_is_possibly_different() -> None:
    left = CompanyIdentity("left", normalized_name="acme inc.", city="Boston")
    right = CompanyIdentity("right", normalized_name="acme inc.", city="Austin")

    result = resolve_company_pair(left, right)

    assert result.decision is ResolutionDecision.POSSIBLY_DIFFERENT
    assert result.reasons == ("exact_normalized_name", "conflicting_city")


def test_domain_plus_exact_name_matches() -> None:
    left = CompanyIdentity(
        "left", normalized_name="acme inc.", domain="acme.example"
    )
    right = CompanyIdentity(
        "right", normalized_name="acme inc.", domain="acme.example"
    )

    assert resolve_company_pair(left, right).decision is ResolutionDecision.MATCH


def test_exact_name_alone_is_not_treated_as_identity() -> None:
    left = CompanyIdentity("left", normalized_name="acme inc.")
    right = CompanyIdentity("right", normalized_name="acme inc.")

    assert resolve_company_pair(left, right).decision is ResolutionDecision.UNRESOLVED


def test_conflicting_external_id_prevents_other_weak_signals_from_merging() -> None:
    left = CompanyIdentity(
        "left",
        external_ids={"sec_cik": "0000000001"},
        normalized_name="acme inc.",
        domain="acme.example",
    )
    right = CompanyIdentity(
        "right",
        external_ids={"sec_cik": "0000000002"},
        normalized_name="acme inc.",
        domain="acme.example",
    )

    assert resolve_company_pair(left, right).decision is ResolutionDecision.NO_MATCH


def test_blocking_is_separate_from_matching() -> None:
    identities = (
        CompanyIdentity("left", domain="shared.example"),
        CompanyIdentity("right", domain="shared.example"),
    )

    assert candidate_pairs(identities) == ((0, 1),)
    assert resolve_company_pair(*identities).decision is ResolutionDecision.UNRESOLVED


def test_synthetic_10k_blocking_benchmark() -> None:
    identities: list[CompanyIdentity] = []

    # 100 disjoint pairs share one exact external identifier. Every other
    # identity has a unique identifier, yielding exactly 100 candidate pairs.
    for pair_index in range(100):
        shared_cik = f"{pair_index + 1:010d}"
        identities.append(
            CompanyIdentity(f"paired:{pair_index}:a", external_ids={"sec_cik": shared_cik})
        )
        identities.append(
            CompanyIdentity(f"paired:{pair_index}:b", external_ids={"sec_cik": shared_cik})
        )

    for unique_index in range(9_800):
        identities.append(
            CompanyIdentity(
                f"unique:{unique_index}",
                external_ids={"internal_test": f"unique-{unique_index}"},
            )
        )

    candidates = candidate_pairs(tuple(identities))
    all_pairs = all_pairs_count(len(identities))

    assert len(identities) == 10_000
    assert all_pairs == 49_995_000
    assert len(candidates) == 100
    assert reduction_ratio(all_pairs=all_pairs, candidates=len(candidates)) > 0.999998
