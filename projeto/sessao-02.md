# Sessão 02 — RAG NVIDIA (M2)

## Sessão 01 — FECHADA em 23/08/2026

**Concluído:** ambiente, stack validada por medição, estado do grafo, schema + seed
reproduzível, grafo rodando ponta a ponta, **24 decisões** registradas, **15 testes**.

Os 5 critérios de pronto da `sessao-01.md`: 4 cumpridos, 1 parcial (base de startups).

**Critério de pronto que ficou parcial:** a sessão 01 pedia 5 startups × 3 documentos.
Entregou **3 × 3 = 9 documentos**, todos com `url_fonte` verificada em HTTP 200 e
`conteudo_texto` extraído da página real. Faltam os 2 slots de curadoria abaixo. Não bloqueia
nada — o grafo já roda, e a base completa é a M3 (02/09).

**Revisão de encerramento (23/08).** Uma passagem pela topologia achou três defeitos em
caminhos que o "caminho feliz" nunca toca. Os três foram reproduzidos, corrigidos e viraram
teste — ver D-022, D-023, D-024:

| | O que estava errado | Como aparecia |
|---|---|---|
| D-022 | `thread_id` fixo + reducer `operator.add` | rodar o comando 2x duplicava as startups no briefing |
| D-023 | fan-out vazio não alcançava o briefing | consulta sem resultado terminava em silêncio |
| D-024 | `try/except` em volta do subgrafo descartava o trabalho parcial | falha no meio voltava com `perfil=None` |

D-006 foi corrigida no lugar: ela declarava quatro recursos do LangGraph e o código tinha dois.
Agora são três — `cache_policy` segue não implementado de propósito, entra com o primeiro nó
que chamar LLM (M4).

**Ainda em aberto da topologia (não bloqueia a M2):** o subgrafo é compilado sem checkpointer
e invocado à mão, então o checkpoint tem granularidade de startup inteira e `interrupt()` não
funciona lá dentro — e "intervenção humana" é uma das justificativas que o TAPI dá para exigir
LangGraph. Decidir junto com o `PostgresSaver`. Também em aberto: `max_concurrency` não está
configurado, e o teto de paralelismo hoje mora no planner (`MAX_STARTUPS`), não no executor —
amarra com o risco nº 1 (créditos).

## Pendências herdadas

| # | O que | Por quê |
|---|---|---|
| 1 | **Slot non-AI** na base | é o caso negativo; hoje as 3 empresas são de IA e o Classifier nunca exercita o "não" |
| 2 | **Slot inelegível ao Inception** de verdade | o único "não elegível" de hoje é o falso positivo da Axenya (D-020), não um caso real |
| 3 | **Tractian** como caso "AI-native + stack madura" | ela já aparece no blog da própria NVIDIA — testa o sistema recusar recomendar NIM para quem já otimizou, e recomendar Inception |
| 4 | Perguntar à liga: **canal de submissão** e **individual ou em grupo** | o TAPI não diz nem uma coisa nem outra; eliminatório nº 1 é entrega fora do prazo *sem alinhamento prévio* |

## M2 são três sessões, não uma

Os 9 passos do pipeline RAG não cabem numa sessão. O corte abaixo é por **acoplamento**: cada
bloco termina num artefato testável, e o seguinte só depende do artefato, não do contexto de
quem escreveu.

| Sessão | Entrega | Termina quando |
|---|---|---|
| **02** ← você está aqui | passos 1-5 **+ o gabarito de avaliação** | `chunks_nvidia` populada e indexada, **e** um conjunto de perguntas com fonte esperada capaz de pontuá-la |
| **03** | passos 6-8 · busca híbrida → reranking → citação | `buscar_hibrido(query, k)` devolve `CitacaoRAG` com os **três** scores, e cada incremento foi medido contra o gabarito |
| **04** | passo 9 · otimização guiada por medida | recall@k comparando denso vs híbrido vs +rerank, 384 vs 768 vs 1024, e duas estratégias de chunking |

### O gabarito é da sessão 02, não da 04 — isto é a parte não óbvia

