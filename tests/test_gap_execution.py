from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest

from searchleads.gap_automation.execution import (
    ActionExecutionStatus, GapLifecycleHooks, GapRuntimeState,
    execute_and_reassess_gap_cycle, execute_gap_plan, run_gap_automation_until_stable,
)
from searchleads.gap_automation.planning import (
    ActionDisposition, ActionEffect, ActionKind, AutomationAction, AutomationPlan,
)

NOW = datetime(2026, 8, 26, 4, 0, tzinfo=timezone.utc)
REQ = object()
GAP = SimpleNamespace(gap_id="gap:1")


def ready(kind=ActionKind.BRASILAPI_POINT_LOOKUP, *, action_id="a1", cache="cache:1", attempts=3, interval=60):
    return AutomationAction(
        action_id, "gap:1", ActionDisposition.READY, kind,
        ActionEffect.PREREQUISITE, "ready",
        retry_max_attempts=attempts, cache_key=cache, min_interval_seconds=interval,
    )


def blocked():
    return AutomationAction(
        "b1", "gap:1", ActionDisposition.BLOCKED, None,
        ActionEffect.NONE, "blocked reason",
    )


def plan(actions=(), gaps=(GAP,)):
    return AutomationPlan("company:1", REQ, gaps, tuple(actions))


def test_naive_now_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        execute_gap_plan(plan(), {}, now=datetime(2026, 1, 1), runtime=GapRuntimeState())


def test_blocked_plan_action_remains_blocked():
    record = execute_gap_plan(plan((blocked(),)), {}, now=NOW, runtime=GapRuntimeState())[0]
    assert (record.status, record.attempts, record.reason) == (
        ActionExecutionStatus.BLOCKED, 0, "blocked reason",
    )


def test_defensively_blocks_malformed_ready_metadata():
    malformed = ready()
    object.__setattr__(malformed, "cache_key", None)
    object.__setattr__(malformed, "retry_max_attempts", 0)
    record = execute_gap_plan(plan((malformed,)), {}, now=NOW, runtime=GapRuntimeState())[0]
    assert record.status is ActionExecutionStatus.BLOCKED
    assert "finite retry/cache" in record.reason


def test_success_retries_finitely_then_caches():
    state = GapRuntimeState()
    calls = []

    def handler(action):
        calls.append(action.action_id)
        if len(calls) == 1:
            raise RuntimeError("transient")

    action = ready()
    record = execute_gap_plan(
        plan((action,)), {action.action_kind: handler}, now=NOW, runtime=state,
    )[0]
    assert record.status is ActionExecutionStatus.SUCCEEDED and record.attempts == 2
    assert state.successful_cache_keys == {"cache:1"}
    assert state.last_attempt_at["cache:1"] == NOW

    second = execute_gap_plan(
        plan((action,)), {action.action_kind: handler},
        now=NOW + timedelta(seconds=1), runtime=state,
    )[0]
    assert second.status is ActionExecutionStatus.CACHE_HIT and second.attempts == 0
    assert len(calls) == 2


def test_minimum_interval_schedules_without_handler_call():
    state = GapRuntimeState(last_attempt_at={"cache:1": NOW})
    action = ready()
    calls = []
    record = execute_gap_plan(
        plan((action,)), {action.action_kind: lambda a: calls.append(a)},
        now=NOW + timedelta(seconds=10), runtime=state,
    )[0]
    assert record.status is ActionExecutionStatus.SCHEDULED
    assert record.next_eligible_at == NOW + timedelta(seconds=60)
    assert calls == []


def test_naive_runtime_last_attempt_is_rejected():
    state = GapRuntimeState(last_attempt_at={"cache:1": datetime(2026, 1, 1)})
    action = ready()
    with pytest.raises(ValueError, match="timezone-aware"):
        execute_gap_plan(
            plan((action,)), {action.action_kind: lambda a: None}, now=NOW, runtime=state,
        )


def test_missing_explicit_handler_is_blocked():
    record = execute_gap_plan(plan((ready(),)), {}, now=NOW, runtime=GapRuntimeState())[0]
    assert record.status is ActionExecutionStatus.BLOCKED
    assert record.reason == "no explicit handler supplied for planned known action"


def test_failure_exhausts_exact_bound_and_sets_next_eligible():
    action = ready(attempts=2, interval=30)
    calls = []

    def fail(a):
        calls.append(a)
        raise RuntimeError("nope")

    record = execute_gap_plan(
        plan((action,)), {action.action_kind: fail}, now=NOW, runtime=GapRuntimeState(),
    )[0]
    assert record.status is ActionExecutionStatus.FAILED
    assert record.attempts == 2 and len(calls) == 2
    assert record.executed_at == NOW
    assert record.next_eligible_at == NOW + timedelta(seconds=30)
    assert "nope" in record.reason


def test_failure_without_interval_has_no_next_eligible():
    action = ready(attempts=1, interval=0)

    def fail(_):
        raise RuntimeError("x")

    record = execute_gap_plan(
        plan((action,)), {action.action_kind: fail}, now=NOW, runtime=GapRuntimeState(),
    )[0]
    assert record.status is ActionExecutionStatus.FAILED
    assert record.next_eligible_at is None


