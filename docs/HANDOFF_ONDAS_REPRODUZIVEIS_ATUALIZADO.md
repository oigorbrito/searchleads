# HANDOFF OPERACIONAL — ONDAS DE FECHAMENTO REPRODUTÍVEIS

## 0. PRINCÍPIO METODOLÓGICO OBRIGATÓRIO

A partir de agora, limite recomendações técnicas, comparações, conclusões de superioridade, thresholds, decisões arquiteturais **e melhorias documentais/harness** ao que puder ser sustentado por:

- guias de pesquisa empírica em engenharia de software;
- critérios de artifact evaluation e reprodutibilidade aplicáveis à engenharia de software;
- desenho experimental reproduzível;
- evidência executada no repositório ou em ambiente explicitamente identificado;
- critérios de validade, rastreabilidade, proveniência e reprodutibilidade;
- distinção rigorosa entre observação, hipótese, inferência e conclusão.

Melhorias documentais não constituem exceção ao requisito de evidência. Não recomendar novos relatórios, matrizes, ADRs, campos, logs, schemas, checklists ou artefatos apenas por completude aparente, preferência de organização ou conveniência narrativa.

Uma melhoria documental só é admissível quando houver vínculo explícito com pelo menos um destes efeitos verificáveis:

```text
REPRODUCIBILITY_IMPROVEMENT
TRACEABILITY_IMPROVEMENT
VALIDITY_THREAT_CONTROL
PROVENANCE_PRESERVATION
PROTOCOL_DISAMBIGUATION
DECISION_RELEVANT_EVIDENCE
EXECUTABLE_POLICY_PARITY
```

Na ausência desse vínculo:

`DOCUMENTATION_CHANGE = NOT_APPLICABLE`

Não recomendar tecnologias, frameworks, arquiteturas ou parâmetros apenas por preferência, popularidade ou expectativa subjetiva.

Quando a evidência for insuficiente, use explicitamente:

`EVIDENCE_INSUFFICIENT`

Quando houver apenas hipótese:

`HYPOTHESIS_NOT_YET_TESTED`

Quando houver resultado limitado a determinado corpus, modelo, ambiente ou protocolo, declarar essa limitação e não generalizar.

Ausência de execução nunca é evidência de sucesso.

---

# 1. MODO DE EXECUÇÃO

Trabalhe em **ONDAS DE FECHAMENTO completas**.

Uma onda contém vários blocos técnicos encadeados e deve continuar autonomamente até que todo trabalho executável daquela onda esteja concluído.

Não pare entre blocos para pedir autorização quando a próxima ação for uma continuação técnica direta, segura, reversível e coerente com o objetivo da onda.

Uma onda só termina quando:

A. todo trabalho executável estiver fechado;

ou

B. todo trabalho restante depender exclusivamente de blockers externos já registrados.

---

# 2. REGRA DE BLOCKERS

NÃO encerre uma onda porque um recurso externo falhou.

Exemplos:

- GitHub;
- GitHub Actions;
- CI remoto;
- MCP;
- runtime externo;
- serviço de terceiros;
- credencial ausente;
- endpoint indisponível;
- ferramenta não instalada;
- dependência externa inacessível;
- runner remoto indisponível.

Esses eventos devem ser tratados como:

`BLOCKED`

e registrados no `BLOCKER_REGISTER`.

Depois do registro, continue imediatamente todo trabalho independente do blocker.

Nunca converta:

`BLOCKED → FAIL`

sem evidência de falha do sistema testado.

Nunca converta:

`BLOCKED → PASS`

sem execução.

---

# 3. BLOCKER REGISTER

Para cada blocker registre:

```text
blocker_id
type
blocked_operation
observed_evidence
impact
work_that_can_continue
objective_unblock_condition

```

Formato final preferencial:

| blocker\_idtypeblocked\_operationobserved\_evidenceimpactwork\_that\_can\_continueunblock\_condition |
| ---------------------------------------------------------------------------------------------------- |

