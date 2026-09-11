# WAVE-AGENT-15: EVENT-DRIVEN REVALIDATION PROTOCOL

## Resumo
A WAVE-15 formaliza a matriz operacional da governança estabelecida na WAVE-14, transmutando-a em um **Mecanismo de Revalidação Orientada a Eventos**. Nenhuma nova arquitetura foi introduzida; apenas a amarração burocrática e técnica para sustentar as atualizações do `SEARCHLEADS_CORE_FIRST_MINIMAL` no longo prazo.

## Modelo de Revalidação por Evento
Diferente de certificações periódicas estáticas, o sistema revalida apenas perante gatilhos definidos (`trigger_catalog.json`), englobando alterações no Modelo, Provider, Prompt, Tools, Policy, Core ou alertas de Incidentes/Drifts.

As revalidações são classificadas (`revalidation_levels.json`) em:
- **R0**: Nenhuma revalidação estrutural. Restrito a documentação ou refatoração compatível. Requer regressão canônica padrão.
- **R1**: Smoke revalidation. Para patches menores e compatíveis.
- **R2**: Targeted recertification. Avaliações contidas em subset do frozen corpus para mudanças no SDK, no schema das tools ou prompts materiais.
- **R3**: Full recertification. Protocolo completo de rollout para transições maiores como trocas de modelo ou incidentes de segurança críticos.

## Champion / Challenger e Custódia
O modelo atual é tratado formalmente como `CHAMPION`. Upgrades não são automáticos; novas versões (como futuros modelos) são `CHALLENGERS` que exigem provar ausência de degradação e preservar os invariantes para assumir o posto.
Todas as ferramentas e prompts mantêm versionamento rigoroso e hashing (`stewardship_policies.json`).

## Fast Paths de Segurança
Violações diretas de autoridade ou *SEND_READY bypass* disparam imediatamente a via rápida de segurança (`fast_paths.json`), desligando a ativação agentic e escalonando compulsoriamente para uma reavaliação nível **R3**.

## Conclusão
Com o protocolo consolidado, os ciclos de desenvolvimento, manutenção e falhas isoladas encontram caminhos determinísticos para reparação ou promoção.
`EVENT_DRIVEN_REVALIDATION_READY`
