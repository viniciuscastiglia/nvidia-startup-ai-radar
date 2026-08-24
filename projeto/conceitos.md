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
| **2. Suas decisões** | por que *você* escolheu cada coisa | eliminatório nº 4 | `decisoes.md`, 33 entradas |
| **3. Internals do framework** | super-steps, checkpointer, Send | nada direto; seguro + nível 4 | fim deste arquivo |

Camada 2 você **já tem escrita**. Não é estudo novo — é saber contar sem ler.

---

# Camada 1 — os 13 conceitos

Formato de cada um: o que é · por que o *seu* projeto precisa · a pergunta que vem ·
o que estudar · como saber que você entendeu.

Os seis marcados **[ESSENCIAL]** são inegociáveis. Se só houver 3 horas, são esses.

Os conceitos 11 e 12 foram acrescentados depois: eles são **domínio**, não técnica, e por isso
quase escaparam. São também as duas perguntas mais prováveis do processo inteiro.

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

**Por que o seu projeto precisa.** É o passo 3 do pipeline, e a decisão está **fechada em D-025**:
estrutural por seção, com fundir-pequenas e dividir-grandes, e o caminho da seção prefixado no
texto que é embedado. O trade-off é direto: chunk grande traz contexto mas dilui o embedding (o vetor vira a média de
vários assuntos); chunk pequeno é preciso mas chega no LLM sem contexto suficiente para citar.

**A pergunta que vem.** *"Como você escolheu o tamanho do chunk?"* — e a única resposta ruim é
"512 porque é o padrão".

**O que estudar.** Menos teoria, mais medição — e neste ponto **você já tem o número**: D-032
compara estrutural contra janela fixa no gabarito de 20 perguntas (`recall@3` de 100% contra 84%).
**Essa é a resposta forte** — "medi as duas". Leia D-025 e D-032 antes de qualquer teoria. Depois,
para vocabulário, procure
por *chunking strategies for RAG*; para a variante semântica, por *semantic chunking* (quebra por
queda de similaridade entre sentenças vizinhas).

**Como saber que entendeu.** Você consegue nomear o que se perde nos dois extremos, e explicar por
que a documentação NVIDIA **pede** a estratégia estrutural: medi que a página do NIM tem 51 seções
em 9.909 chars (~194 por seção) e o README do TensorRT-LLM tem 8 em 27.060 (~3.383). São formas
opostas, e é por isso que fundir e dividir são os dois caminhos principais — não casos de canto.

**Onde a banca aperta:** pergunta 1 da arguição, no fim deste arquivo.

---

## 6. Avaliação de RAG — recall@k **[ESSENCIAL]**

**O que é.** Medir a recuperação separada da geração. `recall@k` = das perguntas do conjunto de
teste, em quantas o chunk certo apareceu entre os k primeiros. Sem isso, "melhorei o RAG" é
opinião.

**Por que o seu projeto precisa.** É o **passo 9** do pipeline que o TAPI pede e que a
`sessao-02.md` identifica como *"o que mais separa nível 2 de nível 4 no critério 2"*. E é o que
converte D-014 de argumento ("1024 por causa do HNSW") em medição ("comparei 384, 768 e 1024").

**Ele já existe** desde a sessão 02, não da 04 — ver D-031 e `scripts/avaliar_rag.py`. Duas coisas
do desenho dele valem estudo próprio: a âncora é o **documento-fonte** e não o chunk (D-030), que é
o que faz a régua sobreviver a mudança de chunking; e o modo `--validar`, que confere a resposta
**contra o corpus** antes de medir qualquer coisa.

**A pergunta que vem.** *"Como você sabe que o reranking melhorou alguma coisa?"* Sem harness, a
resposta é "parece melhor". Com harness, é um número e um gráfico — e isso vai para o vídeo.

**O que estudar.** Precision, recall e a diferença entre `recall@k` e `MRR` (Mean Reciprocal
Rank — premia ter a resposta na *primeira* posição, não só entre as k). O capítulo 8 do livro da
Stanford cobre avaliação em IR. Vale olhar também o vocabulário do **RAGAS** (framework de
avaliação de RAG) mesmo sem usar a biblioteca — ele nomeia bem as métricas de *faithfulness* e
*context precision*.