Um blocker não invalida evidência já obtida nos demais blocos.

---

# 4. STATUS PERMITIDOS

Para requisitos, experimentos e testes, usar somente:

```text
PASS
FAIL
BLOCKED
NOT_TESTED
NOT_APPLICABLE

```

Regras:

`PASS`
\= execução realizada e critério objetivo satisfeito.

`FAIL`
\= execução realizada e critério objetivo violado.

`BLOCKED`
\= execução impedida por condição externa ou ambiental identificada.

`NOT_TESTED`
\= não executado.

`NOT_APPLICABLE`
\= requisito justificadamente fora do escopo.

Nunca inferir PASS a partir de ausência de erro aparente.

---

# 5. ESTRUTURA OBRIGATÓRIA DA ONDA

## BLOCO 1 — BASELINE

Antes de modificar qualquer coisa:

- confirmar branch;
- confirmar HEAD;
- confirmar worktree;
- registrar versões relevantes;
- registrar configuração relevante;
- confirmar estado inicial dos testes relacionados.

Registrar quando aplicável:

```text
branch
git_commit
git_status
runtime
python_version
dependency_versions
dataset_version
schema_version
configuration

```

O baseline deve ser executado antes da implementação sempre que tecnicamente possível.

---

## BLOCO 2 — DIAGNÓSTICO

Identificar gaps objetivos antes de alterar código.

Reproduzir falhas quando existirem.

Separar explicitamente:

```text
REGRESSION
PREEXISTING_FAILURE
ENVIRONMENT_FAILURE
CORPUS_OR_ORACLE_GAP
TEST_ISOLATION_FAILURE
POLICY_DRIFT
EXTERNAL_BLOCKER
UNKNOWN

```

Quando causalidade entre mudança e falha for relevante, comparar:

```text
HEAD
vs
parent/base revision

```

Não atribuir causalidade somente por proximidade temporal.

---

## BLOCO 3 — HIPÓTESE

Quando houver investigação causal, declarar antes da intervenção:

```text
HYPOTHESIS
EXPECTED_OBSERVATION_IF_TRUE
EXPECTED_OBSERVATION_IF_FALSE

```

Evitar formular hipótese depois de observar o resultado.

Quando possível, alterar uma variável relevante por vez.

---

## BLOCO 4 — IMPLEMENTAÇÃO

Para cada gap comprovado:

- fazer a menor alteração capaz de fechar o requisito;
- preservar contratos existentes;
- evitar abstrações sem necessidade demonstrada;
- não introduzir frameworks ou componentes por preferência;
- não ampliar autoridade ou side effects sem requisito comprovado.

Princípio:

`MINIMUM_CHANGE_SUFFICIENT_TO_CLOSE_THE_REQUIREMENT`

Se uma mudança maior parecer desejável, registre-a separadamente como hipótese futura.

---

## BLOCO 5 — TESTES DIRETAMENTE ASSOCIADOS

Executar primeiro os testes com maior relação causal com a mudança.

Priorizar:

```text
focal test
→ related module tests
→ contract/invariant tests
→ broader regression

```

Selecionar testes pelo risco da mudança.

Não usar percentual de coverage como critério isolado de aceitação.

Coverage pode ser evidência auxiliar, nunca substituto de testes semanticamente relevantes.

---

## BLOCO 6 — REGRESSÃO

Executar, conforme aplicável:

```text
teste focal
módulo relacionado
fast gate
contract/invariant tests
suíte canônica

```

Quando concorrência puder contaminar:

- filesystem;
- banco;
- portas;
- caches;
- estado compartilhado;
- rate limits;

executar testes sequencialmente.

Não usar paralelismo se ele reduzir a qualidade da evidência.

---

# 6. REPRODUTIBILIDADE

Para toda execução relevante, registrar quando aplicável:

```text
git_commit
branch
runtime
python_version
dependency_versions
dataset_version
dataset_hash
query_set_version
schema_version
prompt_version
prompt_hash
tool_contract_hash
model_id
provider
seed
temperature
configuration
commands
test_count
duration
exit_code
stdout
stderr
raw_results
protocol_deviations
observed_side_effects
timestamp

```

