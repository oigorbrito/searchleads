import unittest
from datetime import datetime, timedelta, timezone

from searchleads.gap_automation import (
    ActionDisposition,
    ActionKind,
    AutomationAction,
    AutomationPlan,
    Gap,
    GapKind,
)
from searchleads.gap_execution import (
    ActionExecutionStatus,
    GapLifecycleHooks,
    GapRuntimeState,
    execute_and_reassess_gap_cycle,
    execute_gap_plan,
    run_gap_automation_until_stable,
)

NOW = datetime(2026, 8, 21, 17, 0, tzinfo=timezone.utc)


def action(
    kind=ActionKind.BRASILAPI_LOOKUP,
    *,
    retry=3,
    interval=60,
    disposition=ActionDisposition.READY,
):
    return AutomationAction(
        "a1",
        Gap(GapKind.COMPANY_FIELD, "legal_name", "missing"),
        disposition,
        kind if disposition is ActionDisposition.READY else None,
        "reason",
        retry,
        "cache:1",
        interval,
    )


def plan(*actions):
    gaps = tuple(item.gap for item in actions)
    return AutomationPlan("company:1", gaps, tuple(actions))


class GapExecutionTests(unittest.TestCase):
    def test_success_executes_once_and_caches(self):
        calls = []
        runtime = GapRuntimeState()
        current = plan(action())
        result = execute_gap_plan(
            current,
            {ActionKind.BRASILAPI_LOOKUP: lambda item: calls.append(item.action_id)},
            now=NOW,
            runtime=runtime,
        )
        self.assertEqual(result[0].status, ActionExecutionStatus.SUCCEEDED)
        self.assertEqual(calls, ["a1"])

        cached = execute_gap_plan(
            current,
            {ActionKind.BRASILAPI_LOOKUP: lambda item: calls.append("again")},
            now=NOW + timedelta(seconds=61),
            runtime=runtime,
        )
        self.assertEqual(cached[0].status, ActionExecutionStatus.CACHE_HIT)
        self.assertEqual(calls, ["a1"])

    def test_retry_is_bounded(self):
        calls = []

        def fail(_):
            calls.append(1)
            raise RuntimeError("boom")

        result = execute_gap_plan(
            plan(action(retry=3)),
            {ActionKind.BRASILAPI_LOOKUP: fail},
            now=NOW,
            runtime=GapRuntimeState(),
        )
        self.assertEqual(len(calls), 3)
        self.assertEqual(result[0].status, ActionExecutionStatus.FAILED)
        self.assertEqual(result[0].attempts, 3)
        self.assertEqual(result[0].next_eligible_at, NOW + timedelta(seconds=60))

    def test_rate_limit_returns_schedule_time(self):
        runtime = GapRuntimeState(last_attempt_at={"cache:1": NOW})
        result = execute_gap_plan(
            plan(action()),
            {ActionKind.BRASILAPI_LOOKUP: lambda _: None},
            now=NOW + timedelta(seconds=20),
            runtime=runtime,
        )
        self.assertEqual(result[0].status, ActionExecutionStatus.SCHEDULED)
        self.assertEqual(result[0].next_eligible_at, NOW + timedelta(seconds=60))

    def test_blocked_action_is_never_executed(self):
        result = execute_gap_plan(
            plan(action(disposition=ActionDisposition.BLOCKED)),
            {},
            now=NOW,
            runtime=GapRuntimeState(),
        )
        self.assertEqual(result[0].status, ActionExecutionStatus.BLOCKED)

    def test_missing_handler_blocks_without_dynamic_dispatch(self):
        result = execute_gap_plan(
            plan(action()),
            {},
            now=NOW,
            runtime=GapRuntimeState(),
        )
        self.assertEqual(result[0].status, ActionExecutionStatus.BLOCKED)

    def test_cycle_reassesses_after_handler_mutates_state(self):
        missing = {"value": True}

        def factory():
            return (
                plan(action())
                if missing["value"]
                else AutomationPlan("company:1", (), ())
            )

        def handler(_):
            missing["value"] = False

        result = execute_and_reassess_gap_cycle(
            factory,
            {ActionKind.BRASILAPI_LOOKUP: handler},
            clock=lambda: NOW,
            runtime=GapRuntimeState(),
        )
        self.assertTrue(result.plan_before.gaps)
        self.assertFalse(result.plan_after.gaps)

    def test_cycle_orders_enrich_resolve_validate_then_reassess(self):
        events = []
        missing = {"value": True}

        def factory():
            events.append("detect" if not events else "reassess")
            return (
                plan(action())
                if missing["value"]
                else AutomationPlan("company:1", (), ())
            )

        def enrich(_):
            events.append("enrich")

        def resolve():
            events.append("resolve")

        def validate():
            events.append("validate")
            missing["value"] = False

        result = execute_and_reassess_gap_cycle(
            factory,
            {ActionKind.BRASILAPI_LOOKUP: enrich},
            clock=lambda: NOW,
            runtime=GapRuntimeState(),
            lifecycle_hooks=GapLifecycleHooks(resolve=resolve, validate=validate),
        )
        self.assertEqual(events, ["detect", "enrich", "resolve", "validate", "reassess"])
        self.assertFalse(result.plan_after.gaps)

    def test_lifecycle_hooks_do_not_run_without_successful_enrichment(self):
        events = []
        current = plan(action(disposition=ActionDisposition.BLOCKED))
        execute_and_reassess_gap_cycle(
            lambda: current,
            {},
            clock=lambda: NOW,
            runtime=GapRuntimeState(),
            lifecycle_hooks=GapLifecycleHooks(
                resolve=lambda: events.append("resolve"),
                validate=lambda: events.append("validate"),
            ),
        )
        self.assertEqual(events, [])

    def test_run_until_stable_resolves_gap(self):
        missing = {"value": True}

        def factory():
            return (
                plan(action())
                if missing["value"]
                else AutomationPlan("company:1", (), ())
            )

        def handler(_):
            missing["value"] = False

        result = run_gap_automation_until_stable(
            factory,
            {ActionKind.BRASILAPI_LOOKUP: handler},
            clock=lambda: NOW,
            max_cycles=3,
        )
        self.assertEqual(result.stop_reason, "GAPS_RESOLVED")
        self.assertEqual(len(result.cycles), 1)

    def test_run_until_stable_passes_lifecycle_hooks(self):
        state = {"enriched": False, "resolved": False, "validated": False}
        events = []

        def factory():
            complete = all(state.values())
            return AutomationPlan("company:1", (), ()) if complete else plan(action())

        def enrich(_):
            events.append("enrich")
            state["enriched"] = True

        def resolve():
            events.append("resolve")
            state["resolved"] = True

        def validate():
            events.append("validate")
            state["validated"] = True

        result = run_gap_automation_until_stable(
            factory,
            {ActionKind.BRASILAPI_LOOKUP: enrich},
            clock=lambda: NOW,
            lifecycle_hooks=GapLifecycleHooks(resolve=resolve, validate=validate),
            max_cycles=3,
        )
        self.assertEqual(result.stop_reason, "GAPS_RESOLVED")
        self.assertEqual(events, ["enrich", "resolve", "validate"])

    def test_run_stops_when_no_progress(self):
        current = plan(action(disposition=ActionDisposition.BLOCKED))
        result = run_gap_automation_until_stable(
            lambda: current,
            {},
            clock=lambda: NOW,
            max_cycles=3,
        )
        self.assertEqual(result.stop_reason, "NO_PROGRESS_OR_SCHEDULED")
        self.assertEqual(len(result.cycles), 1)

    def test_naive_clock_is_rejected(self):
        with self.assertRaises(ValueError):
            execute_gap_plan(
                plan(action()),
                {ActionKind.BRASILAPI_LOOKUP: lambda _: None},
                now=datetime(2026, 8, 21, 17, 0),
                runtime=GapRuntimeState(),
            )


if __name__ == "__main__":
    unittest.main()
