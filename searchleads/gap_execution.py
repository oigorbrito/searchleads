"""Bounded synchronous execution/reassessment for SearchLeads Work Unit 14.

The runner only executes ActionKind values already selected by gap_automation.
It adds finite retry, cache, rate-limit scheduling metadata, explicit resolve and
validate lifecycle hooks, and reassessment. It is not a background scheduler or
a generic workflow engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Mapping

from .gap_automation import ActionDisposition, ActionKind, AutomationAction, AutomationPlan


class ActionExecutionStatus(str, Enum):
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
    """Explicit post-enrichment stages required by the handoff loop.

    Hooks are supplied by SearchLeads-specific orchestration code. They are not
    dynamically discovered and cannot introduce new action/source types.
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
        return any(
            record.status is ActionExecutionStatus.SUCCEEDED
            for record in self.execution_records
        )


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
    """Execute one already-planned batch without inventing new action kinds."""
    _require_aware(now)
    records: list[ActionExecutionRecord] = []

    for action in plan.actions:
        if action.disposition is ActionDisposition.BLOCKED or action.action_kind is None:
            records.append(
                ActionExecutionRecord(
                    action.action_id,
                    action.action_kind,
                    ActionExecutionStatus.BLOCKED,
                    0,
                    action.reason,
                )
            )
            continue

        if action.cache_key in runtime.successful_cache_keys:
            records.append(
                ActionExecutionRecord(
                    action.action_id,
                    action.action_kind,
                    ActionExecutionStatus.CACHE_HIT,
                    0,
                    "successful action result already cached",
                )
            )
            continue

        last = runtime.last_attempt_at.get(action.cache_key)
        if last is not None and action.min_interval_seconds > 0:
            next_eligible = last + timedelta(seconds=action.min_interval_seconds)
            if now < next_eligible:
                records.append(
                    ActionExecutionRecord(
                        action.action_id,
                        action.action_kind,
                        ActionExecutionStatus.SCHEDULED,
                        0,
                        "minimum interval has not elapsed",
                        next_eligible_at=next_eligible,
                    )
                )
                continue

        handler = handlers.get(action.action_kind)
        if handler is None:
            records.append(
                ActionExecutionRecord(
                    action.action_id,
                    action.action_kind,
                    ActionExecutionStatus.BLOCKED,
                    0,
                    "no explicit handler supplied for planned known action",
                )
            )
            continue

        attempts = 0
        error: Exception | None = None
        runtime.last_attempt_at[action.cache_key] = now
        for _ in range(max(1, action.retry_max_attempts)):
            attempts += 1
            try:
                handler(action)
            except Exception as exc:
                error = exc
                continue
            else:
                runtime.successful_cache_keys.add(action.cache_key)
                records.append(
                    ActionExecutionRecord(
                        action.action_id,
                        action.action_kind,
                        ActionExecutionStatus.SUCCEEDED,
                        attempts,
                        "known action handler completed",
                        executed_at=now,
                    )
                )
                break
        else:
            next_eligible = (
                now + timedelta(seconds=action.min_interval_seconds)
                if action.min_interval_seconds
                else None
            )
            records.append(
                ActionExecutionRecord(
                    action.action_id,
                    action.action_kind,
                    ActionExecutionStatus.FAILED,
                    attempts,
                    f"handler failed after bounded retries: {error}",
                    executed_at=now,
                    next_eligible_at=next_eligible,
                )
            )

    return tuple(records)


def _invalidate_cycle_success_cache(
    plan: AutomationPlan,
    records: tuple[ActionExecutionRecord, ...],
    runtime: GapRuntimeState,
) -> None:
    """Undo cache success when post-enrichment lifecycle stages fail.

    A handler result is only safely reusable after resolve and validate complete.
    Otherwise a retry could turn into CACHE_HIT and permanently skip unfinished
    lifecycle work.
    """
    succeeded_action_ids = {
        record.action_id
        for record in records
        if record.status is ActionExecutionStatus.SUCCEEDED
    }
    for action in plan.actions:
        if action.action_id in succeeded_action_ids:
            runtime.successful_cache_keys.discard(action.cache_key)


def execute_and_reassess_gap_cycle(
    plan_factory: PlanFactory,
    handlers: Mapping[ActionKind, ActionHandler],
    *,
    clock: Clock,
    runtime: GapRuntimeState,
    lifecycle_hooks: GapLifecycleHooks | None = None,
) -> GapCycleResult:
    """Run detect → enrich → resolve → validate → reassess for one bounded cycle.

    The lifecycle hooks run only after at least one enrichment/action succeeds.
    This prevents blocked, failed, cached, or merely scheduled work from being
    mislabeled as a fresh resolution/validation pass. If resolve or validate
    fails, cache entries created by this cycle are invalidated so a retry cannot
    skip unfinished lifecycle work.
    """
    plan_before = plan_factory()
    now = clock()
    _require_aware(now)
    records = execute_gap_plan(plan_before, handlers, now=now, runtime=runtime)

    if lifecycle_hooks is not None and any(
        record.status is ActionExecutionStatus.SUCCEEDED for record in records
    ):
        try:
            lifecycle_hooks.resolve()
            lifecycle_hooks.validate()
        except Exception:
            _invalidate_cycle_success_cache(plan_before, records, runtime)
            raise

    plan_after = plan_factory()
    return GapCycleResult(plan_before, records, plan_after)


def run_gap_automation_until_stable(
    plan_factory: PlanFactory,
    handlers: Mapping[ActionKind, ActionHandler],
    *,
    clock: Clock,
    runtime: GapRuntimeState | None = None,
    lifecycle_hooks: GapLifecycleHooks | None = None,
    max_cycles: int = 3,
) -> GapRunResult:
    """Run a finite synchronous detect→enrich→resolve→validate→reassess loop."""
    if max_cycles < 1:
        raise ValueError("max_cycles must be >= 1")
    state = runtime or GapRuntimeState()
    cycles: list[GapCycleResult] = []

    for _ in range(max_cycles):
        before = plan_factory()
        if not before.gaps:
            return GapRunResult(tuple(cycles), before, "NO_GAPS")
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
            return GapRunResult(
                tuple(cycles),
                cycle.plan_after,
                "NO_PROGRESS_OR_SCHEDULED",
            )

    return GapRunResult(tuple(cycles), plan_factory(), "MAX_CYCLES_REACHED")
