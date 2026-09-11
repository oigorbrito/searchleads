from dataclasses import dataclass, field
from typing import List, Dict, Any
import uuid

@dataclass
class AgentTrace:
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ''
    model_id: str = ''
    escalation_reason: str = ''
    actions: List[Dict[str, Any]] = field(default_factory=list)
    stop_reason: str = ''
    authority_attempts: int = 0
    usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: int = 0
