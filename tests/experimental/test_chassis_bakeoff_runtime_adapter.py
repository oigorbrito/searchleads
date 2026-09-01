from __future__ import annotations

import asyncio
from dataclasses import dataclass
import os

import pytest

pytest.importorskip("crawlee")

from crawlee import Request
from crawlee.crawlers import BasicCrawler
from crawlee.storage_clients import MemoryStorageClient

from scripts.empirical_observation import build_observation, write_observation
from searchleads.gap_automation.planning import (
    ActionDisposition,
    ActionEffect,
    ActionKind,
    AutomationAction,
)


@dataclass(frozen=True, slots=True)
class AdapterObservation:
    action_id: str
    cache_key: str
    action_kind: str
    locator: str
    request_unique_key: str
    max_retries: int | None


def _record_observation(name: str, payload: dict[str, object]) -> None:
    observation_dir = os.environ.get("SEARCHLEADS_EMPIRICAL_OBSERVATION_DIR")
    if not observation_dir:
        return
    write_observation(
        observation_id=name,
        research_question="Does the adapter preserve SearchLeads request identity and runtime metadata?",
        method="FUNCTIONAL_PROBE",
        evidence_class="FUNCTIONAL_PROBE",
        payload=payload,
        validity_limits=[
            "single-process local probe only",
            "no operational superiority claim",
        ],
    )


def _action(index: int) -> AutomationAction:
    return AutomationAction(
        action_id=f"automation:adapter:{index}",
        gap_id=f"gap:adapter:{index}",
        disposition=ActionDisposition.READY,
        action_kind=ActionKind.BRASILAPI_POINT_LOOKUP,
        effect=ActionEffect.PREREQUISITE,
        reason="runtime adapter bake-off",
        locator=f"https://example.invalid/company/{index}",
        retry_max_attempts=3,
        cache_key=f"automation-cache:adapter:{index}",
        min_interval_seconds=60,
    )


def _to_request(action: AutomationAction) -> Request:
    assert action.disposition is ActionDisposition.READY
    assert action.action_kind is not None
    assert action.locator is not None
    assert action.cache_key is not None

    max_retries = max(0, action.retry_max_attempts - 1)
    return Request.from_url(
        action.locator,
        unique_key=action.cache_key,
        max_retries=max_retries,
        user_data={
            "searchleads": {
                "action_id": action.action_id,
                "gap_id": action.gap_id,
                "action_kind": action.action_kind.value,
                "cache_key": action.cache_key,
                "min_interval_seconds": action.min_interval_seconds,
            },
        },
    )


async def _adapter_probe(actions: tuple[AutomationAction, ...]) -> tuple[list[AdapterObservation], object]:
    crawler = BasicCrawler(
        max_request_retries=0,
        use_session_pool=False,
        storage_client=MemoryStorageClient(),
        configure_logging=False,
    )
    observations: list[AdapterObservation] = []

    @crawler.router.default_handler
    async def handler(context) -> None:
        metadata = context.request.user_data["searchleads"]
        observations.append(
            AdapterObservation(
                action_id=metadata["action_id"],
                cache_key=metadata["cache_key"],
                action_kind=metadata["action_kind"],
                locator=context.request.url,
                request_unique_key=context.request.unique_key,
                max_retries=context.request.crawlee_data.max_retries,
            )
        )

    stats = await crawler.run([_to_request(action) for action in actions])
    return observations, stats


def test_minimal_runtime_adapter_preserves_searchleads_action_identity() -> None:
    actions = tuple(_action(index) for index in range(3))
    observations, stats = asyncio.run(_adapter_probe(actions))

    assert stats.requests_finished == 3
    assert stats.requests_failed == 0
    assert len(observations) == 3

    by_id = {observation.action_id: observation for observation in observations}
    for action in actions:
        observation = by_id[action.action_id]
        assert observation.cache_key == action.cache_key
        assert observation.request_unique_key == action.cache_key
        assert observation.action_kind == action.action_kind.value
        assert observation.locator == action.locator
        assert observation.max_retries == action.retry_max_attempts - 1

    print("SEARCHLEADS_CRAWLEE_ADAPTER_PROBE_V1")
    print("actions=3 identity_roundtrip=3/3")
    print("cache_key_to_request_unique_key=3/3")
    print("retry_semantics_translation=SearchLeads total_attempts -> Crawlee retries_after_initial")
    print("planner_min_interval_preserved_as_metadata=YES enforced_by_crawlee_native=NO")
    print("domain_truth_mutation=NONE")
    _record_observation(
        "runtime-adapter-roundtrip-v1",
        {
            "action_count": len(actions),
            "requests_finished": stats.requests_finished,
            "requests_failed": stats.requests_failed,
            "observations": [
                {
                    "action_id": item.action_id,
                    "cache_key": item.cache_key,
                    "action_kind": item.action_kind,
                    "locator": item.locator,
                    "request_unique_key": item.request_unique_key,
                    "max_retries": item.max_retries,
                }
                for item in sorted(observations, key=lambda value: value.action_id)
            ],
            "retry_translation": "searchleads_total_attempts_minus_initial",
        },
    )


def test_adapter_boundary_keeps_business_policy_outside_crawlee() -> None:
    action = _action(1)
    request = _to_request(action)
    metadata = request.user_data["searchleads"]

    assert metadata["gap_id"] == action.gap_id
    assert metadata["min_interval_seconds"] == 60
    assert "effect" not in request.user_data
    assert "evidence" not in request.user_data
    assert "qualification" not in request.user_data

    print("SEARCHLEADS_CRAWLEE_ADAPTER_BOUNDARY_V1")
    print("request_runtime_receives_action_identity_and_execution_metadata=YES")
    print("evidence_truth_policy_transferred_to_runtime=NO")
    print("qualification_policy_transferred_to_runtime=NO")
    print("candidate_integration_shape=THIN_ADAPTER")
    _record_observation(
        "runtime-adapter-boundary-v1",
        {
            "preserved_runtime_metadata": ["action_id", "gap_id", "action_kind", "cache_key", "min_interval_seconds"],
            "excluded_policy_fields": ["effect", "evidence", "qualification"],
            "max_retries": getattr(getattr(request, "crawlee_data", None), "max_retries", None),
        },
    )
