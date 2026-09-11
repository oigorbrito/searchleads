# WAVE-AGENT-07R: Framework Installation Remediation

## Objetivo
Resolver pendências de instalação (INSTALLATION_BLOCKED) da WAVE-07, migrando os frameworks suportados para `LIVE_SMOKE_READY` de modo a validar suas integrações nativas ao provedor Gemini.

## Resumo dos Resultados (Block 18)
* **LangGraph**: `LIVE_SMOKE_READY` (Instalação via Python 3.13, integração validada via langchain-google-genai, provedor acessível via gemini-3.5-flash)
* **Agents SDK (OpenAI)**: `LIVE_SMOKE_READY` (Instalação em Python 3.13, uso nativo via OpenAI-compatible endpoint em `generativelanguage.googleapis.com`)
* **OpenManus**: `PYTHON_RUNTIME_BLOCKED` (Requisito upstream restrito ao Python 3.12 ausente no ambiente, bloqueado conforme Block 9).

## Regressão do Baseline
Executado sem side-effects no repositório principal:
- 0 falhas e 0 erros no `.venv-baseline` (883 passed).

## Decisão Global
`SOME_FRAMEWORKS_LIVE_SMOKE_READY`
WAVE_AGENT_07R = CLOSED. Prontos para avançar para a WAVE-AGENT-07B (Live Benchmark Completion).
