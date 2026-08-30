from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import inspect
from pathlib import Path

import pytest

pytest.importorskip("crawlee")

from crawlee import Request
from crawlee.configuration import Configuration
from crawlee.crawlers import BasicCrawler
from crawlee.storage_clients import FileSystemStorageClient, MemoryStorageClient
from crawlee.storages import RequestQueue

from searchleads.gap_automation.execution import (
    ActionExecutionStatus,
    GapRuntimeState,
    execute_gap_plan,
)
from searchleads.gap_automation.planning import (
    ActionDisposition,
    ActionEffect,
    ActionKind,
    AutomationAction,
    AutomationPlan,
    Gap,
    GapKind,
    GapRequirements,
)


def _network_plan() -> AutomationPlan:
    gap = Gap(
        gap_id="gap:runtime-bakeoff",
        kind=GapKind.COMPANY_FIELD,
        key="legal_name",
        reason="runtime bake-off missing field",
    )
    action = AutomationAction(
        action_id="action:runtime-bakeoff",
        gap_id=gap.gap_id,
        disposition=ActionDisposition.READY,
        action_kind=ActionKind.BRASILAPI_POINT_LOOKUP,
        effect=ActionEffect.PREREQUISITE,
        reason="runtime bake-off network action",
        locator="https://example.invalid/company/1",
        retry_max_attempts=3,
        cache_key="runtime-bakeoff:company:1",
        min_interval_seconds=60,
    )
    return AutomationPlan(
        company_id="company:runtime-bakeoff",
        requirements=GapRequirements(company_fields=("legal_name",)),
        gaps=(gap,),
        actions=(action,),
    )


def test_searchleads_runtime_fault_injection_exposes_process_local_state() -> None:
    plan = _network_plan()
    started = datetime(2026, 8, 30, 18, 0, tzinfo=timezone(timedelta(hours=-3)))
    first_runtime = GapRuntimeState()
    failed_calls = 0

    def always_fail(_action: AutomationAction) -> None:
        nonlocal failed_calls
        failed_calls += 1
        raise RuntimeError("deterministic injected failure")

    failed = execute_gap_plan(
        plan,
        {ActionKind.BRASILAPI_POINT_LOOKUP: always_fail},
        now=started,
        runtime=first_runtime,
    )
    assert failed_calls == 3
    assert failed[0].status is ActionExecutionStatus.FAILED
    assert failed[0].attempts == 3

    # The same runtime remembers the last attempt and enforces the planner's
    # minimum interval after an exhausted failure.
    scheduled = execute_gap_plan(
        plan,
        {ActionKind.BRASILAPI_POINT_LOOKUP: always_fail},
        now=started + timedelta(seconds=10),
        runtime=first_runtime,
    )
    assert scheduled[0].status is ActionExecutionStatus.SCHEDULED
    assert failed_calls == 3

    # A fresh runtime models a process restart. Because operational state is
    # currently in-memory only, the same action becomes immediately executable.
    restarted_runtime = GapRuntimeState()
    restarted_calls = 0

    def succeed_after_restart(_action: AutomationAction) -> None:
        nonlocal restarted_calls
        restarted_calls += 1

    restarted = execute_gap_plan(
        plan,
        {ActionKind.BRASILAPI_POINT_LOOKUP: succeed_after_restart},
        now=started + timedelta(seconds=10),
        runtime=restarted_runtime,
    )
    assert restarted[0].status is ActionExecutionStatus.SUCCEEDED
    assert restarted_calls == 1

    print("SEARCHLEADS_RUNTIME_RESTART_PROBE_V1")
    print("finite_retry=YES attempts_on_failure=3")
    print("same_process_min_interval=YES")
    print("restart_preserves_last_attempt=NO")
    print("restart_preserves_success_cache=NO (GapRuntimeState is process-local)")


async def _crawlee_request_queue_probe() -> tuple[bool, bool, bool, int, int]:
    storage = MemoryStorageClient()
    queue = await RequestQueue.open(name="searchleads-runtime-bakeoff", storage_client=storage)
    try:
        first = await queue.add_request("https://example.invalid/company/1")
        duplicate = await queue.add_request("https://example.invalid/company/1")
        assert first is not None and duplicate is not None

        fetched = await queue.fetch_next_request()
        assert fetched is not None
        first_key = fetched.unique_key
        await queue.reclaim_request(fetched)

        reclaimed = await queue.fetch_next_request()
        assert reclaimed is not None
        same_after_reclaim = reclaimed.unique_key == first_key
        await queue.mark_request_as_handled(reclaimed)

        metadata = await queue.get_metadata()
        finished = await queue.is_finished()
        return (
            duplicate.was_already_present,
            same_after_reclaim,
            finished,
            metadata.total_request_count,
            metadata.handled_request_count,
        )
    finally:
        await queue.drop()


def test_crawlee_request_queue_has_dedupe_reclaim_and_handled_lifecycle() -> None:
    duplicate, reclaimed, finished, total, handled = asyncio.run(_crawlee_request_queue_probe())

    assert duplicate is True
    assert reclaimed is True
    assert finished is True
    assert total == 1
    assert handled == 1

    print("CRAWLEE_REQUEST_QUEUE_PROBE_V1")
    print("unique_key_dedupe=YES")
    print("failed_request_reclaim=YES")
    print("handled_terminal_state=YES")
    print(f"total_requests={total} handled_requests={handled}")
    print("storage_backend_for_probe=MemoryStorageClient (durability not claimed)")


