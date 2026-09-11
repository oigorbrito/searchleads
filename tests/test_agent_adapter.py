import pytest
from searchleads.agent.provider import ModelProvider
from searchleads.agent.policy import AgentEscalationPolicy, AgentBudget, AgentTool
from searchleads.agent.adapter import MinimalAgentAdapter

class FakeProvider:
    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0

    def generate(self, prompt: str) -> str:
        return "fake"

    def tool_call(self, prompt: str, tools: list) -> dict:
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        return {"action": "stop"}

    def usage(self) -> dict:
        return {"tokens": 100}

    def model_id(self) -> str:
        return "fake-model"

def test_agent_disabled_preserves_legacy():
    adapter = MinimalAgentAdapter(policy=AgentEscalationPolicy(enabled=False))
    res = adapter.run({'reason': 'need help'})
    assert res['status'] == 'DISABLED'

def test_deterministic_bypass_produces_zero_model_calls():
    policy = AgentEscalationPolicy(enabled=True)
    adapter = MinimalAgentAdapter(provider=FakeProvider([]), policy=policy)
    res = adapter.run({'core_resolved': True})
    assert res['status'] == 'BYPASS_CORE_RESOLVED'
    assert adapter.provider.call_count == 0

def test_authorized_escalation_invokes_provider():
    policy = AgentEscalationPolicy(enabled=True, allowlist=[
        AgentTool('my_tool', {}, {}, False, 'none', 1000, 'none')
    ])
    adapter = MinimalAgentAdapter(provider=FakeProvider([{"tool": "my_tool"}]), policy=policy)
    res = adapter.run({'reason': 'escalate'})
    assert res['status'] == 'SUCCESS'
    assert adapter.provider.call_count == 1

def test_mandatory_review_cannot_be_overridden():
    policy = AgentEscalationPolicy(enabled=True)
    adapter = MinimalAgentAdapter(provider=FakeProvider([]), policy=policy)
    res = adapter.run({'mandatory_review': True})
    assert res['status'] == 'BYPASS_MANDATORY_REVIEW'

def test_hallucinated_tool_rejected():
    policy = AgentEscalationPolicy(enabled=True, allowlist=[])
    adapter = MinimalAgentAdapter(provider=FakeProvider([{"tool": "hallucinated"}]), policy=policy)
    res = adapter.run({'reason': 'escalate'})
    assert res['status'] == 'REVIEW'

def test_timeout_safe_fallback():
    policy = AgentEscalationPolicy(enabled=True, allowlist=[])
    adapter = MinimalAgentAdapter(provider=FakeProvider([{"error": "timeout"}]), policy=policy)
    res = adapter.run({'reason': 'escalate'})
    assert res['status'] == 'REVIEW'

def test_budget_exhausted_safe_fallback():
    policy = AgentEscalationPolicy(enabled=True, allowlist=[
        AgentTool('my_tool', {}, {}, False, 'none', 1000, 'none')
    ])
    budget = AgentBudget(max_steps=2)
    # Give it 3 tool calls, but budget is 2
    adapter = MinimalAgentAdapter(provider=FakeProvider([{"tool": "my_tool"}, {"tool": "my_tool"}, {"tool": "my_tool"}]), policy=policy, budget=budget)
    res = adapter.run({'reason': 'escalate'})
    assert res['status'] == 'BUDGET_EXHAUSTED'

def test_provider_unavailable_safe_fallback():
    policy = AgentEscalationPolicy(enabled=True)
    adapter = MinimalAgentAdapter(provider=None, policy=policy)
    res = adapter.run({'reason': 'escalate'})
    assert res['status'] == 'PROVIDER_UNAVAILABLE'
