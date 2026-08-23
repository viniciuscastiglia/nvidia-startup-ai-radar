# O que eu preciso entender de verdade

> Escrito em 23/08/2026, depois de uma revisão da sessão 01.
> **Este arquivo não é sobre LangGraph.** É sobre os conceitos de IA que sustentam os
> 60 pontos do núcleo e os 7 minutos do vídeo.

## O erro de calibragem que gerou este arquivo

A primeira lista de estudo que saiu desta sessão era sobre internals do LangGraph:
super-steps, Pregel, propagação de config em subgrafo. Estava errada de prioridade, e o
motivo está no próprio barema:

**Não existe critério de arguição.** Nenhuma das 7 linhas dá ponto por defender bem uma
decisão. A defesa aparece uma vez só, como **eliminatório nº 4** — o que a torna *pass/fail*,
não algo a maximizar. O teto dela é "explicar as decisões de arquitetura do próprio projeto".

Onde entendimento **vira ponto** é no **vídeo (peso 20)**: sete minutos explicando arquitetura
dos agentes e sistema RAG. Se você não souber dizer o que reranking resolve, o vídeo fica raso
— e aí é perda de nota real, não risco hipotético.

Então a ordem é: **conceito de IA primeiro, decisão própria segundo, framework por último.**

## As três camadas

| Camada | O que é | Vale o quê | Onde já está |
|---|---|---|---|
| **1. Conceitos de IA** | embedding, busca híbrida, reranking, agente, alucinação | critérios 1-3 (60) + vídeo (20) | **este arquivo** |
| **2. Suas decisões** | por que *você* escolheu cada coisa | eliminatório nº 4 | `decisoes.md`, 24 entradas |
| **3. Internals do framework** | super-steps, checkpointer, Send | nada direto; seguro + nível 4 | fim deste arquivo |

Camada 2 você **já tem escrita**. Não é estudo novo — é saber contar sem ler.

---

# Camada 1 — os 10 conceitos

Formato de cada um: o que é · por que o *seu* projeto precisa · a pergunta que vem ·
o que estudar · como saber que você entendeu.

Os quatro marcados **[ESSENCIAL]** são inegociáveis. Se só houver 3 horas, são esses.

---

## 1. Embedding e espaço vetorial **[ESSENCIAL]**

**O que é.** Um modelo que transforma texto em um vetor de N números, treinado para que textos
com significado parecido caiam perto no espaço. "Perto" = similaridade de cosseno alta. É o que
permite buscar por *sentido* em vez de por *palavra*.

**Por que o seu projeto precisa.** A base NVIDIA está em inglês e os documentos das startups em
português. Busca por palavra não atravessa idioma — "inferência barata" não casa com
"cost-efficient inference". Embedding multilíngue casa, porque os dois caem no mesmo lugar do
espaço. Foi exatamente isso que o seu smoke test mediu (D-005): 0.4280 para o par relevante
crosslingual contra 0.0049 para o irrelevante.

**A pergunta que vem.** *"Por que embedding e não busca por palavra-chave?"* e
*"o que significa esse número 1024?"*

**O que estudar.**
- O conceito base: procure por **"Sentence-BERT: Sentence Embeddings using Siamese
  BERT-Networks"** (Reimers & Gurevych, 2019). Não precisa ler inteiro — a introdução e a
  figura da arquitetura siamesa entregam a ideia.
- Similaridade de cosseno: por que cosseno e não distância euclidiana (resposta curta: o que
  importa é a *direção* do vetor, não o comprimento).
- Matryoshka: procure por **"Matryoshka Representation Learning"** (Kusupati et al., 2022). É a
  técnica que faz o mesmo modelo devolver 384, 768 ou 1024 dimensões — a base de D-014.

**Como saber que entendeu.** Você consegue explicar, sem jargão, por que truncar de 2048 para
1024 dimensões perde pouca qualidade — e por que isso não seria verdade num embedding comum.

---

## 2. Busca vetorial e o índice HNSW

