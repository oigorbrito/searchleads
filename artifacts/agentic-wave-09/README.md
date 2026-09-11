# WAVE-AGENT-09: MINIMAL-A PRODUCTIONIZATION

## Resumo da Operação
A arquitetura `Minimal-A` (SearchLeads → Minimal Agent Adapter) foi canonicamente implementada e promovida para o código de produção (`src/searchleads/agent/`). A topologia garante a autoridade determinística do SearchLeads, acionando o framework agentic apenas como via de escalonamento. 

## Destaques da Promoção
- **Default OFF**: O sistema Agentic entra nativamente desligado (`AgentEscalationPolicy(enabled=False)`).
- **Sem Frameworks Invasivos**: LangGraph, OpenAI Agents SDK e afins foram descartados de forma definitiva (confirmando a diretriz de `NO_FRAMEWORK_BENEFIT_OVER_MINIMAL` das ondas anteriores).
- **Provider Intercambiável**: O núcleo de domínio acopla via protocolo (`ModelProvider`) em vez de Gemini SDK.
- **Autoridade e Segurança**: A verificação de limites (budget/timeout) produz terminologias seguras em *REVIEW*.
- **Live vs Canonical**: Testes rodaram 100% integrados em ambiente canônico usando Mock Providers (891 testes passaram limpos). Os testes live de integração de API estão isolados em suas suítes separadas.
- **ADR Registrado**: Em `docs/ADR-005-MINIMAL-AGENT.md`.

## OpenManus
`OPENMANUS_RESEARCH_STATUS = NON_BLOCKING_OPEN_QUESTION`. Permanecerá para ondas puramente de pesquisa se e quando o sistema base for subido para suportar seu ambiente imperativo de execução (Python 3.12+).

## Conclusão
`MINIMAL_A_PROMOTED`
`PRIMARY_AGENTIC_ARCHITECTURE = SEARCHLEADS_CORE_FIRST_MINIMAL`
`WAVE_AGENT_09 = CLOSED`