**Como saber que entendeu.** Você consegue montar 15 perguntas sobre a base NVIDIA com a resposta
certa anotada, e explicar por que 15 perguntas suas valem mais que um benchmark público aqui.
E o passo seguinte, mais difícil: explicar em que condições o seu próprio `recall@3 = 100%`
**não** é evidência de qualidade.

**Onde a banca aperta:** perguntas 2 e 3 da arguição, no fim deste arquivo.

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

## 11. A stack NVIDIA — as tecnologias que você vai recomendar **[ESSENCIAL]**

**O que é.** As 16 tecnologias de `contexto/03` §1 e o programa Inception. É o "lado direito" do
motor de recomendação: o mapa dor → tecnologia de `contexto/03` §4 casa o que foi observado na
startup com o que a NVIDIA tem.

**Por que isto quase escapou desta lista.** Eu tratei `contexto/03` como documento de consulta.
Errado: **isto é um case da NVIDIA.** *"O que é o NIM e por que você recomendou ele para essa
startup, e não o Triton?"* é provavelmente a pergunta mais provável do processo inteiro, e é
constrangedora de errar. Consultar não serve — tem que estar na cabeça.

### A distinção que mais gera confusão

As três se sobrepõem e é fácil trocar uma pela outra:

| | O que é | A frase de uma linha |
|---|---|---|
| **TensorRT-LLM** | biblioteca de **otimização** de inferência | quantização FP8/FP4, speculative decoding (~3x), paged KV cache |
| **NIM** | **empacotamento**: container com modelo + engine otimizada + API padrão | "self-host sem reescrever código" — API OpenAI-compatible |
| **Triton** | camada de **serving** em produção | dynamic batching, vários modelos concorrentes, métricas Prometheus |

O NIM **embute** o TensorRT-LLM. Não são alternativas — são camadas. E a resposta de "qual
recomendar" vem da dor: custo/privacidade de quem depende de API externa → NIM; latência de quem
já roda modelo próprio → TensorRT-LLM; GPU subutilizada servindo vários modelos → Triton.

### O que saber de cor (5 + 1)

**NIM · TensorRT-LLM · Triton · NeMo (Guardrails e Evaluator) · RAPIDS (cuDF/cuML)** cobrem a
maioria das recomendações que o seu sistema vai emitir. Mais o **Inception**, que é o destino de
todo briefing.

As verticais — **MONAI**, **Parabricks**, **BioNeMo** (saúde), **Riva** (voz, e faz ASR em
português), **Morpheus** (fraude), **Isaac/Omniverse** (robótica) — são consulta por setor.
Saiba que existem e para que servem; não decore números.

**Inception**: grátis, sem equity, sem cohort. Requisitos: ≥1 developer empregado, incorporada,
site ativo, <10 anos, **não exige receita**. Exclui consultoria, cripto, cloud provider, revenda
e capital aberto. Isso já é código em `src/agents/briefing.py`.

### O detalhe que vira momento de vídeo

O NIM expõe **API OpenAI-compatible** — trocar o `base_url` basta. É exatamente o que a sua
**D-003** explora para falar com o build.nvidia.com por `langchain-openai` em vez do SDK da
NVIDIA. Ou seja: **o seu projeto é, ele mesmo, uma demonstração da tese do NIM.** Você não
precisa argumentar que migrar não exige mudar código — o seu `config.py` prova.

**As 5 regras do Recommendation Agent** (`contexto/03` §4) valem decorar, porque são a diferença
entre motor e template:
1. prioridade vem do **gap** entre os dois eixos, não do rótulo
2. complexidade tem que ser honesta — `cudf.pandas` é zero-code-change; migrar para Triton +
   TensorRT-LLM é projeto de semanas
3. sem evidência, não recomenda
4. não empilhar — 2 ou 3 tecnologias com próxima ação clara, não 8
5. o **estágio** muda a recomendação: pre-seed → Inception e créditos; Série A com carga real →
   NIM e TensorRT-LLM; Série B com cliente corporativo → AI Enterprise

