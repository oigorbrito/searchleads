from __future__ import annotations

from searchleads.gap_automation.planning import ActionKind


NETWORK_RUNTIME_CANDIDATES = frozenset(
    {
        ActionKind.BRASILAPI_POINT_LOOKUP,
        ActionKind.OFFICIAL_COMPANY_LOCATION_INGEST,
        ActionKind.COMPANY_CONTACT_PAGE_INGEST,
        ActionKind.PERSON_ROLE_PAGE_INGEST,
    }
)

LOCAL_SEARCHLEADS_ACTIONS = frozenset(
    {
        ActionKind.CONTACT_PUBLICATION_VALIDATION,
        ActionKind.DENTAL_QUALIFICATION_EVALUATION,
    }
)


def test_runtime_scope_partition_covers_every_current_action_kind() -> None:
    assert NETWORK_RUNTIME_CANDIDATES.isdisjoint(LOCAL_SEARCHLEADS_ACTIONS)
    assert NETWORK_RUNTIME_CANDIDATES | LOCAL_SEARCHLEADS_ACTIONS == frozenset(ActionKind)

    print("RUNTIME_SCOPE_PARTITION_V1")
    print(f"network_runtime_candidates={len(NETWORK_RUNTIME_CANDIDATES)}")
    print(f"local_searchleads_actions={len(LOCAL_SEARCHLEADS_ACTIONS)}")
    print(f"all_action_kinds={len(tuple(ActionKind))}")


def test_crawler_challenger_is_not_a_generic_business_action_executor() -> None:
    assert ActionKind.CONTACT_PUBLICATION_VALIDATION not in NETWORK_RUNTIME_CANDIDATES
    assert ActionKind.DENTAL_QUALIFICATION_EVALUATION not in NETWORK_RUNTIME_CANDIDATES

    print("CRAWLER_RUNTIME_AUTHORITY_BOUNDARY_V1")
    print("network_acquisition_actions_to_challenger=YES_CANDIDATE")
    print("contact_publication_validation_to_challenger=NO")
    print("dental_qualification_to_challenger=NO")
    print("crawler_becomes_business_workflow_engine=NO")


def test_current_scope_ratio_is_reported_not_used_as_quality_metric() -> None:
    total = len(tuple(ActionKind))
    network = len(NETWORK_RUNTIME_CANDIDATES)
    local = len(LOCAL_SEARCHLEADS_ACTIONS)

    assert total == network + local
    assert total > 0

    print("RUNTIME_SCOPE_RATIO_V1")
    print(f"network_fraction={network / total:.3f}")
    print(f"local_fraction={local / total:.3f}")
    print("interpretation=integration_surface_only_not_product_quality")
