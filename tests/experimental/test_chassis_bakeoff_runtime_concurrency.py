from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from time import perf_counter, sleep

import pytest

pytest.importorskip("crawlee")

from crawlee import ConcurrencySettings
from crawlee.crawlers import BasicCrawler
from crawlee.storage_clients import MemoryStorageClient

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


WORK_ITEMS = 12
SYNTHETIC_WORK_SECONDS = 0.02
CRAWLEE_CONCURRENCY = 4


def _searchleads_plan() -> AutomationPlan:
    gaps = tuple(
        Gap(
            gap_id=f"gap:concurrency:{index}",
            kind=GapKind.COMPANY_FIELD,
            key=f"field_{index}",
            reason="synthetic runtime concurrency probe",
        )
        for index in range(WORK_ITEMS)
    )
    actions = tuple(
        AutomationAction(
            action_id=f"action:concurrency:{index}",
            gap_id=gap.gap_id,
            disposition=ActionDisposition.READY,
            action_kind=ActionKind.BRASILAPI_POINT_LOOKUP,
            effect=ActionEffect.PREREQUISITE,
            reason="synthetic runtime concurrency probe",
            locator=f"https://example.invalid/company/{index}",
            retry_max_attempts=1,
            cache_key=f"runtime-concurrency:{index}",
            min_interval_seconds=0,
        )
        for index, gap in enumerate(gaps)
    )
    return AutomationPlan(
        company_id="company:runtime-concurrency",
        requirements=GapRequirements(company_fields=tuple(f"field_{index}" for index in range(WORK_ITEMS))),
        gaps=gaps,
        actions=actions,
    )


def _searchleads_concurrency_probe() -> tuple[int, int, float]:
    active = 0
    peak = 0
    completed = 0

    def handler(_action: AutomationAction) -> None:
        nonlocal active, peak, completed
        active += 1
        peak = max(peak, active)
        sleep(SYNTHETIC_WORK_SECONDS)
        completed += 1
        active -= 1

    started = perf_counter()
    records = execute_gap_plan(
        _searchleads_plan(),
        {ActionKind.BRASILAPI_POINT_LOOKUP: handler},
        now=datetime(2026, 8, 30, 21, 0, tzinfo=timezone.utc),
        runtime=GapRuntimeState(),
    )
    elapsed = perf_counter() - started

    assert all(record.status is ActionExecutionStatus.SUCCEEDED for record in records)
    return peak, completed, elapsed


async def _crawlee_concurrency_probe() -> tuple[int, int, float]:
    crawler = BasicCrawler(
        concurrency_settings=ConcurrencySettings(
            desired_concurrency=CRAWLEE_CONCURRENCY,
            max_concurrency=CRAWLEE_CONCURRENCY,
        ),
        use_session_pool=False,
        storage_client=MemoryStorageClient(),
        configure_logging=False,
    )
    active = 0
    peak = 0
    completed = 0
    lock = asyncio.Lock()

    @crawler.router.default_handler
    async def handler(_context) -> None:
        nonlocal active, peak, completed
        async with lock:
            active += 1
            peak = max(peak, active)
        await asyncio.sleep(SYNTHETIC_WORK_SECONDS)
        async with lock:
            completed += 1
            active -= 1

    urls = [f"https://example.invalid/runtime-concurrency/{index}" for index in range(WORK_ITEMS)]
    started = perf_counter()
    await crawler.run(urls)
    elapsed = perf_counter() - started
    return peak, completed, elapsed


def test_runtime_scheduling_concurrency_bakeoff() -> None:
    searchleads_peak, searchleads_completed, searchleads_elapsed = _searchleads_concurrency_probe()
    crawlee_peak, crawlee_completed, crawlee_elapsed = asyncio.run(_crawlee_concurrency_probe())

    assert searchleads_completed == WORK_ITEMS
    assert crawlee_completed == WORK_ITEMS
    assert searchleads_peak == 1
    assert 2 <= crawlee_peak <= CRAWLEE_CONCURRENCY

    print("RUNTIME_CONCURRENCY_BAKEOFF_V1")
    print(
        f"work_items={WORK_ITEMS} synthetic_work_s={SYNTHETIC_WORK_SECONDS:.3f} "
        f"searchleads_peak={searchleads_peak} crawlee_peak={crawlee_peak}"
    )
    print(
        f"searchleads_elapsed_s={searchleads_elapsed:.4f} "
        f"crawlee_elapsed_s={crawlee_elapsed:.4f}"
    )
    if crawlee_elapsed > 0:
        print(f"synthetic_wallclock_ratio_searchleads_over_crawlee={searchleads_elapsed / crawlee_elapsed:.3f}")
    print("scope=synthetic scheduling capability only; not live HTTP throughput or product-quality evidence")
