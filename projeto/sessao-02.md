# Sessão 02 — RAG NVIDIA (M2)

## Onde a sessão 01 parou

**Concluído:** ambiente, stack validada por medição, estado do grafo, schema + seed
reproduzível, grafo rodando ponta a ponta, 20 decisões registradas, 11 testes.

**Critério de pronto que ficou parcial:** a sessão 01 pedia 5 startups × 3 documentos.
Entregou **3 × 3 = 9 documentos**, todos com `url_fonte` verificada em HTTP 200 e
`conteudo_texto` extraído da página real. Faltam os 2 slots de curadoria abaixo. Não bloqueia
nada — o grafo já roda, e a base completa é a M3 (02/09).

## Pendências herdadas

| # | O que | Por quê |
|---|---|---|
| 1 | **Slot non-AI** na base | é o caso negativo; hoje as 3 empresas são de IA e o Classifier nunca exercita o "não" |
| 2 | **Slot inelegível ao Inception** de verdade | o único "não elegível" de hoje é o falso positivo da Axenya (D-020), não um caso real |
| 3 | **Tractian** como caso "AI-native + stack madura" | ela já aparece no blog da própria NVIDIA — testa o sistema recusar recomendar NIM para quem já otimizou, e recomendar Inception |
| 4 | Perguntar à liga: **canal de submissão** e **individual ou em grupo** | o TAPI não diz nem uma coisa nem outra; eliminatório nº 1 é entrega fora do prazo *sem alinhamento prévio* |

## Pauta da sessão 02 — os 9 passos do pipeline RAG

Passos 1-5 (ingestão → embeddings → armazenamento):
- [ ] Coletar as 16 tecnologias de `contexto/03` §5 (URLs oficiais já verificadas)
- [ ] **Chunking semântico** — decidir a estratégia e registrar a alternativa descartada
- [ ] Tabela `chunks_nvidia` com `vector(1024)` + índice HNSW (o limite de 2000 dims já foi
      verificado; 1024 cabe)
- [ ] Embedar com `input_type="passage"` — a assimetria do NeMo Retriever é silenciosa: embedar
      documento como consulta degrada a recuperação sem dar erro

Passos 6-8 (busca híbrida → reranking → citação):
- [ ] `bm25s` em processo, com `k1`/`b` explícitos
- [ ] Fusão denso + lexical atrás de `buscar_hibrido(query, k)` — **o peso entre os dois precisa
      ser configurável**, porque a base NVIDIA é em inglês e a consulta nasce de texto português:
      léxico não atravessa idioma (ver D-014)
- [ ] Reranking com `llama-nemotron-rerank-1b-v2`, preenchendo os **três** scores de `CitacaoRAG`

Passo 9 — **o que mais separa nível 2 de nível 4 no critério 2**:
- [ ] Harness de avaliação: conjunto de perguntas com resposta esperada, recall@k, e comparação
      denso puro vs híbrido vs híbrido+rerank. É o que transforma D-014 ("1024 por causa do HNSW")
      em medição, e permite comparar 384 vs 768 vs 1024

## Decisão adiada que volta aqui
`PostgresSaver` no lugar do `MemorySaver` (D-006). Passa a valer a pena quando os nós tiverem
LLM de verdade e re-rodar custar crédito.