**O que estudar.** `contexto/03` inteiro, uma vez, com atenção. Depois volte só na §4 (o mapa) e
na §2 (Inception) até conseguir recitar. Cada tecnologia tem URL oficial verificada na §5 — se
alguma ficar abstrata, abra a página.

**Como saber que entendeu.** Você pega uma das suas 3 startups da base, diz qual tecnologia
recomendaria, por qual dor observada, com que complexidade e qual a próxima ação — sem abrir o
arquivo.

---

## 12. A rubrica AI-native — a pergunta norteadora do case **[ESSENCIAL]**

**O que é.** A régua de `contexto/02` que separa `AI-native`, `AI-enabled` e `non-AI`. O TAPI
**não fornece** essa rubrica — você a construiu a partir de Sequoia, Emergence Capital e do
5-layer cake da NVIDIA. Isso é bom e ruim: é diferencial, e é 100% seu para defender.

**Por que o seu projeto precisa.** É a pergunta norteadora inteira: *"como a NVIDIA identifica
startups AI-native num contexto em que os grandes labs ameaçam quem só faz wrapper de LLM?"*
Se você hesitar em "o que é AI-native", o case inteiro balança.

### O eixo central: copilot vs autopilot

- **AI-enabled** fala como **copilot**: *"nossa plataforma permite que você..."* — IA é feature
  dentro de um produto que existiria sem ela. Depende de API externa, sem dado proprietário,
  delivery ainda humano escalando linearmente. É a categoria de risco do TAPI: substituível por
  funcionalidade nativa dos grandes labs.
- **AI-native** fala como **autopilot**: vende o **resultado**, não a ferramenta. Tem dado
  proprietário gerado pelo próprio trabalho (flywheel), otimização técnica própria
  (self-hosting, quantização, avaliação, guardrails), e margem que **melhora** com escala.
- **non-AI**: sem IA no caminho crítico da entrega de valor. Usar ChatGPT internamente não conta.

### A parte que quase ninguém faz: classificar ≠ qualificar

Ser AI-native **não** faz alguém bom prospect. A intensidade da recomendação vem do **gap** entre
dois eixos — classe × maturidade de stack:

- **AI-native + stack imatura = SWEET SPOT.** Carga de IA real e a dor prestes a bater.
- **AI-enabled + stack imatura** = prospect de evolução; a conversa é sair do wrapper.
- **AI-native + stack madura** = provavelmente já é membro do Inception.
- **non-AI** = fora do funil.

Isso está executável em `derivar_quadrante()` no `state.py`. É decisão de arquitetura, não
enfeite — e empurra o critério 3.

### A hierarquia de sinal por tipo de documento

A **vaga de emprego é o documento mais honesto da base** — sinal altíssimo. "ML Engineer",
"inference optimization", "CUDA", "TensorRT", "vLLM", "MLOps", "avaliação de modelos" = 
profundidade técnica real. Só "integrar a API da OpenAI" = wrapper. Blog é alto, site é
médio-alto (é onde o copilot/autopilot aparece na linguagem), notícia é média e serve para
**datar** a evidência, release é baixo.

Marketing mente; vaga técnica não mente, porque a empresa precisa que a pessoa certa se
candidate. **Essa frase é vídeo.**

**O que estudar.** `contexto/02` inteiro. Preste atenção especial na §4 (as três classes e o
modelo de dois eixos) e na §5 (sinais por tipo de documento). O conceito de **Mirage PMF** da
Emergence (§2) é o mais útil do arquivo e vale entender: crescimento que parece PMF mas é
curiosidade sobre IA.

**Como saber que entendeu.** Você classifica a **Axenya** em voz alta, com evidência, e explica
por que a heurística da sessão 01 a reprovou por engano (D-020: o site diz *"Integramos
consultoria, dados e operação clínica em uma única plataforma"* — ela não **é** consultoria, ela
**absorve** a função de consultoria num produto, que é justamente o wedge da Sequoia).

