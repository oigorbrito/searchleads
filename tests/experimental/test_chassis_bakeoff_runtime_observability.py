from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from time import perf_counter

import pytest

pytest.importorskip("crawlee")

from crawlee.crawlers import BasicCrawler
from crawlee.storage_clients import MemoryStorageClient

from searchleads.gap_automation.execution import GapRuntimeState, execute_gap_plan
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
from searchleads.measurement.metrics import compute_operational_metrics


def _plan() -> AutomationPlan:
    gaps = tuple(
        Gap(
            gap_id=f"gap:observability:{index}",
            kind=GapKind.COMPANY_FIELD,
            key=f"field_{index}",
            reason="observability bake-off",
        )
        for index in range(3)
    )
    actions = tuple(
        AutomationAction(
            action_id=f"action:observability:{index}",
            gap_id=gap.gap_id,
            disposition=ActionDisposition.READY,
            action_kind=ActionKind.BRASILAPI_POINT_LOOKUP,
            effect=ActionEffect.PREREQUISITE,
            reason="observability bake-off",
            locator=f"https://example.invalid/observability/{index}",
            retry_max_attempts=3,
            cache_key=f"observability:{index}",
            min_interval_seconds=0,
        )
        for index, gap in enumerate(gaps)
    )
    return AutomationPlan(
        company_id="company:observability",
        requirements=GapRequirements(company_fields=("field_0", "field_1", "field_2")),
        gaps=gaps,
        actions=actions,
    )


def test_searchleads_execution_records_are_audit_friendly_but_not_request_telemetry() -> None:
    attempts: dict[str, int] = {}

    def handler(action: AutomationAction) -> None:
        attempts[action.action_id] = attempts.get(action.action_id, 0) + 1
        # action 0 succeeds immediately, action 1 succeeds after one failure,
        # action 2 exhausts all three attempts.
        if action.action_id.endswith(":1") and attempts[action.action_id] == 1:
            raise RuntimeError("injected transient failure")
        if action.action_id.endswith(":2"):
            raise RuntimeError("injected permanent failure")

    started = perf_counter()
    records = execute_gap_plan(
        _plan(),
        {ActionKind.BRASILAPI_POINT_LOOKUP: handler},
        now=datetime(2026, 8, 30, 21, 15, tzinfo=timezone.utc),
        runtime=GapRuntimeState(),
    )
    elapsed = perf_counter() - started

    assert [record.attempts for record in records] == [1, 2, 3]
    assert [record.status.value for record in records] == ["SUCCEEDED", "SUCCEEDED", "FAILED"]

    # Existing unified measurement can express aggregate wall-clock/cost metrics,
    # but the executor does not natively emit per-attempt duration, retry reason
    # taxonomy, status-code histogram, session/proxy identity or persisted stats.
    operational = compute_operational_metrics(elapsed_seconds=elapsed, processed_leads=3)
    assert operational.time_per_lead_seconds.value is not None

    print("SEARCHLEADS_RUNTIME_OBSERVABILITY_V1")
    print("action_records=3 attempts=1,2,3 statuses=SUCCEEDED,SUCCEEDED,FAILED")
    print("action_level_reason=YES action_level_executed_at=YES")
    print("per_attempt_duration=NO retry_reason_histogram=NO status_code_histogram=NO")
    print("session_proxy_telemetry=NO persisted_runtime_statistics=NO")
    print("aggregate_operational_time_metric=YES")


async def _crawlee_stats_probe():
    crawler = BasicCrawler(
        max_request_retries=2,
        use_session_pool=False,
        storage_client=MemoryStorageClient(),
        configure_logging=False,
    )
    attempts: dict[str, int] = {}

    @crawler.router.default_handler
    async def handler(context) -> None:
        url = context.request.url
        attempts[url] = attempts.get(url, 0) + 1
        if url.endswith("/transient") and attempts[url] == 1:
            raise RuntimeError("injected transient failure")
        if url.endswith("/permanent"):
            raise RuntimeError("injected permanent failure")

    stats = await crawler.run(
        [
            "https://example.invalid/observability/success",
            "https://example.invalid/observability/transient",
            "https://example.invalid/observability/permanent",
        ]
    )
    return stats, attempts


def test_crawlee_exposes_native_retry_duration_and_completion_statistics() -> None:
    stats, attempts = asyncio.run(_crawlee_stats_probe())

    assert attempts["https://example.invalid/observability/success"] == 1
    assert attempts["https://example.invalid/observability/transient"] == 2
    assert attempts["https://example.invalid/observability/permanent"] == 3
    assert stats.requests_finished == 2
    assert stats.requests_failed == 1
    assert stats.requests_total == 3
    assert sum(stats.retry_histogram) == 3
    assert stats.request_total_duration.total_seconds() >= 0
    assert stats.crawler_runtime.total_seconds() >= 0

    print("CRAWLEE_RUNTIME_OBSERVABILITY_V1")
    print(
        f"requests_total={stats.requests_total} finished={stats.requests_finished} "
        f"failed={stats.requests_failed} retry_histogram={stats.retry_histogram}"
    )
    print(
        f"request_total_duration_s={stats.request_total_duration.total_seconds():.6f} "
        f"crawler_runtime_s={stats.crawler_runtime.total_seconds():.6f}"
    )
    print("native_retry_histogram=YES request_duration_metrics=YES")
    print("network_navigation=NONE (handler-only deterministic probe)")


def test_observability_decision_matrix() -> None:
    matrix = {
        "business_action_identity_and_reason": ("SEARCHLEADS_NATIVE", "ADAPTER_REQUIRED"),
        "business_reassessment_semantics": ("SEARCHLEADS_NATIVE", "SEARCHLEADS_EXTENSION"),
        "request_success_failure_counts": ("DERIVABLE", "CRAWLEE_NATIVE"),
        "retry_histogram": ("DERIVABLE_WITH_EXTRA_CODE", "CRAWLEE_NATIVE"),
        "request_duration_metrics": ("ABSENT", "CRAWLEE_NATIVE"),
        "status_code_statistics": ("ABSENT", "CRAWLEE_NATIVE"),
        "retry_error_tracking": ("LOSSY_STRING_REASON", "CRAWLEE_NATIVE"),
        "persistable_runtime_statistics": ("ABSENT", "CRAWLEE_NATIVE_OPTION"),
        "aggregate_cost_and_time_per_lead": ("SEARCHLEADS_NATIVE", "SEARCHLEADS_EXTENSION"),
    }

    print("RUNTIME_OBSERVABILITY_DECISION_MATRIX_V1")
    for capability, (searchleads, crawlee) in matrix.items():
        print(f"{capability} searchleads={searchleads} crawlee={crawlee}")
    print("candidate=retain SearchLeads business telemetry; source request telemetry from runtime adapter")
    print("winner=UNDECIDED until probes execute")

    assert len(matrix) == 9
