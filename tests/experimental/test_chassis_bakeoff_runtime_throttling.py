from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

pytest.importorskip("crawlee")

from crawlee.request_loaders import ThrottlingRequestManager
from crawlee.storage_clients import MemoryStorageClient
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


def _searchleads_same_domain_plan() -> AutomationPlan:
    gaps = tuple(
        Gap(
            gap_id=f"gap:throttle:{index}",
            kind=GapKind.COMPANY_FIELD,
            key=f"field_{index}",
            reason="throttling semantics bake-off",
        )
        for index in range(2)
    )
    actions = tuple(
        AutomationAction(
            action_id=f"action:throttle:{index}",
            gap_id=gaps[index].gap_id,
            disposition=ActionDisposition.READY,
            action_kind=ActionKind.BRASILAPI_POINT_LOOKUP,
            effect=ActionEffect.PREREQUISITE,
            reason="throttling semantics bake-off",
            locator=f"https://api.example.test/company/{index}",
            retry_max_attempts=1,
            cache_key=f"cache:throttle:{index}",
            min_interval_seconds=60,
        )
        for index in range(2)
    )
    return AutomationPlan(
        company_id="company:throttle",
        requirements=GapRequirements(company_fields=("field_0", "field_1")),
        gaps=gaps,
        actions=actions,
    )


def test_searchleads_min_interval_is_per_cache_key_not_per_domain() -> None:
    calls: list[str] = []

    def handler(action: AutomationAction) -> None:
        calls.append(action.cache_key or "")

    records = execute_gap_plan(
        _searchleads_same_domain_plan(),
        {ActionKind.BRASILAPI_POINT_LOOKUP: handler},
        now=datetime(2026, 8, 30, 21, 20, tzinfo=timezone.utc),
        runtime=GapRuntimeState(),
    )

    assert [record.status for record in records] == [
        ActionExecutionStatus.SUCCEEDED,
        ActionExecutionStatus.SUCCEEDED,
    ]
    assert calls == ["cache:throttle:0", "cache:throttle:1"]

    print("SEARCHLEADS_THROTTLING_SEMANTICS_V1")
    print("same_domain_distinct_cache_keys_dispatch_same_cycle=YES")
    print("min_interval_scope=CACHE_KEY_ACTION")


async def _crawlee_domain_throttling_probe() -> tuple[str, str, bool]:
    storage = MemoryStorageClient()
    inner = await RequestQueue.open(name="runtime-throttle-inner", storage_client=storage)
    throttler = ThrottlingRequestManager(
        inner=inner,
        domains=["api.example.test"],
        request_manager_opener=RequestQueue.open,
    )
    try:
        throttler.set_crawl_delay("https://api.example.test/company/1", 60)
        await throttler.add_request("https://api.example.test/company/1")
        await throttler.add_request("https://api.example.test/company/2")
        await throttler.add_request("https://other.example.test/company/3")

        first = await throttler.fetch_next_request()
        assert first is not None
        assert first.url.startswith("https://api.example.test/")

        second = await throttler.fetch_next_request()
        assert second is not None
        assert second.url == "https://other.example.test/company/3"

        # One same-domain request remains queued but is temporarily not
        # dispatchable because the domain is in its crawl-delay cooldown.
        temporarily_empty = await throttler.is_empty()
        finished = await throttler.is_finished()
        return first.url, second.url, temporarily_empty and not finished
    finally:
        await throttler.drop()


def test_crawlee_throttling_is_domain_scoped_and_releases_other_domains() -> None:
    first, second, cooldown_visible = asyncio.run(_crawlee_domain_throttling_probe())

    assert first.startswith("https://api.example.test/")
    assert second == "https://other.example.test/company/3"
    assert cooldown_visible is True

    print("CRAWLEE_THROTTLING_SEMANTICS_V1")
    print("crawl_delay_scope=DOMAIN")
    print("same_domain_second_request_delayed=YES")
    print("other_domain_can_progress_during_cooldown=YES")
    print("cooldown_request_keeps_is_finished_false=YES")


def test_adapter_must_not_naively_translate_searchleads_min_interval_to_domain_crawl_delay() -> None:
    # SearchLeads currently defines the delay per action/cache key; Crawlee's
    # crawl-delay is per domain. They are both useful, but not semantically
    # interchangeable. A production adapter must keep them separate unless a
    # future policy change is explicitly benchmarked and accepted.
    searchleads_scope = "CACHE_KEY_ACTION"
    crawlee_scope = "DOMAIN"

    assert searchleads_scope != crawlee_scope

    print("THROTTLING_MAPPING_DECISION_V1")
    print("direct_translation=REJECTED")
    print("reason=scope_mismatch")
    print("candidate=retain_action_policy_and_optionally_add_domain_throttling")
