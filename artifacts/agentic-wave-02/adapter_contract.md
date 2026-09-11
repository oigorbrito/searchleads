# AgentTopologyAdapter Contract
Operations required for framework integration:
1. 
eceive_state(case): Parses domain state into framework context.
2. choose_tool(context): Selects next tool.
3. invoke_searchleads_tool(tool, args): Proxies execution to domain.
4. 
eceive_observation(result): Updates context.
5. decide_continue_or_stop(context): Checks stop condition.
6. mit_trace(): Logs workflow telemetry.
