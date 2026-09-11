from typing import Optional, Any
from .provider import ModelProvider
from .policy import AgentEscalationPolicy, AgentBudget
from .trace import AgentTrace

class MinimalAgentAdapter:
    def __init__(self, provider: Optional[ModelProvider] = None, policy: Optional[AgentEscalationPolicy] = None, budget: Optional[AgentBudget] = None):
        self.provider = provider
        self.policy = policy or AgentEscalationPolicy()
        self.budget = budget or AgentBudget()

    def run(self, context: dict, request_id: str = '') -> dict:
        trace = AgentTrace(request_id=request_id)
        if not self.policy.enabled:
            return {'status': 'DISABLED', 'trace': trace}
        
        # Core checks
        if self.policy.core_resolved_bypass and context.get('core_resolved'):
            return {'status': 'BYPASS_CORE_RESOLVED', 'trace': trace}
        if self.policy.hard_constraints_bypass and context.get('hard_constraints_met'):
            return {'status': 'BYPASS_HARD_CONSTRAINTS', 'trace': trace}
        if self.policy.mandatory_review_bypass and context.get('mandatory_review'):
            return {'status': 'BYPASS_MANDATORY_REVIEW', 'trace': trace}

        if not self.provider:
            return {'status': 'PROVIDER_UNAVAILABLE', 'trace': trace}

        trace.model_id = self.provider.model_id()
        trace.escalation_reason = context.get('reason', 'unknown')

        try:
            # Simulate basic agent loop with budget limits
            for step in range(self.budget.max_steps):
                resp = self.provider.tool_call(str(context), self.policy.allowlist)
                trace.actions.append(resp)
                
                # Check safe failure semantics
                if 'error' in resp:
                    trace.stop_reason = resp['error'].upper()
                    return {'status': 'REVIEW', 'trace': trace}
                elif 'tool' in resp and resp.get('tool') not in [t.name for t in self.policy.allowlist]:
                    trace.stop_reason = 'UNKNOWN_TOOL'
                    return {'status': 'REVIEW', 'trace': trace}

                if resp.get('action') == 'stop':
                    break
            else:
                trace.stop_reason = 'BUDGET_EXHAUSTED'
                return {'status': 'BUDGET_EXHAUSTED', 'trace': trace}

        except Exception:
            return {'status': 'REVIEW', 'trace': trace}

        trace.stop_reason = 'SUCCESS'
        return {'status': 'SUCCESS', 'trace': trace}
