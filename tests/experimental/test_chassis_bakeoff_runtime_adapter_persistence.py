from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

pytest.importorskip("crawlee")

from crawlee import Request
from crawlee.configuration import Configuration
from crawlee.storage_clients import FileSystemStorageClient

from scripts.empirical_observation import write_observation
from searchleads.gap_automation.planning import (
    ActionDisposition,
    ActionEffect,
    ActionKind,
    AutomationAction,
)


def _action() -> AutomationAction:
    return AutomationAction(
        action_id="automation:persisted-adapter:1",
        gap_id="gap:persisted-adapter:1",
        disposition=ActionDisposition.READY,
        action_kind=ActionKind.BRASILAPI_POINT_LOOKUP,
        effect=ActionEffect.PREREQUISITE,
        reason="persisted runtime adapter bake-off",
        locator="https://example.invalid/company/persisted-1",
        retry_max_attempts=3,
        cache_key="automation-cache:persisted-adapter:1",
        min_interval_seconds=60,
    )


def _request_from_action(action: AutomationAction) -> Request:
    assert action.locator is not None
    assert action.cache_key is not None
    assert action.action_kind is not None
    return Request.from_url(
        action.locator,
        unique_key=action.cache_key,
        max_retries=max(0, action.retry_max_attempts - 1),
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


async def _persistence_probe(storage_dir: str) -> tuple[str, str, str, int | None, int]:
    action = _action()
    configuration = Configuration(storage_dir=storage_dir, purge_on_start=False)

    first_storage = FileSystemStorageClient()
    first_queue = await first_storage.create_rq_client(
        name="searchleads-adapter-persistence",
        configuration=configuration,
    )
    response = await first_queue.add_batch_of_requests([_request_from_action(action)])
    assert len(response.processed_requests) == 1

    second_storage = FileSystemStorageClient()
    second_queue = await second_storage.create_rq_client(
        name="searchleads-adapter-persistence",
        configuration=configuration,
    )
    try:
        recovered = await second_queue.fetch_next_request()
        assert recovered is not None
        metadata = recovered.user_data["searchleads"]
        max_retries = recovered.crawlee_data.max_retries
        await second_queue.mark_request_as_handled(recovered)
        queue_metadata = await second_queue.get_metadata()
        return (
            metadata["action_id"],
            metadata["cache_key"],
            recovered.unique_key,
            max_retries,
            queue_metadata.handled_request_count,
        )
    finally:
        await second_queue.drop()


def test_searchleads_action_metadata_survives_crawlee_filesystem_reopen(tmp_path: Path) -> None:
    action_id, cache_key, unique_key, max_retries, handled = asyncio.run(
        _persistence_probe(str(tmp_path / "adapter-persistence"))
    )

    assert action_id == "automation:persisted-adapter:1"
    assert cache_key == "automation-cache:persisted-adapter:1"
    assert unique_key == cache_key
    assert max_retries == 2
    assert handled == 1

    write_observation(
        observation_id="searchleads-crawlee-adapter-persistence-v1",
        research_question="Does SearchLeads adapter metadata and per-request retry configuration survive reopening Crawlee filesystem request storage under the exercised restart-like boundary?",
        method="deterministic filesystem request-queue reopen functional probe",
        evidence_class="FUNCTIONAL_PROBE",
        payload={
            "action_id": action_id,
            "cache_key": cache_key,
            "unique_key": unique_key,
            "max_retries": max_retries,
            "handled_request_count": handled,
        },
        validity_limits=[
            "single request and single filesystem storage directory",
            "storage client re-instantiation occurs within one process",
            "does not establish multi-process safety, throughput, or production recovery guarantees",
        ],
    )

    print("SEARCHLEADS_CRAWLEE_PERSISTED_ADAPTER_V1")
    print("restart_like_action_identity_roundtrip=YES")
    print("cache_key_unique_key_roundtrip=YES")
    print("request_retry_metadata_roundtrip=YES")
    print("handled_after_reopen=YES")
    print("scope=single-process filesystem backend")
