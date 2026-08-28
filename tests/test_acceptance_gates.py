from __future__ import annotations

from searchleads.acceptance import AcceptanceMetrics, GateStatus, evaluate_acceptance


def test_reference_metrics_preserve_real_blockers() -> None:
    report = evaluate_acceptance(
        AcceptanceMetrics(
            real_companies=25,
            source_count=4,
            multi_source_company_count=1,
            entity_resolution_rules_verified=True,
            provenance_verified=True,
            contact_discovery_verified=True,
            export_roundtrip_verified=True,
            reproducible_replay_verified=True,
            dedup_labeled_pairs=0,
            dedup_false_merge_measured=False,
            dedup_false_split_measured=False,
            icp_defined=False,
        )
    )

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
    metrics = AcceptanceMetrics(
        real_companies=3,
        source_count=1,
        multi_source_company_count=0,
        entity_resolution_rules_verified=False,
        provenance_verified=False,
        contact_discovery_verified=False,
        export_roundtrip_verified=False,
        reproducible_replay_verified=False,
        dedup_labeled_pairs=0,
        dedup_false_merge_measured=False,
        dedup_false_split_measured=False,
        icp_defined=False,
    )

    report = evaluate_acceptance(metrics)

    assert report.real_companies is GateStatus.PARTIAL
    assert report.qualification is GateStatus.BLOCKED


def test_dedup_requires_labeled_error_measurement() -> None:
    base = dict(
        real_companies=25,
        source_count=2,
        multi_source_company_count=1,
        entity_resolution_rules_verified=True,
        provenance_verified=True,
        contact_discovery_verified=True,
        export_roundtrip_verified=True,
        reproducible_replay_verified=True,
        icp_defined=False,
    )
    partial = evaluate_acceptance(
        AcceptanceMetrics(
            **base,
            dedup_labeled_pairs=100,
            dedup_false_merge_measured=True,
            dedup_false_split_measured=False,
        )
    )
    complete = evaluate_acceptance(
        AcceptanceMetrics(
            **base,
            dedup_labeled_pairs=100,
            dedup_false_merge_measured=True,
            dedup_false_split_measured=True,
        )
    )

    assert partial.deduplication is GateStatus.PARTIAL
    assert complete.deduplication is GateStatus.PASS


def test_qualification_pass_requires_explicit_icp_definition() -> None:
    metrics = AcceptanceMetrics(
        real_companies=25,
        source_count=2,
        multi_source_company_count=1,
        entity_resolution_rules_verified=True,
        provenance_verified=True,
        contact_discovery_verified=True,
        export_roundtrip_verified=True,
        reproducible_replay_verified=True,
        dedup_labeled_pairs=1,
        dedup_false_merge_measured=True,
        dedup_false_split_measured=True,
        icp_defined=True,
    )

    assert evaluate_acceptance(metrics).qualification is GateStatus.PASS
