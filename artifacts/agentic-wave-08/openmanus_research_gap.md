# OpenManus Research Gap

## Status
Não funcionalmente avaliado na WAVE-07B e WAVE-08.

## Por que não foi avaliado
O framework foi bloqueado no gate de infraestrutura (`PYTHON_RUNTIME_BLOCKED`). O projeto oficial da FoundationAgents (OpenManus) estabelece uma dependência upstream estrita de Python 3.12. A codebase do SearchLeads atualmente se encontra ancorada em Python 3.13.14. 

## Python/runtime requirement observado
A criação do ambiente `py -3.12 -m venv .venv-exp-openmanus` falhou pela ausência física do interpretador compatível na máquina atual, impedindo a viabilização inicial sem comprometer a política restritiva da onda (que proíbe a degradação silenciosa do host local).

## O que faltaria para um benchmark justo
Para reavaliar de forma rigorosa:
1. Instalação e provisionamento formal do runtime CPython 3.12 na máquina.
2. Isolamento de ambiente compatível (`.venv-exp-openmanus`).
3. Uma interface de roteamento entre o OpenManus (`ModelProvider`) com nossas SearchLeads Tools.
4. Desativação completa dos seus defaults de Browser/MCP, nivelando-o ao baseline para focar puramente em orquestração de chamadas de tool.

## Artefatos existentes que poderiam ser reutilizados
* Traces divergentes da WAVE-07B
* Configurações de Budget (budget_policy.json)
* Tool Allowlist (tool_allowlist.json)
* Scripts de medição (scorer e pipeline de batch live)