async def _crawlee_filesystem_persistence_probe(storage_dir: str) -> tuple[int, int, str]:
    configuration = Configuration(storage_dir=storage_dir, purge_on_start=False)
    first_storage = FileSystemStorageClient()
    first_client = await first_storage.create_rq_client(
        name="runtime-persistence-bakeoff",
        configuration=configuration,
    )
    request = Request.from_url("https://example.invalid/persisted-company/1")
    response = await first_client.add_batch_of_requests([request])
    assert len(response.processed_requests) == 1

    # Re-instantiate the filesystem storage client against the same directory.
    # This is an executable restart-like boundary without relying on a shared
    # Python object or the RequestQueue in-process instance cache.
    second_storage = FileSystemStorageClient()
    second_client = await second_storage.create_rq_client(
        name="runtime-persistence-bakeoff",
        configuration=configuration,
    )
    try:
        fetched = await second_client.fetch_next_request()
        assert fetched is not None
        await second_client.mark_request_as_handled(fetched)
        metadata = await second_client.get_metadata()
        return metadata.total_request_count, metadata.handled_request_count, fetched.unique_key
    finally:
        await second_client.drop()


def test_crawlee_filesystem_request_state_survives_storage_client_reinstantiation(tmp_path: Path) -> None:
    total, handled, unique_key = asyncio.run(
        _crawlee_filesystem_persistence_probe(str(tmp_path / "crawlee-storage"))
    )

    assert total == 1
    assert handled == 1
    assert unique_key

    print("CRAWLEE_FILESYSTEM_PERSISTENCE_PROBE_V1")
    print("storage_client_reinstantiation_preserves_pending_request=YES")
    print("request_can_be_handled_after_reinstantiation=YES")
    print(f"total_requests={total} handled_requests={handled}")
    print("scope=single-process filesystem backend; multi-process safety not claimed")


async def _crawlee_retry_probe() -> int:
    crawler = BasicCrawler(
        max_request_retries=2,
        use_session_pool=False,
        storage_client=MemoryStorageClient(),
        configure_logging=False,
    )
    attempts = 0

    @crawler.router.default_handler
    async def handler(_context) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("deterministic injected failure")

    await crawler.run(["https://example.invalid/runtime-bakeoff"])
    return attempts


def test_crawlee_basic_crawler_retries_the_request_and_recovers() -> None:
    attempts = asyncio.run(_crawlee_retry_probe())
    assert attempts == 3

    print("CRAWLEE_RETRY_FAULT_INJECTION_V1")
    print("max_request_retries=2 total_handler_attempts=3 recovered=YES")
    print("network_navigation=NONE (BasicCrawler handler-only deterministic probe)")


def test_runtime_chassis_capability_scorecard_does_not_encode_a_winner() -> None:
    signature = inspect.signature(BasicCrawler.__init__)
    crawlee_options = set(signature.parameters)

    expected_external_options = {
        "max_request_retries",
        "max_requests_per_crawl",
        "max_session_rotations",
        "use_session_pool",
        "retry_on_blocked",
        "concurrency_settings",
        "request_handler_timeout",
        "statistics",
        "proxy_configuration",
        "respect_robots_txt_file",
    }
    assert expected_external_options <= crawlee_options

    # This is a capability-presence scorecard, not a product-quality score. The
    # outcome benchmarks above and future durability/load tests decide adoption.
    capabilities = {
        "finite_retry": ("SEARCHLEADS_NATIVE", "CRAWLEE_NATIVE"),
        "per_action_or_request_retry_limit": ("SEARCHLEADS_NATIVE", "CRAWLEE_NATIVE"),
        "minimum_interval_from_planner": ("SEARCHLEADS_NATIVE", "ADAPTER_NEEDED"),
        "bounded_business_reassessment_loop": ("SEARCHLEADS_NATIVE", "SEARCHLEADS_EXTENSION"),
        "request_unique_key_dedupe": ("ABSENT", "CRAWLEE_NATIVE"),
        "failed_request_reclaim": ("ABSENT", "CRAWLEE_NATIVE"),
        "request_handled_state": ("ABSENT", "CRAWLEE_NATIVE"),
        "durable_local_request_queue": ("ABSENT", "CRAWLEE_NATIVE_FILESYSTEM"),
        "session_rotation": ("ABSENT", "CRAWLEE_NATIVE"),
        "adaptive_concurrency": ("ABSENT", "CRAWLEE_NATIVE"),
        "crawler_statistics": ("ABSENT", "CRAWLEE_NATIVE"),
        "proxy_runtime": ("ABSENT", "CRAWLEE_NATIVE"),
        "robots_policy": ("ABSENT", "CRAWLEE_NATIVE"),
        "searchleads_evidence_truth_boundary": ("SEARCHLEADS_NATIVE", "SEARCHLEADS_EXTENSION"),
    }

    print("RUNTIME_CHASSIS_CAPABILITY_SCORECARD_V1")
    for capability, (searchleads, crawlee) in capabilities.items():
        print(f"{capability} searchleads={searchleads} crawlee={crawlee}")
    print("winner=UNDECIDED pending executed durability/load/operational-cost evidence")

    assert len(capabilities) == 14
