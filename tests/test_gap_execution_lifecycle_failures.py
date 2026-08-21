import unittest
from datetime import datetime, timezone

from searchleads.gap_automation import (
    ActionDisposition,
    ActionKind,
    AutomationAction,
    AutomationPlan,
    Gap,
    GapKind,
)
from searchleads.gap_execution import (
    GapLifecycleHooks,
    GapRuntimeState,
    execute_and_reassess_gap_cycle,
)


def plan_with_gap():
    gap = Gap("gap-1", "company-1", GapKind.MISSING_FIELD, "state")
    action = AutomationAction(
        action_id="action-1",
        company_id="company-1",
        gap_id="gap-1",
        action_kind=ActionKind.BRASILAPI_LOOKUP,
        disposition=ActionDisposition.READY,
        reason="known registry capability",
        cache_key="brasilapi:company-1",
        retry_max_attempts=1,
        min_interval_seconds=0,
    )
    return AutomationPlan("company-1", (gap,), (action,))


class GapLifecycleFailureTests(unittest.TestCase):
    def test_resolve_failure_does_not_leave_action_cached(self):
        runtime = GapRuntimeState()
        handler_calls = []
        validate_calls = []

        def handler(_action):
            handler_calls.append("enrich")

        def resolve():
            raise RuntimeError("resolve failed")

        def validate():
            validate_calls.append("validate")

        with self.assertRaisesRegex(RuntimeError, "resolve failed"):
            execute_and_reassess_gap_cycle(
                plan_with_gap,
                {ActionKind.BRASILAPI_LOOKUP: handler},
                clock=lambda: datetime(2026, 8, 21, tzinfo=timezone.utc),
                runtime=runtime,
                lifecycle_hooks=GapLifecycleHooks(resolve=resolve, validate=validate),
            )

        self.assertEqual(handler_calls, ["enrich"])
        self.assertEqual(validate_calls, [])
        self.assertNotIn("brasilapi:company-1", runtime.successful_cache_keys)

    def test_validate_failure_does_not_leave_action_cached(self):
        runtime = GapRuntimeState()
        calls = []

        def handler(_action):
            calls.append("enrich")

        def resolve():
            calls.append("resolve")

        def validate():
            calls.append("validate")
            raise RuntimeError("validate failed")

        with self.assertRaisesRegex(RuntimeError, "validate failed"):
            execute_and_reassess_gap_cycle(
                plan_with_gap,
                {ActionKind.BRASILAPI_LOOKUP: handler},
                clock=lambda: datetime(2026, 8, 21, tzinfo=timezone.utc),
                runtime=runtime,
                lifecycle_hooks=GapLifecycleHooks(resolve=resolve, validate=validate),
            )

        self.assertEqual(calls, ["enrich", "resolve", "validate"])
        self.assertNotIn("brasilapi:company-1", runtime.successful_cache_keys)


if __name__ == "__main__":
    unittest.main()
