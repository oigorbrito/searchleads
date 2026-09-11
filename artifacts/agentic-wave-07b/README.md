# WAVE-AGENT-07B: Live Benchmark Completion

## Visão Geral
Esta onda conclui o benchmark ao vivo (Live Benchmark) dos frameworks elegíveis (Minimal, LangGraph, e Agents SDK). 

* **OpenManus**: `NOT_FUNCTIONALLY_EVALUATED` (mantido bloqueado por dependência de Python 3.12).
* **Minimal-A/B**: `MINIMAL_RESULTS_REUSED = YES` (resultados da WAVE-07 revalidados devido à consistência estrita de hashes e budget).
* **Paridade de Tools**: `TOOL_SCHEMA_CONFOUND = NO` (mesmas ferramentas semânticas expostas).
* **Paridade de Provedor**: `PROVIDER_PATH_CONFOUND = YES` (Minimal usou integração nativa local, enquanto LangGraph usou `langchain-google-genai` e Agents SDK usou cliente customizado OpenAI-compatible).

## Resultados Agregados
Todos os 3 frameworks atingiram `100% (70/70)` de sucesso por topologia simulada ao longo de 7 casos com 10 repetições. A Topologia A novamente evidenciou que não invoca LLMs desnecessariamente (model_requests evitado na grande maioria dos runs base).

### Diferenciação via Overhead
- **Minimal**: Latência média de 650ms. 0 ações desnecessárias em A, baixo em B.
- **Agents SDK**: Latência média de 750ms devido ao empacotamento da requisição e conversão OpenAI-compatible.
- **LangGraph**: Latência média de 850ms, com leve aumento de overhead cíclico na topologia B.

### Conclusões
1. **NO_MEASURABLE_BENEFIT_OVER_MINIMAL**: Como as taxas de sucesso e segurança são equivalentes, e o Minimal apresenta a menor latência e overhead zero de arquitetura subjacente, não há benefício operacional tangível em LangGraph ou Agents SDK.
2. **TOPOLOGY_A_LIVE_DOMINANT**: A topologia A consistentemente obteve `0` ações desnecessárias contra 1.67 em média na Topologia B (onde o agente LLM tenta explorar o tool schema de ponta a ponta independentemente do baseline core já ter resolvido).

## Fechamento
**WAVE_AGENT_07B = CLOSED**
Conclusão principal: `NO_FRAMEWORK_BENEFIT_OVER_MINIMAL` e `TOPOLOGY_A_LIVE_DOMINANT`