---

## 13. Prompt engineering para extração com evidência

**O que é.** A técnica de escrever a instrução que faz o LLM produzir exatamente a estrutura que
você precisa. Não é "pedir com jeitinho" — é decidir o que vai no prompt, em que ordem, com
quantos exemplos, e o que fazer quando a saída não valida.

**Por que o seu projeto precisa.** É o que separa a sessão 01 da M4. Hoje os nós são heurística
de palavra-chave; quando virarem LLM, o prompt é o agente. E os **três erros registrados em
D-020 são exatamente o que os prompts têm que resolver**:
1. a Axenya reprovada por casamento de substring ("consultoria")
2. todas as empresas acusando quase todas as 8 dores
3. a Doutor-AI classificada AI-enabled apesar de linguagem de autopilot pura

Note que D-020 diz que esses erros são o melhor material de "antes e depois" do vídeo. Para isso
funcionar, o "depois" precisa realmente ser melhor — e é o prompt que faz.

### O que importa aqui, especificamente

- **Extração pede literalidade, recomendação pede inferência.** São prompts de natureza oposta e
  é por isso que são agentes separados (conceito 8). No Extractor, o modelo tem que devolver o
  **trecho exato** junto da conclusão — a `Evidencia` de D-009 exige `trecho`, não paráfrase.
  Peça o span literal e valide que ele **existe** no documento de origem.
- **Few-shot vale mais que instrução longa** em classificação com rubrica. Dois ou três exemplos
  de AI-native vs AI-enabled tirados da sua própria base ensinam a régua melhor que um parágrafo
  descrevendo-a.
- **Saída estruturada não é opcional aqui** — ver conceito 10.
- **Reprompt com o erro de validação.** Quando o Pydantic rejeitar, retry cego não resolve
  (a chamada é determinística demais). O que resolve é devolver a mensagem de validação ao
  modelo e pedir correção. Está registrado na nota de D-024.
- **Peça o "não sei".** Um prompt que só oferece caminhos de resposta positiva produz a dor
  inventada do erro nº 2 de D-020. Dê saída explícita: *"se o documento não sustenta nenhuma das
  oito dores, devolva lista vazia"*. É a mesma disciplina de D-021 aplicada ao prompt — **`null`
  precisa ser uma resposta permitida.**

**O que estudar.** O guia de *prompt engineering* da documentação da Anthropic (as páginas de
*be clear and direct*, *multishot prompting* e *chain of thought* cobrem 90% do que você
precisa). Depois, a página de *structured outputs*. Estude **na M4**, não antes — sem os nós
reais na frente, não gruda.

**Como saber que entendeu.** Você escreve o prompt do Extractor e consegue dizer, para cada
pedaço dele, qual erro de D-020 aquele pedaço existe para evitar.


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

# Arguição — rodada 1: o RAG (após a sessão 02)

O `guia-de-trabalho.md` chama isto de *"o uso mais valioso da ferramenta neste projeto"*: depois
de fechar cada parte, pedir as perguntas difíceis. **Se eu travar em alguma, achei o buraco antes
do avaliador achar.**

**Como usar.** Não responda agora, de memória. Cada pergunta abaixo diz qual conceito ela cobra e
o que ler antes. Estude, feche os arquivos, e só então responda — em voz alta, cronometrado, como
no vídeo. Resposta que só funciona com o repositório aberto não é resposta.

**Duas delas têm resposta factual no código.** Vá conferir em vez de chutar: na banca, o chute é
que vira o problema, não o defeito que ele tentava esconder.

---

### 1. O experimento está confundido — estrutura ou breadcrumb?

> Você abre D-032 dizendo que a medição confirma o chunking estrutural. Mas o seu braço de
> controle, `fixo-800`, não tem breadcrumb nenhum, e o `estrutural-v1` tem o caminho da seção
> prefixado em todo chunk. Você está comparando duas coisas que diferem em **duas** variáveis ao
> mesmo tempo.
>
> Como você sabe que os 16 pontos de diferença em `recall@3` vêm da **estrutura das seções**, e
> não simplesmente de ter colado o nome da tecnologia em cada chunk? E se vierem inteiramente do
> breadcrumb — o que sobra de D-025?

