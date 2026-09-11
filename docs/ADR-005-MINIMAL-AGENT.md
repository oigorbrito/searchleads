# ADR-005: Adopt core-first Minimal Agent Adapter

## Status
Accepted

## Context & Evidence
A partir da experimentação de agentes LLM autônomos iniciada na WAVE-03 até a WAVE-08, comparamos abordagens orquestradas como LangGraph e OpenAI Agents SDK, bem como abordagens leves nativas (Minimal). 

A avaliação live (WAVE-07B) demonstrou estruturalmente que a topologia core-first (Topologia A) aliada ao wrapper Minimal reduz overhead arquitetural e latência (em ~100-200ms) atingindo exatos mesmos indicadores de task success e safety. A evidência quantitativa determinou formalmente:
- `NO_FRAMEWORK_BENEFIT_OVER_MINIMAL`
- `TOPOLOGY_A_LIVE_DOMINANT`

## Decision
Adotamos a implementação "Minimal Agent Adapter" (localizada em `src/searchleads/agent/`) com a topologia "core-first".
Isso significa que a funcionalidade Agentic entra OFF por default (`AGENTIC_DEFAULT = OFF`) e, quando ligada, só é acionada após o SearchLeads Core falhar em resolver deterministicamente a task.

## Scope Limitation
O resultado atual foi referendado em cima do modelo `gemini-3.5-flash` para o corpus MVP fechado (C1 a C7). 

## Alternatives Evaluated
- **LangGraph**: Over-engineering sem ganho de precisão neste escopo.
- **OpenAI Agents SDK**: Funcional, porém requer adapter ou infra compativel e insere camadas indiretas na stack sem trade-off positivo justificado.
- **OpenManus**: Alternativa bloqueada por runtime (`PYTHON_RUNTIME_BLOCKED`), mantida apenas como open question para exploração posterior.
