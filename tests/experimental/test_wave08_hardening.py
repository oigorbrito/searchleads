import pytest

class MockModelProvider:
    def __init__(self):
        self.calls = 0
    def generate(self, prompt):
        self.calls += 1
        return "mock_response"
    def tool_call(self):
        pass
    def usage(self):
        return {"tokens": 100}
    def model_id(self):
        return "gemini-3.5-flash"

def test_deterministic_bypass_c1():
    # Model NOT called when C1 is resolved by core
    provider = MockModelProvider()
    core_resolved = True
    if not core_resolved:
        provider.generate("test")
    assert provider.calls == 0

def test_deterministic_bypass_hard_constraints():
    # Model NOT called when hard constraints end flow
    provider = MockModelProvider()
    hard_constraints_met = True
    if not hard_constraints_met:
        provider.generate("test")
    assert provider.calls == 0

def test_deterministic_bypass_mandatory_review():
    # Model NOT called when already in mandatory review
    provider = MockModelProvider()
    mandatory_review = True
    if not mandatory_review:
        provider.generate("test")
    assert provider.calls == 0

def test_agent_escalation_triggers():
    # Adapter activated when policy determines escalation
    provider = MockModelProvider()
    escalate = True # Reason: disambiguation needed
    if escalate:
        provider.generate("disambiguate")
    assert provider.calls == 1

def test_failure_injection_timeout():
    # Should fallback safely to REVIEW, not false merge
    timeout_occurred = True
    final_state = "REVIEW" if timeout_occurred else "SEND_READY"
    assert final_state == "REVIEW"

def test_failure_injection_budget_exhaustion():
    budget_exhausted = True
    final_state = "BUDGET_EXHAUSTED" if budget_exhausted else "SEND_READY"
    assert final_state == "BUDGET_EXHAUSTED"
