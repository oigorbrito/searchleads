"""Bounded synchronous execution for already-planned SearchLeads gap actions.

This module executes only ``ActionKind`` values already selected by the clean
``gap_automation`` planner. It adds finite retry, successful-result cache,
minimum-interval scheduling, explicit SearchLeads lifecycle hooks, and bounded
reassessment. It is not a background scheduler, generic workflow engine,
source selector, or crawler.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Callable, Mapping

from .planning import ActionDisposition, ActionKind, AutomationAction, AutomationPlan


class ActionExecutionStatus(StrEnum):
    BLOCKED = "BLOCKED"
    CACHE_HIT = "CACHE_HIT"
    SCHEDULED = "SCHEDULED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class ActionExecutionRecord:
    action_id: str
    action_kind: ActionKind | None
    status: ActionExecutionStatus
    attempts: int
    reason: str
    executed_at: datetime | None = None
    next_eligible_at: datetime | None = None


@dataclass(slots=True)
class GapRuntimeState:
    successful_cache_keys: set[str] = field(default_factory=set)
    last_attempt_at: dict[str, datetime] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GapLifecycleHooks:
    """Explicit post-action SearchLeads stages.

    The caller supplies these hooks; execution never discovers handlers or
    lifecycle stages dynamically. They run only after at least one action
    succeeds in the current cycle.
    """

    resolve: Callable[[], None]
    validate: Callable[[], None]


@dataclass(frozen=True, slots=True)
class GapCycleResult:
    plan_before: AutomationPlan
    execution_records: tuple[ActionExecutionRecord, ...]
    plan_after: AutomationPlan

    @property
    def made_progress(self) -> bool:
        return any(record.status is ActionExecutionStatus.SUCCEEDED for record in self.execution_records)


@dataclass(frozen=True, slots=True)
class GapRunResult:
    cycles: tuple[GapCycleResult, ...]
    final_plan: AutomationPlan
    stop_reason: str


ActionHandler = Callable[[AutomationAction], None]
PlanFactory = Callable[[], AutomationPlan]
Clock = Callable[[], datetime]


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("clock must return timezone-aware datetimes")


def execute_gap_plan(
    plan: AutomationPlan,
    handlers: Mapping[ActionKind, ActionHandler],
    *,
    now: datetime,
    runtime: GapRuntimeState,
) -> tuple[ActionExecutionRecord, ...]:
    """Execute one finite batch of actions already authorized by the planner."""
    _require_aware(now)
    records: list[ActionExecutionRecord] = []

    for action in plan.actions:
        if action.disposition is ActionDisposition.BLOCKED or action.action_kind is None:
            records.append(ActionExecutionRecord(
                action.action_id, action.action_kind, ActionExecutionStatus.BLOCKED,
                0, action.reason,
            ))
            continue

        # READY is already validated by AutomationAction: cache key exists and
        # retry_max_attempts >= 1. Keep a defensive guard at this boundary so a
        # malformed external implementation cannot create an unbounded/opaque run.
        if action.cache_key is None or action.retry_max_attempts < 1:
            records.append(ActionExecutionRecord(
                action.action_id, action.action_kind, ActionExecutionStatus.BLOCKED,
                0, "planned READY action lacks finite retry/cache metadata",
            ))
            continue

        if action.cache_key in runtime.successful_cache_keys:
            records.append(ActionExecutionRecord(
                action.action_id, action.action_kind, ActionExecutionStatus.CACHE_HIT,
                0, "successful action result already cached",
            ))
            continue

        last = runtime.last_attempt_at.get(action.cache_key)
        if last is not None and action.min_interval_seconds > 0:
            _require_aware(last)
            next_eligible = last + timedelta(seconds=action.min_interval_seconds)
            if now < next_eligible:
                records.append(ActionExecutionRecord(
                    action.action_id, action.action_kind, ActionExecutionStatus.SCHEDULED,
                    0, "minimum interval has not elapsed", next_eligible_at=next_eligible,
                ))
                continue

        handler = handlers.get(action.action_kind)
        if handler is None:
            records.append(ActionExecutionRecord(
                action.action_id, action.action_kind, ActionExecutionStatus.BLOCKED,
                0, "no explicit handler supplied for planned known action",
            ))
            continue

        runtime.last_attempt_at[action.cache_key] = now
        error: Exception | None = None
        for attempt in range(1, action.retry_max_attempts + 1):
            try:
                handler(action)
            except Exception as exc:  # handler boundary is intentionally explicit
                error = exc
                continue

            runtime.successful_cache_keys.add(action.cache_key)
            records.append(ActionExecutionRecord(
                action.action_id, action.action_kind, ActionExecutionStatus.SUCCEEDED,
                attempt, "known action handler completed", executed_at=now,
            ))
            break
        else:
            next_eligible = (
                now + timedelta(seconds=action.min_interval_seconds)
                if action.min_interval_seconds > 0 else None
            )
            records.append(ActionExecutionRecord(
                action.action_id, action.action_kind, ActionExecutionStatus.FAILED,
                action.retry_max_attempts,
                f"handler failed after bounded retries: {error}",
                executed_at=now, next_eligible_at=next_eligible,
            ))

    return tuple(records)


def execute_and_reassess_gap_cycle(
    plan_factory: PlanFactory,
    handlers: Mapping[ActionKind, ActionHandler],
    *,
    clock: Clock,
    runtime: GapRuntimeState,
    lifecycle_hooks: GapLifecycleHooks | None = None,
) -> GapCycleResult:
    """Run one ``detect -> enrich -> resolve -> validate -> reassess`` cycle."""
    plan_before = plan_factory()
    now = clock()
    _require_aware(now)
    records = execute_gap_plan(plan_before, handlers, now=now, runtime=runtime)

    if lifecycle_hooks is not None and any(
        record.status is ActionExecutionStatus.SUCCEEDED for record in records
    ):
        lifecycle_hooks.resolve()
        lifecycle_hooks.validate()

    return GapCycleResult(plan_before, records, plan_factory())


def run_gap_automation_until_stable(
    plan_factory: PlanFactory,
    handlers: Mapping[ActionKind, ActionHandler],
    *,
    clock: Clock,
    runtime: GapRuntimeState | None = None,
    lifecycle_hooks: GapLifecycleHooks | None = None,
    max_cycles: int = 3,
) -> GapRunResult:
    """Run a finite synchronous lifecycle until resolved or no progress is possible."""
    if max_cycles < 1:
        raise ValueError("max_cycles must be >= 1")

    state = runtime if runtime is not None else GapRuntimeState()
    cycles: list[GapCycleResult] = []

    for _ in range(max_cycles):
        current = plan_factory()
        if not current.gaps:
            return GapRunResult(tuple(cycles), current, "NO_GAPS")

        cycle = execute_and_reassess_gap_cycle(
            plan_factory,
            handlers,
            clock=clock,
            runtime=state,
            lifecycle_hooks=lifecycle_hooks,
        )
        cycles.append(cycle)

        if not cycle.plan_after.gaps:
            return GapRunResult(tuple(cycles), cycle.plan_after, "GAPS_RESOLVED")
        if not cycle.made_progress:
            return GapRunResult(tuple(cycles), cycle.plan_after, "NO_PROGRESS_OR_SCHEDULED")

    return GapRunResult(tuple(cycles), plan_factory(), "MAX_CYCLES_REACHED")