A primeira versão deste plano deixava a avaliação inteira para a sessão 04. Está errado, e o
motivo é específico: **a sessão 02 decide chunking e dimensão, e o harness é o instrumento que
mede essas duas decisões.** Deixá-lo para depois significa decidir por argumento e descobrir por
medição — quando D-014 já registra que mudar a dimensão exige re-embedar o corpus inteiro.

Duas razões para escrever o gabarito aqui:

1. **Ele não depende de chunking.** Ancore a resposta esperada no **documento-fonte** ("qual
   tecnologia dá speculative decoding?" → página do TensorRT-LLM), não num id de chunk. Assim
   `recall@k` = "apareceu algum chunk do documento certo entre os k primeiros", e a métrica
   sobrevive a qualquer mudança de chunking — que é justamente o que permite **comparar**
   estratégias. Variante mais estrita: anotar a frase que responde e checar se o chunk a contém.
2. **É quase de graça agora e caro depois.** Você vai ler as 16 páginas para coletar. Esse é o
   momento de escrever a pergunta e anotar a fonte. Na sessão 04, custa reler as 16 páginas.

Mire em **15 a 20 perguntas**, incluindo casos difíceis de propósito: uma que exija o léxico
(nome de produto raro), uma que exija o denso (pergunta em português sobre página em inglês), e
uma **sem resposta na base** — para medir se o sistema sabe dizer "não sei".

**Por que 02 e 03 são separadas.** A ingestão sempre dá mais trabalho que o previsto — 16 páginas
com estruturas diferentes, e erro de parsing só aparece depois de embedar. Se a busca híbrida
estiver na mesma sessão, ela é a parte cortada às pressas — e é metade do critério 2.

> **É teto, não piso.** Se a coleta correr lisa, 02 e 03 podem virar uma sessão só. O que não se
> deve fazer é *planejar* assim. E o número é estimativa pela forma do trabalho, não medição.

**O que NÃO fazer na 02:** busca lexical, fusão, reranking. Estão listados abaixo para você ver o
destino, não para implementar agora.

---

## Pauta da sessão 02 — passos 1-5

Ingestão → embeddings → armazenamento:
- [ ] Coletar as 16 tecnologias de `contexto/03` §5 (URLs oficiais já verificadas)
- [ ] **Chunking semântico** — decidir a estratégia e registrar a alternativa descartada
- [ ] Tabela `chunks_nvidia` com `vector(1024)` + índice HNSW (o limite de 2000 dims já foi
      verificado; 1024 cabe)
- [ ] Embedar com `input_type="passage"` — a assimetria do NeMo Retriever é silenciosa: embedar
      documento como consulta degrada a recuperação sem dar erro
- [ ] **Gabarito de avaliação: 15-20 perguntas com o documento-fonte esperado**, escritas
      DURANTE a coleta. Versionar em `data/avaliacao/`. É o que transforma as decisões de
      chunking e dimensão em medição na sessão 04 — e é quase de graça agora

### Sessão 03 — passos 6-8 (busca híbrida → reranking → citação)
- [ ] `bm25s` em processo, com `k1`/`b` explícitos
- [ ] Fusão denso + lexical atrás de `buscar_hibrido(query, k)` — **o peso entre os dois precisa
      ser configurável**, porque a base NVIDIA é em inglês e a consulta nasce de texto português:
      léxico não atravessa idioma (ver D-014)
- [ ] Reranking com `llama-nemotron-rerank-1b-v2`, preenchendo os **três** scores de `CitacaoRAG`

### Sessão 04 — passo 9: otimizar com o gabarito que a 02 escreveu

**O que mais separa nível 2 de nível 4 no critério 2.** A sessão 04 não constrói a régua — ela
já existe desde a 02. Aqui ela é usada para decidir:
- [ ] Harness de avaliação: conjunto de perguntas com resposta esperada, recall@k, e comparação
      denso puro vs híbrido vs híbrido+rerank. É o que transforma D-014 ("1024 por causa do HNSW")
      em medição, e permite comparar 384 vs 768 vs 1024

## Decisão adiada que volta aqui
`PostgresSaver` no lugar do `MemorySaver` (D-006). Passa a valer a pena quando os nós tiverem
LLM de verdade e re-rodar custar crédito.