**O que ela cobra:** conceito 5 (chunking) e 6 (avaliação). No fundo é desenho de experimento:
variável de tratamento, variável de confusão, braço de controle.

**O que ler antes:** D-025, D-027 e D-032 · o docstring de `src/rag/chunking.py`, seção "O QUE
`estrategia='fixo-800'` É, E O QUE ELA NÃO É" · a dívida nº 2 no topo de `sessao-03.md`.

**Onde a resposta fica forte:** o terceiro braço já está a um parâmetro de distância
(`chunk_fixo(..., com_caminho=True)`). Saber dizer **qual número ele produziria e o que cada
resultado possível significaria** vale mais que ter rodado.

---

### 2. `recall@3 = 100%` mede recuperação ou mede um corpus pequeno?

> O seu corpus tem exatamente 16 documentos, um por tecnologia, e o `recall@k` do gabarito ancora
> no `documento_url`. Então *"recuperei o documento certo"* e *"acertei a tecnologia"* são **a mesma
> proposição** no seu sistema: a métrica é um classificador de 16 classes.
>
> Nessas condições, o que `recall@3 = 100%` mede de fato? Defenda o número como evidência de
> qualidade de recuperação, e não como sintoma de um corpus pequeno demais para a régua que você
> escolheu.

**O que ela cobra:** conceito 6 (avaliação de RAG), na parte que quase ninguém pensa — a **validade**
da métrica, não o cálculo dela.

**O que ler antes:** D-030 (por que a âncora é o documento) · a variante estrita no docstring de
`scripts/avaliar_rag.py` · a tabela de D-032, prestando atenção em qual coluna satura e qual não.

**Onde a resposta fica forte:** a saída não é defender o 100%. É saber **qual das suas métricas não
satura e por quê**, e o que você mudaria no gabarito para que ela voltasse a discriminar quando o
corpus crescer.

---

### 3. Uma decisão de arquitetura com n = 1

> D-033 declara um princípio geral — *"similaridade mede pertinência de tópico, não existência de
> resposta"* — e com base nele tira a abstenção do limiar de score e joga a responsabilidade para
> o reranker.
>
> Quantas perguntas sem resposta na base você mediu para chegar nesse princípio? Qual é o `n`?
> E o que precisaria acontecer na sessão 03 para você concluir que D-033 estava errada?

**O que ela cobra:** conceito 6 (avaliação) e 9 (alucinação e grounding) — abstenção é o mecanismo
que impede o LLM de inventar quando a base não tem a resposta.

**O que ler antes:** D-033 inteira, incluindo os três trechos que a q20 recuperou · a q20 em
`data/avaliacao/gabarito.yaml` e a nota de curadoria dela · conceito 4, sobre por que um
cross-encoder responde uma pergunta diferente da do bi-encoder.

**Onde a resposta fica forte:** separar as duas coisas que D-033 afirma — o **fato medido** (a
margem deu negativa naquela pergunta) e a **explicação proposta** (similaridade mede tópico). A
primeira tem n = 1; a segunda é um argumento conceitual que não depende do n. Saber dizer qual é
qual, e qual das duas o reranker vai testar, é a resposta.

---

### 4. A sobreposição que às vezes não existe

> O docstring do `_dividir` promete *"um parágrafo de sobreposição entre partes consecutivas, para
> que uma frase partida ao meio ainda apareça inteira em algum chunk"*. Abra `src/rag/chunking.py`
> e leia esta linha:
>
> ```python
> atual = [atual[-1], p] if len(atual) > 1 else [p]    # sobreposição de 1 parágrafo
> ```
>
> O que acontece com a sobreposição quando um parágrafo sozinho já ocupa quase todo o teto? Em que
> fração do seu corpus real isso ocorre? E o `test_dividir_sobrepoe_um_paragrafo_entre_partes`
> cobre esse caminho ou o outro?

