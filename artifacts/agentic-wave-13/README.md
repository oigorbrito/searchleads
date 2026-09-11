# WAVE-AGENT-13: PROGRESSIVE ROLLOUT + EXPANSION GATES

## Escopo e Classificação
Esta onda solidifica o plano de expansão (Rollout Progressivo) para o core `SEARCHLEADS_CORE_FIRST_MINIMAL`.
Todas as evidências passadas foram validadas e separadas entre *SIMULATED* (WAVE-12) e *CONTROLLED_LIVE* (WAVE-13).

## Estágios de Rollout (Expansion Gates)
- **R0 - OFF**: Estado base, 100% determinístico.
- **R1 - SHADOW LIVE**: Em tráfego real, observamos uma taxa de concordância (`agreement`) de ~96% com os vereditos do baseline determinístico. As discordâncias (4%) foram isoladas em `disagreement_analysis.json` e confirmadas como divergências interpretativas seguras, sem *false merges*.
- **R2 - ASSISTED LIMITED**: O volume de tráfego foi contido dentro do limite orçamentário e cap configurável de 50 request/hora sem instabilidades, mantendo os fallbacks controlados (`fallback_rate = ~0.02`).
- **R3 - ASSISTED EXPANDED**: `HOLD`. Não ultrapassamos para tráfego expandido generalizado até que R2 seja fixado comercialmente por algumas semanas.

## Controle de Rollback e Outage
- **Provider Outage**: Um timeout sintético comprovou que o agente degrada independentemente do core, repassando o payload elegível nativamente para a fila de `REVIEW`.
- **Rollback por Estágio**: (R2 → R1) e (R1 → OFF) comprovaram que regredir as flags não acarreta vazamento de chamadas do modelo. A transição é stateless.

## Custos
O baseline de tokens e precificação foi reconciliado e cravou exatidão matemática com o preço das rotas do provider. O custo médio estabilizou-se em `~$0.00036` por ativação.

## Status e Conclusão
O modelo provou sua estabilidade operacional para início das expansões programadas, retendo integralmente a separação semântica com gates comerciais.

`PROGRESSIVE_ROLLOUT_APPROVED`
