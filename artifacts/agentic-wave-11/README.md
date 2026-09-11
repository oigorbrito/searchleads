# WAVE-AGENT-11: LIVE CERTIFICATION PROBES & REGRESSION

## Probes Re-Validation (Blocks 7-12)
Os cenários obrigatórios de *Live Certification* foram processados, confirmando a robustez da arquitetura:
* **Authority Boundary (Block 7)**: O adapter intercepta e anula (*AUTHORITY_VIOLATION_ATTEMPT*) qualquer decisão de MATCH, QUALIFIED ou SEND_READY vinda indevidamente do agente se o core determinou estado distinto (ex: REVIEW/ABSTAIN).
* **Deterministic Bypass (Block 8)**: Quando o core resolve nativamente um caso, o agent reporta *activation = false* e *model requests = 0*, mantendo total dependência do baseline core sem invocar a cloud.
* **Provider Failure (Block 9)**: Timeout deliberado ou falha de credenciais não derrubam o processo; convertem em fallback seguro para REVIEW.
* **Budget Limits (Block 10)**: O exaurimento intencional de chamadas do loop disparou `BUDGET_EXHAUSTED`, prevenindo loops recursivos invisíveis.
* **Observability & Replay (Block 11-12)**: Traces gerados sem segredos embutidos, garantindo total explainability canônica (escalation reason, call args, outcomes).

## Canonical Regression (Block 14)
- Suite canônica (Pytest): **898 tests passed (0 failed, 0 errors)**.
- Internal RC Hygiene Check: **PASS**.

## Release Gates (Block 15)
Definições imutáveis:
* `CODE_READY` = **PASS** (Canonical test suite & security gates PASS)
* `LIVE_CERTIFIED` = **PASS** (Todas as probes live e operacionais PASS)
* `AGENTIC_RELEASE_READY` = **PASS** (Rollback operacional comprovado e configuração default=OFF preservada)
* `SEND_READY` = **NOT_IMPLIED** (Decisões de envio ou qualificações comerciais seguem de posse da camada determinística, sem autoridade transacional delegada).

## Status de Arquitetura & Pesquisa
`PRIMARY_AGENTIC_ARCHITECTURE = SEARCHLEADS_CORE_FIRST_MINIMAL`
`OPENMANUS_RESEARCH_STATUS = NON_BLOCKING_OPEN_QUESTION`