Preservar resultados brutos sempre que economicamente razoável.

Relatórios derivados não substituem raw data.

---

# 7. CORPUS, GOLD SET E ORACLES

Quando houver benchmark ou experimento:

- congelar corpus antes dos tratamentos;
- versionar dataset;
- calcular hash;
- preservar gold set;
- registrar proveniência dos casos;
- não modificar expected outcomes após observar resultados.

Mudança de corpus exige nova versão:

```text
dataset_vN → dataset_vN+1

```

Não sobrescrever evidência histórica.

Não usar output de LLM como gold oracle sem validação independente adequada.

---

# 8. COMPARAÇÕES E BAKE-OFFS

Não declarar tecnologia/framework A superior a B sem comparação controlada suficiente.

Comparações devem, quando possível, manter constantes:

```text
corpus
scorer
model
prompt
tool set
budget
timeouts
retry policy
hardware/environment
authority boundaries

```

Quando alguma variável não puder ser mantida constante, registrar:

`CONFOUND`

e limitar a conclusão.

Framework bloqueado na instalação não é framework derrotado.

Resultado permitido:

```text
NOT_FUNCTIONALLY_EVALUATED

```

---

# 9. ESTATÍSTICA E INTERPRETAÇÃO

Não tratar repetições do mesmo caso como casos independentes.

Preservar estrutura hierárquica:

```text
case
└── repeated runs

```

Preferir análise descritiva quando o número de casos independentes não justificar inferência robusta.

Não produzir p-value apenas para dar aparência de rigor.

Não transformar diferença numérica pequena em superioridade sem suporte.

Usar formulações como:

```text
OBSERVED_IN_THIS_CORPUS
SUPPORTED_FOR_FURTHER_EVALUATION
NO_MEASURABLE_BENEFIT
INCONCLUSIVE

```

---

# 10. CRITÉRIOS DE SEGURANÇA E INVARIANTES

Constraints críticos não entram em score médio.

Exemplos:

```text
false_merge = 0
critical_authority_violation = 0
evidence_integrity_violation = 0
SEND_READY_bypass = 0
unrecoverable_state_corruption = 0

```

Uma melhoria em recall, latência ou custo não compensa regressão crítica.

---

# 11. EFEITOS COLATERAIS

Depois dos testes:

```text
git status --short
git diff --stat
git diff

```

Identificar:

- mudanças deliberadas;
- artefatos de teste;
- caches;
- temporários;
- arquivos produzidos automaticamente;
- alterações não intencionais.

Preservar evidência necessária.

Restaurar efeitos não intencionais.

Nunca confundir artefato produzido pelo teste com mudança deliberada de implementação.

---

# 12. DOCUMENTAÇÃO

Atualizar documentação somente quando necessário para:

- reproduzir execução;
- registrar protocolo experimental;
- registrar configuração materialmente relevante;
- registrar thresholds acompanhados de origem e critério de decisão;
- registrar threats to validity;
- preservar proveniência de dados, corpus, oracles e resultados;
- documentar contracts/invariants cuja execução ou interpretação dependa da especificação;
- manter paridade entre política executável e descrição metodológica;
- permitir verificação independente de uma conclusão ou decisão.

Toda sugestão de melhoria documental deve declarar sua base de sustentação em uma destas classes:

```text
SUPPORTED_BY_EXECUTED_EVIDENCE
SUPPORTED_BY_RESEARCH_GUIDANCE
HYPOTHESIS_REQUIRING_VALIDATION
INSUFFICIENT_EVIDENCE
```

Para `SUPPORTED_BY_RESEARCH_GUIDANCE`, a sustentação deve vir prioritariamente de:

- guias de pesquisa empírica em engenharia de software;
- critérios formais de artifact evaluation/reproducibility;
- orientação metodológica primária com critérios verificáveis de validade, replicação ou rastreabilidade.