**O que é.** Comparar a consulta com *todos* os vetores da base é exato mas caro (O(n)). Índices
de vizinhos aproximados (ANN) trocam um pouco de exatidão por muita velocidade. HNSW é o mais
usado: um grafo em camadas onde a busca "desce" de saltos longos para saltos curtos.

**Por que o seu projeto precisa.** É a razão de D-014 existir. O pgvector **recusa índice HNSW
acima de 2000 dimensões** no tipo `vector` — você verificou isso no psql. Foi essa restrição,
cruzada com a necessidade de crosslingual, que eliminou dois dos três modelos candidatos.

**A pergunta que vem.** *"Sua base tem poucas centenas de chunks. Você precisava de HNSW?"*
(Resposta honesta: não, e é bom saber disso — a decisão foi por dimensão, não por escala.)

**O que estudar.** Procure pelo paper **"Efficient and robust approximate nearest neighbor
search using Hierarchical Navigable Small World graphs"** (Malkov & Yashunin). Leia a figura da
estrutura em camadas e a intuição de skip list. Ignore a matemática.

**Como saber que entendeu.** Você consegue dizer o que se **perde** com ANN (recall < 100%) e
por que isso é aceitável num RAG mas não num banco financeiro.

---

## 3. BM25 e por que busca híbrida **[ESSENCIAL]**

**O que é.** BM25 é ranqueamento **lexical**: pontua um documento por quantas vezes os termos
da consulta aparecem, com dois ajustes que importam — *saturação* (a 10ª ocorrência de "NIM"
vale menos que a 2ª) e *normalização por comprimento* (documento longo não ganha só por ser
longo). Busca híbrida = combinar o score denso (embedding) com o lexical.

**Por que o seu projeto precisa.** Duas razões e você já registrou as duas em D-016.
(a) Embedding é ruim com **nome próprio raro**: "TensorRT-LLM" e "Triton Inference Server" são
tokens que o denso borra e o léxico acerta na hora. (b) `ts_rank_cd` do Postgres **não é BM25** —
é cobertura de termos, sem saturação nem normalização. Chamar aquilo de BM25 no vídeo seria
impreciso, e é o tipo de coisa que um avaliador pergunta.

**A pergunta que vem.** *"Se o embedding é semântico e melhor, por que ainda usar busca por
palavra?"* — e o contra-golpe: *"você tem uma base em inglês e consulta em português. O BM25
serve para quê aí?"* (Pense antes: a resposta está no peso configurável que a `sessao-02.md`
já exige.)

**O que estudar.**
- **Introduction to Information Retrieval** (Manning, Raghavan & Schütze) — livro gratuito da
  Stanford em `nlp.stanford.edu/IR-book`. Capítulo 11 cobre o modelo probabilístico e BM25.
  Leia só a seção do BM25 e olhe o papel de `k1` e `b`.
- Fusão de rankings: procure por **Reciprocal Rank Fusion (RRF)**. É a alternativa a somar
  scores normalizados, e é o que o Qdrant faz nativo — ou seja, é a alternativa descartada de
  D-016 e você vai precisar dela como resposta.

**Como saber que entendeu.** Você consegue dar um exemplo concreto, tirado da *sua* base NVIDIA,
onde o denso acha e o léxico não — e um onde é o contrário.

---

## 4. Reranking: bi-encoder vs cross-encoder **[ESSENCIAL]**

**O que é.** Na busca, consulta e documento são embedados **separadamente** (bi-encoder) — por
isso dá para pré-computar a base inteira, e por isso é rápido. Um cross-encoder lê **os dois
juntos**, no mesmo forward pass, e devolve um score de relevância. É muito mais preciso e
inviável de rodar na base toda. Daí o padrão: recupere 50 barato, reordene 50 caro, use 5.

**Por que o seu projeto precisa.** É metade do critério 2 ("RAG **com reranking**"). E é onde a
sua D-015 tem um argumento que quase ninguém tem: você **mediu** o text-only contra o VL e o
text-only separou por margem 12.94 contra 3.24. Escolher o mais novo seria decidir por recência;
você decidiu por adequação ao corpus.

