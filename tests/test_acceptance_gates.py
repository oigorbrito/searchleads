from __future__ import annotations

from searchleads.acceptance import AcceptanceMetrics, GateStatus, evaluate_acceptance


def _base_metrics(**overrides: object) -> AcceptanceMetrics:
    values: dict[str, object] = {
        "real_companies": 25,
        "source_count": 4,
        "multi_source_company_count": 1,
        "entity_resolution_rules_verified": True,
        "provenance_verified": True,
        "contact_discovery_verified": True,
        "export_roundtrip_verified": True,
        "reproducible_replay_verified": True,
        "dedup_labeled_pairs": 0,
        "dedup_corpus_sufficient": False,
        "dedup_false_merge_measured": False,
        "dedup_false_split_measured": False,
        "icp_defined": False,
        "qualification_verified": False,
    }
    values.update(overrides)
    return AcceptanceMetrics(**values)  # type: ignore[arg-type]


def test_reference_metrics_preserve_real_blockers() -> None:
    report = evaluate_acceptance(_base_metrics())

    assert report.as_dict() == {
        "REAL_COMPANIES": "PASS",
        "MULTI_SOURCE": "PASS",
        "COMPANY_ER": "PASS",
        "PROVENANCE": "PASS",
        "CONTACT_DISCOVERY": "PASS",
        "EXPORT": "PASS",
        "REPRODUCIBLE": "PASS",
        "DEDUPLICATION": "PARTIAL",
        "QUALIFICATION": "BLOCKED",
    }


def test_fewer_than_25_real_companies_is_not_pass() -> None:
    report = evaluate_acceptance(
        _base_metrics(
            real_companies=3,
            source_count=1,
            multi_source_company_count=0,
            entity_resolution_rules_verified=False,
            provenance_verified=False,
            contact_discovery_verified=False,
            export_roundtrip_verified=False,
            reproducible_replay_verified=False,
        )
    )

    assert report.real_companies is GateStatus.PARTIAL
    assert report.qualification is GateStatus.BLOCKED


def test_dedup_requires_sufficient_labeled_corpus_and_both_error_measurements() -> None:
    insufficient = evaluate_acceptance(
        _base_metrics(
            dedup_labeled_pairs=100,
            dedup_corpus_sufficient=False,
            dedup_false_merge_measured=True,
            dedup_false_split_measured=True,
        )
    )
    incomplete_measurement = evaluate_acceptance(
        _base_metrics(
            dedup_labeled_pairs=100,
            dedup_corpus_sufficient=True,
            dedup_false_merge_measured=True,
            dedup_false_split_measured=False,
        )
    )
    complete = evaluate_acceptance(
        _base_metrics(
            dedup_labeled_pairs=100,
            dedup_corpus_sufficient=True,
            dedup_false_merge_measured=True,
            dedup_false_split_measured=True,
        )
    )

    assert insufficient.deduplication is GateStatus.PARTIAL
    assert incomplete_measurement.deduplication is GateStatus.PARTIAL
    assert complete.deduplication is GateStatus.PASS


def test_qualification_defined_but_not_verified_is_not_pass() -> None:
    report = evaluate_acceptance(
        _base_metrics(icp_defined=True, qualification_verified=False)
    )

    assert report.qualification is GateStatus.NOT_RUN


def test_qualification_pass_requires_defined_icp_and_verified_evaluation() -> None:
    report = evaluate_acceptance(
        _base_metrics(icp_defined=True, qualification_verified=True)
    )

    assert report.qualification is GateStatus.PASS