Documentação primária de uma ferramenta pode sustentar **como registrar ou reproduzir** um mecanismo específico, mas não deve, isoladamente, fundamentar alegações metodológicas de superioridade, validade experimental ou necessidade de um novo artefato documental.

Antes de criar ou recomendar qualquer novo artefato, responder:

```text
WHAT_DECISION_OR_REPRODUCIBILITY_GAP_DOES_THIS_CLOSE?
WHAT_EVIDENCE_REQUIRES_THIS_ARTIFACT?
WOULD_OMITTING_IT_PREVENT_REPLICATION_AUDIT_OR_VALID_INTERPRETATION?
```

Se nenhuma resposta objetiva existir:

```text
DOCUMENTATION_CHANGE = NOT_APPLICABLE
```

Evitar documentação ornamental, duplicada ou sem efeito sobre decisão, replicação, auditoria ou controle de validade.

Não recomendar por padrão:

- novos ADRs sem decisão arquitetural nova;
- novas matrizes que apenas reformatem evidência existente;
- dashboards sem variável decisória definida;
- campos de metadata não usados na reprodução ou auditoria;
- relatórios derivados quando raw evidence já fecha o requisito;
- checklists sem relação com risco, validade ou reprodutibilidade;
- documentação de hipótese futura como se fosse requisito atual.

Toda conclusão deve distinguir:

```text
OBSERVED
INFERRED
ASSUMED
NOT_TESTED

```

---

# 13. THREATS TO VALIDITY

Quando houver experimento relevante, registrar pelo menos:

```text
construct_validity
internal_validity
external_validity
conclusion_validity
reproducibility_limitations

```

Exemplos:

- corpus pequeno;
- único provider;
- único modelo;
- middleware diferente;
- ausência de tráfego operacional real;
- ambiente Windows específico;
- fixtures sintéticas;
- dependência externa bloqueada.

Não esconder limitações atrás de classificação PASS.

---

# 14. COMMIT

Quando um bloco de implementação estiver tecnicamente fechado:

1. revisar diff;
2. executar validação final relevante;
3. verificar ausência de efeitos não intencionais;
4. criar commit pequeno e coerente;
5. registrar commit SHA.

Não:

- reescrever histórico;
- misturar mudanças não relacionadas;
- incluir artifacts/caches por acidente.

Se commit não for apropriado ou possível:

registrar:

`COMMIT = NOT_APPLICABLE`

ou blocker correspondente.

---

# 15. REMOTO / CI

Se GitHub/CI estiver disponível:

- push;
- observar workflow;
- registrar run;
- registrar conclusão;
- registrar logs relevantes.

Se remoto estiver indisponível:

criar blocker.

Exemplo:

```text
blocker_id: BLK-CI-001
type: EXTERNAL_INFRASTRUCTURE
blocked_operation: GitHub Actions validation
observed_evidence: runner not allocated / remote unavailable
impact: remote CI evidence unavailable
work_that_can_continue: all local verification
unblock_condition: remote runner becomes available

```

Depois continuar a onda.

Regra:

`INFRASTRUCTURE_BLOCKED != TEST_FAILED`

---

# 16. PRÓXIMO BLOCO DA MESMA ONDA

Ao concluir um bloco:

1. procurar imediatamente o próximo gap objetivo associado ao objetivo da onda;
2. executá-lo se for seguro e independente;
3. registrar blocker apenas quando necessário;
4. continuar.

Não parar apenas porque um marco intermediário foi alcançado.

---

# 17. CONDIÇÃO DE FECHAMENTO

A onda só termina quando:

```text
ALL_EXECUTABLE_WORK_CLOSED

```

ou:

```text
ALL_REMAINING_WORK_DEPENDS_EXCLUSIVELY_ON_REGISTERED_BLOCKERS

```

Antes disso, não emitir fechamento.

---

# 18. FORMATO OBRIGATÓRIO DO FECHAMENTO

Ao final da onda, devolver somente:

```text
1. HEAD inicial
2. HEAD final
3. blocos concluídos
4. arquivos alterados
5. testes executados
6. resultados e exit codes
7. regressões encontradas
8. regressões corrigidas
9. evidência de reprodutibilidade
10. commits criados
11. pushes/CI observados
12. blocker register
13. itens ainda FAIL
14. itens ainda NOT_TESTED
15. próximo ponto objetivo recomendado

```

Não adicionar recomendações genéricas fora desse formato.

---

# 19. REGRAS PARA PROMPTS FUTUROS

Prompts de ondas devem ser otimizados para execução.

Cada bloco deve conter apenas:

```text
OBJETIVO
AÇÕES
EVIDÊNCIA ESPERADA
CLASSIFICAÇÃO POSSÍVEL
ARTEFATO, quando necessário

```

Evitar:

- repetição de princípios já globais;
- textos motivacionais;
- exemplos excessivos;
- instruções duplicadas;
- listas de artefatos sem necessidade metodológica;
- criação de documentação que não mude decisão, reprodutibilidade, rastreabilidade ou análise de validade;
- sugestões documentais sem classificação de evidência;
- artefatos propostos apenas para “completar” uma onda.

Preferir blocos curtos, verificáveis e com critério de saída objetivo.

---

# 20. REGRA DE RECOMENDAÇÃO TÉCNICA E DOCUMENTAL

Qualquer recomendação sobre:

- framework;
- arquitetura;
- modelo;
- provider;
- banco;
- biblioteca;
- estratégia de testes;
- threshold;
- performance;
- segurança;
- rollout;
- documentação metodológica;
- estrutura do harness;
- evidence packages;
- matrizes, ADRs, relatórios ou metadata adicionais;

deve cair em uma destas categorias:

```text
SUPPORTED_BY_EXECUTED_EVIDENCE
SUPPORTED_BY_RESEARCH_GUIDANCE
HYPOTHESIS_REQUIRING_VALIDATION
INSUFFICIENT_EVIDENCE

```

Nunca apresentar hipótese como fato.

Quando usar pesquisa externa para fundamentar uma recomendação metodológica ou documental, limitar a base principal a:

- guias de pesquisa empírica em engenharia de software;
- standards/critérios de artifact evaluation e reproducibility;
- estudos metodológicos com desenho e critérios explicitados;
- fontes primárias reproduzíveis relevantes ao mecanismo sob avaliação.

Documentação primária de ferramentas pode complementar detalhes operacionais, mas não substituir orientação metodológica quando a recomendação disser respeito a validade, desenho experimental, reprodutibilidade ou necessidade documental.

Não usar como fundamento de recomendação metodológica/documental:

- popularidade;
- benchmark de marketing;
- opinião comunitária;
- preferência estética;
- convenção sem efeito demonstrável sobre reprodução ou validade;
- “best practice” sem fonte metodológica ou evidência executada aplicável.

Quando nenhuma base admissível sustentar a sugestão:

`INSUFFICIENT_EVIDENCE`

e não recomendar a alteração.

---

# 21. REGRA DE AUTONOMIA

Não solicitar autorização entre blocos para:

- executar testes;
- investigar erro;
- criar artefato de evidência;
- aplicar correção mínima;
- validar regressão;
- registrar blocker;
- continuar tarefa independente.

Pedir intervenção humana apenas quando a ação exigir decisão não inferível com segurança, como:

- uso de credencial não autorizada;
- operação destrutiva;
- alteração irreversível;
- decisão comercial/legal;
- escolha entre objetivos conflitantes sem critério prévio.

---

# 22. REGRA FINAL

O objetivo de uma onda não é produzir atividade.

É produzir **evidência suficiente para fechar requisitos objetivos**, preservando:

```text
correctness
reproducibility
traceability
minimal change
explicit uncertainty
controlled side effects

```

Quando não houver evidência suficiente, a conclusão correta é:

`NOT_PROVEN`

e não uma recomendação por preferência.