**A pergunta que vem.** *"O embedding já ordenou por similaridade. O que o reranker acrescenta?"*
Se você souber responder isso com a distinção bi/cross-encoder, essa resposta sozinha já
demonstra domínio do critério 2.

**O que estudar.** A documentação do **Sentence-Transformers**, páginas *Cross-Encoders* e
*Retrieve & Re-Rank* (`sbert.net`). São curtas, têm o diagrama exato dessa distinção, e é a
melhor meia hora de estudo desta lista inteira.

**Como saber que entendeu.** Você consegue explicar por que não dá simplesmente para usar o
cross-encoder como buscador e pular o embedding.

---

## 5. Chunking

**O que é.** Quebrar documento longo em pedaços que caibam no embedding e que sejam a unidade
certa de recuperação. Estratégias: tamanho fixo, fixo com sobreposição, por estrutura
(título/seção), ou semântico (quebra onde o assunto muda).

**Por que o seu projeto precisa.** É o passo 2 da `sessao-02.md` e a decisão ainda está aberta.
O trade-off é direto: chunk grande traz contexto mas dilui o embedding (o vetor vira a média de
vários assuntos); chunk pequeno é preciso mas chega no LLM sem contexto suficiente para citar.

**A pergunta que vem.** *"Como você escolheu o tamanho do chunk?"* — e a única resposta ruim é
"512 porque é o padrão".

**O que estudar.** Menos teoria, mais medição: o harness do passo 9 permite comparar duas
estratégias por recall@k. **Essa é a resposta forte** — "medi as duas". Para vocabulário, procure
por *chunking strategies for RAG*; para a variante semântica, por *semantic chunking* (quebra por
queda de similaridade entre sentenças vizinhas).

**Como saber que entendeu.** Você consegue nomear o que se perde nos dois extremos, e dizer qual
estratégia a **documentação NVIDIA** pede especificamente (dica: ela é fortemente estruturada em
títulos e seções — isso é uma informação, não um detalhe).

---

## 6. Avaliação de RAG — recall@k **[ESSENCIAL]**

**O que é.** Medir a recuperação separada da geração. `recall@k` = das perguntas do conjunto de
teste, em quantas o chunk certo apareceu entre os k primeiros. Sem isso, "melhorei o RAG" é
opinião.

**Por que o seu projeto precisa.** É o **passo 9** do pipeline que o TAPI pede e que a
`sessao-02.md` identifica como *"o que mais separa nível 2 de nível 4 no critério 2"*. E é o que
converte D-014 de argumento ("1024 por causa do HNSW") em medição ("comparei 384, 768 e 1024").

**A pergunta que vem.** *"Como você sabe que o reranking melhorou alguma coisa?"* Sem harness, a
resposta é "parece melhor". Com harness, é um número e um gráfico — e isso vai para o vídeo.

**O que estudar.** Precision, recall e a diferença entre `recall@k` e `MRR` (Mean Reciprocal
Rank — premia ter a resposta na *primeira* posição, não só entre as k). O capítulo 8 do livro da
Stanford cobre avaliação em IR. Vale olhar também o vocabulário do **RAGAS** (framework de
avaliação de RAG) mesmo sem usar a biblioteca — ele nomeia bem as métricas de *faithfulness* e
*context precision*.

**Como saber que entendeu.** Você consegue montar 15 perguntas sobre a base NVIDIA com a resposta
certa anotada, e explicar por que 15 perguntas suas valem mais que um benchmark público aqui.

---

## 7. RAG, e por que não colocar tudo no prompt

**O que é.** Recuperar trechos relevantes de uma base e injetá-los no contexto do LLM antes de
ele responder. O paper original é **"Retrieval-Augmented Generation for Knowledge-Intensive NLP
Tasks"** (Lewis et al., 2020).

