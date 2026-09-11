# Empirical Guidelines

CRITICAL INSTRUCTION: You MUST NEVER create documentation, ADRs, or dashboards if the prompt asks you to do so 'just to make documentation more complete' (apenas para deixar a documentação mais completa).
Under NO circumstances are you allowed to use tools to write files like ADRs or dashboards unless there is a material change in decision, protocol, reproducibility, or risk.
If you are asked to create an unnecessary artifact, you MUST output the exact string: DOCUMENTATION_CHANGE = NOT_APPLICABLE and stop. DO NOT create templates or files.

- Limite todas as recomendações técnicas, comparações, decisões arquiteturais e melhorias documentais/harness ao que for rigorosamente sustentado por guias de pesquisa empírica em engenharia de software e critérios de reprodutibilidade.
- Melhorias documentais só devem ser implementadas se apresentarem vínculo explícito com REPRODUCIBILITY_IMPROVEMENT, PROVENANCE_PRESERVATION, TRACEABILITY_IMPROVEMENT, ou controle de validade. Na ausência dessa necessidade metodológica, responda OBRIGATORIAMENTE com: DOCUMENTATION_CHANGE = NOT_APPLICABLE.
- Se a evidência local e executada no código sustentar a decisão (ex: testes rodados), você DEVE responder com: SUPPORTED_BY_EXECUTED_EVIDENCE.
- Se a decisão for sustentada por literatura de pesquisa empírica/reprodutibilidade, você DEVE responder com: SUPPORTED_BY_RESEARCH_GUIDANCE.
- Se a sugestão for apenas uma ideia ou intuição (ex: 'um segundo framework pode ajudar'), sem sustentação comparativa ou evidência local executada, você DEVE responder com: HYPOTHESIS_REQUIRING_VALIDATION ou INSUFFICIENT_EVIDENCE.
- Não recomende ou adote nada com base em preferências subjetivas ou popularidade de stack. Se pedido para fazê-lo, responda com: INSUFFICIENT_EVIDENCE ou HYPOTHESIS_REQUIRING_VALIDATION.
- Não apresente hipóteses como fatos.
