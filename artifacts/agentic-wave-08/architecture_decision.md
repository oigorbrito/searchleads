# Architecture Decision: Minimal Agent Approach

## Context
Decidimos utilizar a abordagem Minimal-A (SearchLeads → Agent), onde o modelo só é acionado como fallback (escalation) após o core da aplicação determinar insuficiência para resolver o caso determinísticamente. 

## Abstração de Provider
A implementação rompe a dependência estrita do Gemini na superfície da interface. A abstração central passa a ser o `ModelProvider`, que assina:
* `generate()`
* `tool_call()`
* `usage()`
* `model_id()`

Embora Gemini 3.5 Flash seja a primeira implementação validada, o adapter não acopla as lógicas de negócio a detalhes da sua API de forma vazada. LangGraph e Agents SDK não foram adotados.

## Segurança e Falhas (Failure Semantics)
Qualquer falha do agentic framework (timeout, hallucination, formato inválido) aciona um *deterministic fallback* para o estado explícito de falha ou `REVIEW`. Um erro do agente nunca deve resultar numa decisão comercial `SEND_READY`. Os limites de budget são aplicados rigorosamente, terminando em `BUDGET_EXHAUSTED` se as chamadas excederem o limite, evitando loops infinitos e invisíveis.
