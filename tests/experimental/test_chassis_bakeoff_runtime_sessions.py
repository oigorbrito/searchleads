from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

pytest.importorskip("crawlee")

from crawlee.crawlers import BasicCrawler
from crawlee.errors import SessionError
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


def _searchleads_plan(retry_max_attempts: int) -> AutomationPlan:
    gap = Gap(
        gap_id="gap:session-semantics",
        kind=GapKind.COMPANY_FIELD,
        key="legal_name",
        reason="session semantics bake-off",
    )
    action = AutomationAction(
        action_id="action:session-semantics",
        gap_id=gap.gap_id,
        disposition=ActionDisposition.READY,
        action_kind=ActionKind.BRASILAPI_POINT_LOOKUP,
        effect=ActionEffect.PREREQUISITE,
        reason="session semantics bake-off",
        locator="https://example.invalid/session-semantics",
        retry_max_attempts=retry_max_attempts,
        cache_key="session-semantics",
        min_interval_seconds=0,
    )
    return AutomationPlan(
        company_id="company:session-semantics",
        requirements=GapRequirements(company_fields=("legal_name",)),
        gaps=(gap,),
        actions=(action,),
    )


def test_searchleads_has_one_generic_exception_retry_budget() -> None:
    attempts = 0

    def blocked_handler(_action: AutomationAction) -> None:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("simulated blocked/session failure")

    records = execute_gap_plan(
        _searchleads_plan(retry_max_attempts=2),
        {ActionKind.BRASILAPI_POINT_LOOKUP: blocked_handler},
        now=datetime(2026, 8, 30, 21, 20, tzinfo=timezone.utc),
        runtime=GapRuntimeState(),
    )

    assert attempts == 2
    assert records[0].status is ActionExecutionStatus.FAILED
    assert records[0].attempts == 2

    print("SEARCHLEADS_SESSION_SEMANTICS_V1")
    print("normal_retry_budget=2 blocked_or_session_specific_budget=NONE")
    print("simulated_blocked_failures=2 final_status=FAILED")


async def _crawlee_session_rotation_probe() -> tuple[int, int, int]:
    crawler = BasicCrawler(
        max_request_retries=0,
        max_session_rotations=3,
        use_session_pool=True,
        storage_client=MemoryStorageClient(),
        configure_logging=False,
    )
    attempts = 0

    @crawler.router.default_handler
    async def handler(_context) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise SessionError("simulated blocked session")

    stats = await crawler.run(["https://example.invalid/session-semantics"])
    return attempts, stats.requests_finished, stats.requests_failed


def test_crawlee_session_rotation_can_recover_with_normal_retry_budget_zero() -> None:
    attempts, finished, failed = asyncio.run(_crawlee_session_rotation_probe())

    assert attempts == 3
    assert finished == 1
    assert failed == 0

    print("CRAWLEE_SESSION_SEMANTICS_V1")
    print("normal_retry_budget=0 session_rotation_budget=3")
    print(f"handler_attempts={attempts} finished={finished} failed={failed}")
    print("session_failure_recovered_without_consuming_normal_retry_budget=YES")
    print("network_navigation=NONE (SessionError injected by handler)")


def test_session_semantics_decision_rule() -> None:
    print("SESSION_SEMANTICS_DECISION_V1")
    print("web_blocking_proxy_session_failures=separate operational failure class")
    print("business_action_retry_budget=must remain planner-bounded")
    print("candidate=map Crawlee session rotations below SearchLeads action boundary")
    print("truth_promotion_from_session_recovery=FORBIDDEN")

    # The desired architecture is not encoded as an implementation dependency;
    # this assertion only fixes the experiment's safety boundary.
    assert ActionKind.BRASILAPI_POINT_LOOKUP.value == "BRASILAPI_POINT_LOOKUP"