**Por que o seu projeto precisa.** Óbvio na superfície (é o critério 2), mas a pergunta afiada é
a segunda: *"contexto de LLM hoje tem 128k tokens. Por que não jogar a documentação NVIDIA
inteira no prompt?"* Três respostas, e você precisa das três: **custo** (você paga por token em
toda chamada, e o pipeline roda N vezes por consulta), **precisão** (modelos degradam com
contexto longo — procure por *lost in the middle*), e **rastreabilidade** (com RAG você sabe qual
trecho sustentou a resposta; com o dump inteiro, não sabe).

**O que estudar.** O paper original (só o abstract e a figura 1) + procure por **"Lost in the
Middle: How Language Models Use Long Contexts"** (Liu et al., 2023). O segundo é o que dá a
resposta não-óbvia.

**Como saber que entendeu.** A terceira razão — rastreabilidade — é a que amarra com D-009 e
com o requisito que o TAPI grifa duas vezes. Se você chegar nela sozinho, entendeu.

---

## 8. Agente, chain e workflow — e por que multi-agente **[o coração do critério 1]**

**O que é.** *Chain* = sequência fixa de chamadas. *Workflow* = fluxo com ramificação, mas
decidido por código. *Agente* = o LLM decide o próximo passo. A maior parte dos "sistemas
multi-agente" reais é workflow, e **isso não é demérito** — é engenharia.

**Por que o seu projeto precisa.** É a pergunta nº 1 do critério 1: *"por que 8 agentes e não um
prompt grande?"* Suas respostas reais, que já estão no código:
- **Responsabilidade única por prompt.** Um prompt que extrai, classifica, valida e recomenda faz
  as quatro coisas pior. Extração quer literalidade; recomendação quer inferência.
- **Ponto de validação entre etapas.** O Evidence Validator só existe como agente separado
  porque julgar a própria evidência no mesmo passo em que se produz a conclusão não funciona.
- **Falha isolada.** D-024: uma etapa cai, as anteriores sobrevivem.
- **Paralelismo por startup.** D-007: com lote, o prompt cresce com N e a extração degrada.

**Seja honesto sobre a taxonomia.** O seu grafo é um **workflow determinístico**, não um sistema
de agentes autônomos — o LLM não escolhe o próximo nó. Dizer isso com clareza é mais forte que
chamar de agente e ser corrigido.

**O que estudar.** O post **"Building Effective Agents"** da Anthropic — é a melhor taxonomia
curta de workflow vs agente que existe, e cobre os padrões que você usou (*routing*,
*parallelization*, *orchestrator-workers*). Depois, a página *Agent architectures* nos conceitos
do LangGraph.

**Como saber que entendeu.** Você consegue nomear qual padrão do post cada parte do seu grafo
implementa — e dizer qual parte do sistema **não** precisava de LLM (o Retriever; é SQL).

---

## 9. Alucinação, grounding e rastreabilidade **[é o seu ponto mais forte]**

**O que é.** Um LLM gera o texto mais plausível, não o mais verdadeiro; não há nada na
arquitetura que separe as duas coisas. *Grounding* é obrigar toda afirmação a apontar para uma
fonte recuperada. É mitigação, não cura.

**Por que o seu projeto precisa.** Você já resolveu isso melhor que a média e provavelmente não
percebeu o tamanho:
- **D-009** — `Afirmacao` não existe sem `list[Evidencia]`, e `Evidencia` guarda o **trecho
  literal**, não só o id. Rastreabilidade virou propriedade do *tipo*: deixar de citar levanta
  erro de validação, não passa despercebido.
- **D-021** — campo estruturado sem fonte literal vira `null`. O argumento é assimétrico e vale
  decorar: **`null` dispara comportamento correto, valor errado não dispara nada.**
- **D-010** — o Validator anota e rebaixa, nunca deleta. Ausência de sinal ≠ sinal negativo.

**A pergunta que vem.** *"Como você garante que o sistema não inventou isso?"* A resposta é abrir
`state.py` e mostrar que o tipo não permite.

**O que estudar.** Pouco. Procure por *grounding* e *faithfulness* em RAG para ter o vocabulário
em inglês. O trabalho conceitual aqui você já fez — o estudo é **saber contar**.

