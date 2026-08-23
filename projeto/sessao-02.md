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

| Sessão | Passos | Termina quando |
|---|---|---|
| **02** ← você está aqui | 1-5 · ingestão → embeddings → armazenamento | `chunks_nvidia` populada, índice HNSW criado, um `SELECT` por similaridade devolve chunk plausível |
| **03** | 6-8 · busca híbrida → reranking → citação | `buscar_hibrido(query, k)` devolve `CitacaoRAG` com os **três** scores preenchidos |
| **04** | 9 · avaliação | recall@k medido para denso puro vs híbrido vs híbrido+rerank |

**Por que não juntar 02 e 03.** A ingestão sempre dá mais trabalho que o previsto — são 16
páginas da NVIDIA com estrutura diferente, e cada erro de parsing só aparece depois de embedar.
Se a busca híbrida estiver na mesma sessão, ela é a parte que é cortada às pressas — e ela é
metade do critério 2.

**Por que a 04 é separada.** O harness é o passo que mais separa nível 2 de nível 4, e ele exige
escrever o conjunto de perguntas com resposta esperada — trabalho de curadoria, não de código.
Feito com pressa no fim da 03, vira 5 perguntas fáceis que todo método acerta, e aí não mede nada.

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

### Sessão 03 — passos 6-8 (busca híbrida → reranking → citação)
- [ ] `bm25s` em processo, com `k1`/`b` explícitos
- [ ] Fusão denso + lexical atrás de `buscar_hibrido(query, k)` — **o peso entre os dois precisa
      ser configurável**, porque a base NVIDIA é em inglês e a consulta nasce de texto português:
      léxico não atravessa idioma (ver D-014)
- [ ] Reranking com `llama-nemotron-rerank-1b-v2`, preenchendo os **três** scores de `CitacaoRAG`

### Sessão 04 — passo 9, **o que mais separa nível 2 de nível 4 no critério 2**
- [ ] Harness de avaliação: conjunto de perguntas com resposta esperada, recall@k, e comparação
      denso puro vs híbrido vs híbrido+rerank. É o que transforma D-014 ("1024 por causa do HNSW")
      em medição, e permite comparar 384 vs 768 vs 1024

## Decisão adiada que volta aqui
`PostgresSaver` no lugar do `MemorySaver` (D-006). Passa a valer a pena quando os nós tiverem
LLM de verdade e re-rodar custar crédito.