def test_cycle_runs_explicit_lifecycle_order_only_after_success():
    events = []
    action = ready(interval=0)
    calls = iter([plan((action,)), plan((action,))])

    def factory():
        events.append("detect" if not events else "reassess")
        return next(calls)

    hooks = GapLifecycleHooks(
        lambda: events.append("resolve"), lambda: events.append("validate"),
    )
    result = execute_and_reassess_gap_cycle(
        factory, {action.action_kind: lambda a: events.append("enrich")},
        clock=lambda: NOW, runtime=GapRuntimeState(), lifecycle_hooks=hooks,
    )
    assert result.made_progress is True
    assert events == ["detect", "enrich", "resolve", "validate", "reassess"]


def test_cycle_skips_hooks_when_nothing_succeeds():
    events = []
    calls = iter([plan((blocked(),)), plan((blocked(),))])
    hooks = GapLifecycleHooks(
        lambda: events.append("resolve"), lambda: events.append("validate"),
    )
    result = execute_and_reassess_gap_cycle(
        lambda: next(calls), {}, clock=lambda: NOW,
        runtime=GapRuntimeState(), lifecycle_hooks=hooks,
    )
    assert result.made_progress is False
    assert events == []


def test_run_returns_no_gaps_without_cycle():
    empty = plan((), gaps=())
    result = run_gap_automation_until_stable(lambda: empty, {}, clock=lambda: NOW)
    assert result.stop_reason == "NO_GAPS"
    assert result.cycles == () and result.final_plan is empty


def test_run_resolves_after_success_and_reassessment():
    action = ready(interval=0)
    before = plan((action,))
    after = plan((), gaps=())
    calls = iter([before, before, after])
    result = run_gap_automation_until_stable(
        lambda: next(calls), {action.action_kind: lambda a: None},
        clock=lambda: NOW, max_cycles=2,
    )
    assert result.stop_reason == "GAPS_RESOLVED"
    assert len(result.cycles) == 1


def test_run_stops_when_no_progress():
    before = plan((blocked(),))
    calls = iter([before, before, before])
    result = run_gap_automation_until_stable(lambda: next(calls), {}, clock=lambda: NOW)
    assert result.stop_reason == "NO_PROGRESS_OR_SCHEDULED"
    assert len(result.cycles) == 1


def test_run_reaches_max_cycles_when_every_cycle_progresses_but_gap_remains():
    a1 = ready(action_id="a1", cache="c1", interval=0)
    a2 = ready(action_id="a2", cache="c2", interval=0)
    p1 = plan((a1,))
    p2 = plan((a2,))
    p3 = plan((a2,))
    calls = iter([p1, p1, p2, p2, p2, p3, p3])
    handlers = {ActionKind.BRASILAPI_POINT_LOOKUP: lambda a: None}
    result = run_gap_automation_until_stable(
        lambda: next(calls), handlers, clock=lambda: NOW, max_cycles=2,
    )
    assert result.stop_reason == "MAX_CYCLES_REACHED"
    assert len(result.cycles) == 2 and result.final_plan is p3


def test_run_rejects_non_positive_max_cycles():
    with pytest.raises(ValueError, match="max_cycles"):
        run_gap_automation_until_stable(lambda: plan(), {}, clock=lambda: NOW, max_cycles=0)


def test_all_current_action_kinds_can_be_executed_only_via_explicit_handlers():
    actions = []
    for i, kind in enumerate(ActionKind):
        effect = (
            ActionEffect.DIRECT
            if kind in {ActionKind.CONTACT_PUBLICATION_VALIDATION, ActionKind.DENTAL_QUALIFICATION_EVALUATION}
            else ActionEffect.PREREQUISITE
        )
        action = AutomationAction(
            f"a{i}", "gap:1", ActionDisposition.READY, kind, effect, "ready",
            retry_max_attempts=1, cache_key=f"c{i}", min_interval_seconds=0,
        )
        actions.append(action)
    called = []
    handlers = {
        kind: (lambda a, k=kind: called.append((k, a.action_id))) for kind in ActionKind
    }
    records = execute_gap_plan(
        plan(tuple(actions)), handlers, now=NOW, runtime=GapRuntimeState(),
    )
    assert all(r.status is ActionExecutionStatus.SUCCEEDED for r in records)
    assert {kind for kind, _ in called} == set(ActionKind)


def test_elapsed_minimum_interval_allows_execution():
    state = GapRuntimeState(last_attempt_at={"cache:1": NOW - timedelta(seconds=61)})
    action = ready(interval=60)
    calls = []
    record = execute_gap_plan(
        plan((action,)), {action.action_kind: lambda a: calls.append(a.action_id)},
        now=NOW, runtime=state,
    )[0]
    assert record.status is ActionExecutionStatus.SUCCEEDED
    assert calls == ["a1"]