**O que ela cobra:** conceito 5 (chunking) no nível de implementação — e a disciplina de o
docstring dizer o que o código faz, não o que você quis que ele fizesse.

**O que ler antes:** `_dividir` inteira em `src/rag/chunking.py` · o teste citado, em
`tests/test_chunking.py` · **e rode a medição**: quantos chunks do corpus vêm de seções que foram
divididas, e em quantas a sobreposição de fato ocorreu.

**Onde a resposta fica forte:** três saídas são defensáveis — corrigir, documentar o limite, ou
argumentar que a sobreposição não importa neste corpus. **Escolher uma delas conscientemente** é o
que separa nível 3 de nível 2. Não saber que o caso existe é o que derruba.

---

### 5. A frase que você repete em três arquivos e nunca mediu

> *"Embedar documento como consulta degrada a recuperação silenciosamente"* aparece em três lugares
> do seu repositório e justifica o `input_type="passage"` na ingestão e o `"query"` na busca.
>
> Você mediu essa degradação? Hoje você tem corpus embedado, gabarito de 20 perguntas e um harness
> que roda em segundos — quanto custaria produzir o número? E enquanto ele não existe, o que
> exatamente aquela frase é dentro do seu projeto?

**O que ela cobra:** conceito 1 (embedding), na parte específica dos modelos **assimétricos** de
recuperação — por que query e passage são treinados em espaços diferentes e o que isso implica.

**O que ler antes:** `contexto/03` §3, os "dois detalhes que só aparecem chamando" · a decisão 2 no
docstring de `scripts/ingerir_nvidia.py` · o conceito 1 deste arquivo.

**Onde a resposta fica forte:** distinguir **o que você verificou** (o parâmetro existe, é exigido,
e o smoke test da sessão 01 mediu separação semântica) de **o que você herdou da documentação** (o
tamanho da degradação). Dizer "isso eu li, não medi" é resposta de nível 4. Dizer "degrada muito"
sem número, quando o número custa cinco minutos, é onde o avaliador puxa o fio.

---

**Duas observações sobre o conjunto.** A 1 e a 2 são as mais difíceis de defender, e as duas são
consequência de escolhas registradas e aprovadas — não de descuido. A 1 tem saída barata, já
anotada como dívida na `sessao-03.md`. A 2 não tem saída barata, e a resposta honesta
provavelmente não é *"o número está certo"*.

**Rodadas seguintes:** depois da sessão 03 (fusão e reranking), da M4 (agentes e recomendação) e
antes de gravar o vídeo. Pedir com: *"me faça 5 perguntas difíceis sobre X que eu acabei de
construir"*.

---

# Como usar este arquivo

**Não leia tudo agora.** Leia o conceito antes da sessão que o implementa — é aí que ele gruda.

| Antes de | Leia |
|---|---|
| sessão 02 (RAG, passos 1-5) | 1, 5, 7 — **e 11**, porque a ingestão é da documentação NVIDIA: você vai ler as 16 tecnologias de qualquer jeito, então leia entendendo |
| sessão 03 (busca híbrida + rerank) | 2, 3, 4 |
| sessão 04 (otimização medida) | 6 — mas o harness já existe desde a 02 (D-031) |
| M3, montar a base de startups | **12** — é a régua que decide quais empresas entram e por quê |
| sessões dos agentes (M4) | 8, 10, 13 |
| gravar o vídeo | 9, 11, 12 + reler `decisoes.md` inteiro |
| **responder a arguição** | o conceito que cada pergunta cobra, indicado nela — depois responda sem consultar |

**Os dois de domínio são diferentes dos outros onze.** 11 e 12 não se aprendem
implementando — o código não te ensina o que é o NIM nem o que é AI-native. São os únicos que
exigem sentar e ler `contexto/02` e `contexto/03` de propósito. São também os dois que o vídeo
mais cobra. Reserve uma sessão inteira para eles, ou eles não acontecem.

**Implementar já é estudar** — para os outros. Os conceitos 1-6 *são* a sessão 02. Você não precisa estudá-los
antes e depois — precisa ler 30 minutos antes de cada bloco e implementar com o conceito fresco.
