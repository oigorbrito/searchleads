# Immediate Rollback Runbook

Em caso de violações de segurança (Safety Invariants) ou degradação sistêmica inaceitável, execute imediatamente os passos abaixo:

1. **Set agentic OFF**
   - Altere a flag de configuração do adapter para `enabled=False` no gerenciador de features, **sem** necessidade de redeploy de código.

2. **Verify zero new model calls**
   - Monitore a telemetria em tempo real para confirmar que a taxa de `model_requests` caiu para `0`.

3. **Verify deterministic path**
   - Verifique se os novos casos estão seguindo o caminho de fallback natural (resolução pelo core determinístico ou repasse para fila humana de `REVIEW`).

4. **Preserve traces**
   - Isole os logs e traces associados ao identificador do incidente (filtrando por `trace_id` ou janela de tempo) para futura auditoria e explainability. Não expurgue ou limpe os traces do banco.

5. **Classify incident**
   - Classifique o evento utilizando a `incident_taxonomy.json` (ex: SAFETY, PROVIDER, COST, PERFORMANCE).

6. **Run canonical smoke/regression as needed**
   - Acione o pipeline de CI determinístico (baseline) para atestar que o SearchLeads permaneceu íntegro sob as condições de isolamento atuais.

**Nota de Integridade:** Nenhum rollback deve exigir manipulação destrutiva (apagar state canônico ou rodar migrations de rollback) da base de dados principal. A desativação lógica assegura reversibilidade limpa.