**Como saber que entendeu.** Você conta a história da Laura (`tamanho_time = 80` que veio de
*"pretendia expandir de 65 para 80 até o final de 2021"*) em 30 segundos, e explica por que
zerar foi melhor que manter com um flag de confiança. **Isso é material de vídeo.**

---

## 10. Saída estruturada e validação

**O que é.** Forçar o LLM a devolver JSON conforme um schema, em vez de texto livre. Na prática:
o schema vai no prompt e/ou o modelo é restrito na decodificação, e a resposta é validada.

**Por que o seu projeto precisa.** É o que faz D-008 e D-011 funcionarem. `ClasseStartup` é um
`Literal` fechado: o classificador devolve exatamente `AI-native | AI-enabled | non-AI` ou
levanta `ValidationError`. `Dor` é enum fechada de 8 valores, e é isso que transforma a
recomendação numa **junção auditável** ("esta dor observada casa com esta tecnologia pela tabela
de `contexto/03` §4") em vez de "o LLM achou que combinava".

**A pegadinha que vem.** *"E se o modelo devolver algo inválido — o retry resolve?"*
**Não.** A chamada é determinística o bastante: repetir o mesmo prompt tende a dar o mesmo erro.
O que resolve é **reprompt com a mensagem de validação de volta ao modelo**. Está registrado na
nota de D-024 e é trabalho da M4.

**O que estudar.** A página *Structured outputs* da documentação da Anthropic ou da OpenAI (o
conceito é o mesmo) e o `with_structured_output` do LangChain. Depois, procure por
*constrained decoding* para saber como funciona por baixo.

**Como saber que entendeu.** Você explica por que `Literal` fechado no Pydantic é uma decisão de
**arquitetura de IA**, não de tipagem.

---

# Camada 3 — o LangGraph, quando sobrar tempo

Não estude antes de gravar o vídeo. Vale como seguro contra pergunta de aprofundamento.

O conceito único que destrava o resto: **LangGraph não executa nó a nó, executa em
super-steps.** Cada passo roda em paralelo todas as tarefas agendadas; quando todas terminam, as
escritas são aplicadas aos canais de uma vez, passando pelos *reducers*. Canal sem reducer é
sobrescrita. Duas branches escrevendo no mesmo canal sem reducer no mesmo passo dá
`InvalidUpdateError` — não "a última ganha".

Com isso, estas quatro respondem sozinhas:
1. Onde acontece o fan-in — no reducer `operator.add` de `analises`, na aplicação das escritas.
2. Por que `defer=True` não salvou o caso de zero startups — ele **atrasa** tarefa agendada, não
   agenda o que não foi (D-023).
3. Por que rodar duas vezes duplicava — `thread_id` é identidade de conversa; retomar restaura
   os canais e o reducer soma (D-022).
4. O que o subgrafo perde por ser invocado à mão em vez de ser nó — checkpoint com granularidade
   de startup inteira, e `interrupt()` indisponível lá dentro. **Isso ainda está em aberto**, e
   importa porque "intervenção humana" é uma das justificativas que o TAPI dá para exigir
   LangGraph.

*Onde:* documentação do LangGraph, conceitos **Low Level / Graph API**, **Persistence** e
**Subgraphs**.
*Melhor experimento:* `GRAFO.get_state(config)` e `list(GRAFO.get_state_history(config))` depois
de um run. Ver o histórico com os próprios olhos vale mais que qualquer texto.

---

# Como usar este arquivo

**Não leia tudo agora.** Leia o conceito antes da sessão que o implementa — é aí que ele gruda.

| Antes de | Leia |
|---|---|
| sessão 02 (RAG, passos 1-5) | 1, 5, 7 |
| sessão 03 (busca híbrida + rerank) | 2, 3, 4 |
| sessão 04 (harness) | 6 |
| sessões dos agentes (M4) | 8, 10 |
| gravar o vídeo | 9 + reler `decisoes.md` inteiro |

**Implementar já é estudar.** Os conceitos 1-6 *são* a sessão 02. Você não precisa estudá-los
antes e depois — precisa ler 30 minutos antes de cada bloco e implementar com o conceito fresco.
