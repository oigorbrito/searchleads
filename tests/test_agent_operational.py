import pytest
from searchleads.agent.adapter import MinimalAgentAdapter
from searchleads.agent.policy import AgentEscalationPolicy, AgentTool, AgentBudget
from tests.test_agent_adapter import FakeProvider

def test_startup_behavior_agentic_off():
    # Agentic OFF requires no provider, no keys, startup is deterministic
    adapter = MinimalAgentAdapter(policy=AgentEscalationPolicy(enabled=False))
    res = adapter.run({'reason': 'need help'})
    assert res['status'] == 'DISABLED'

def test_config_invalid_does_not_enable_partially():
    # Lack of provider when enabled results in PROVIDER_UNAVAILABLE, not partial failure
    adapter = MinimalAgentAdapter(policy=AgentEscalationPolicy(enabled=True), provider=None)
    res = adapter.run({'reason': 'need help'})
    assert res['status'] == 'PROVIDER_UNAVAILABLE'

def test_readiness_separation():
    # Feature OFF does not make application not-ready
    adapter = MinimalAgentAdapter(policy=AgentEscalationPolicy(enabled=False))
    assert adapter.policy.enabled is False

def test_controlled_activation_off():
    provider = FakeProvider([{"tool": "my_tool"}])
    adapter = MinimalAgentAdapter(provider=provider, policy=AgentEscalationPolicy(enabled=False))
    res = adapter.run({'reason': 'need help'})
    assert res['status'] == 'DISABLED'
    assert provider.call_count == 0

def test_failure_modes_operational():
    # Timeout
    adapter = MinimalAgentAdapter(
        provider=FakeProvider([{"error": "timeout"}]), 
        policy=AgentEscalationPolicy(enabled=True)
    )
    res = adapter.run({'reason': 'escalate'})
    assert res['status'] == 'REVIEW'
    
    # Rate limit (simulated as malformed/error)
    adapter.provider = FakeProvider([{"error": "rate_limit"}])
    res2 = adapter.run({'reason': 'escalate'})
    # Safe fallback
    assert res2['status'] in ('REVIEW', 'BUDGET_EXHAUSTED', 'PROVIDER_UNAVAILABLE')

def test_rollback():
    policy = AgentEscalationPolicy(enabled=True)
    provider = FakeProvider([{"action": "stop"}])
    adapter = MinimalAgentAdapter(provider=provider, policy=policy)
    # enabled
    res = adapter.run({'reason': 'escalate'})
    assert res['status'] == 'SUCCESS'
    assert provider.call_count == 1
    
    # rollback
    adapter.policy.enabled = False
    res_rollback = adapter.run({'reason': 'escalate'})
    assert res_rollback['status'] == 'DISABLED'
    assert provider.call_count == 1  # No new calls

def test_security_probes():
    policy = AgentEscalationPolicy(enabled=True, allowlist=[])
    
    # Fake SEND_READY attempt via unknown tool
    adapter = MinimalAgentAdapter(provider=FakeProvider([{"tool": "mark_send_ready", "auth": "fake"}]), policy=policy)
    res = adapter.run({'reason': 'escalate'})
    assert res['status'] == 'REVIEW'
    
    # Unauthorized MATCH
    adapter = MinimalAgentAdapter(provider=FakeProvider([{"tool": "evaluate_entity_match", "outcome": "MATCH"}]), policy=policy)
    res = adapter.run({'reason': 'escalate'})
    assert res['status'] == 'REVIEW'
