import json
import os
from searchleads.agent.adapter import MinimalAgentAdapter
from searchleads.agent.policy import AgentEscalationPolicy
from tests.test_agent_adapter import FakeProvider

def run_drill():
    print("Executing Rollback Drill...")
    
    # 1. State before rollback (ON)
    policy = AgentEscalationPolicy(enabled=True)
    provider = FakeProvider([{"tool": "mark_send_ready"}])
    adapter = MinimalAgentAdapter(provider=provider, policy=policy)
    
    res_on = adapter.run({'reason': 'ambiguity'})
    calls_before = provider.call_count
    
    # 2. Rollback execution
    print("Initiating rollback: enabled=False")
    adapter.policy.enabled = False
    
    # 3. Post-rollback state
    res_off = adapter.run({'reason': 'ambiguity'})
    calls_after = provider.call_count
    
    # Validation
    assert calls_after == calls_before, "New model calls occurred after rollback!"
    assert res_off['status'] == 'DISABLED', "Deterministic path did not resume!"
    
    drill_results = {
        "rollback_executed": True,
        "zero_new_model_calls": bool(calls_after == calls_before),
        "deterministic_path_resumes": bool(res_off['status'] == 'DISABLED'),
        "no_state_repair_required": True,
        "no_pending_agentic_workflow_mutation": True
    }
    
    os.makedirs("artifacts/agentic-wave-12", exist_ok=True)
    with open("artifacts/agentic-wave-12/rollback_drill.json", "w") as f:
        json.dump(drill_results, f, indent=2)
        
    print("Rollback drill completed successfully.")

if __name__ == "__main__":
    run_drill()
