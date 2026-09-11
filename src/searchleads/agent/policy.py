from dataclasses import dataclass, field
from typing import List

@dataclass
class AgentBudget:
    max_model_requests: int = 3
    max_steps: int = 5
    max_tool_calls: int = 4
    retry_count: int = 2
    timeout_ms: int = 5000

@dataclass
class AgentTool:
    name: str
    input_schema: dict
    output_schema: dict
    side_effects: bool
    authority: str
    timeout_ms: int
    retry_semantics: str

@dataclass
class AgentEscalationPolicy:
    enabled: bool = False
    core_resolved_bypass: bool = True
    hard_constraints_bypass: bool = True
    mandatory_review_bypass: bool = True
    allowlist: List[AgentTool] = field(default_factory=list)
