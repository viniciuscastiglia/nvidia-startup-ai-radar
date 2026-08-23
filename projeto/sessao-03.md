# Sessão 03 — RAG NVIDIA (M2), passos 6-8: busca híbrida → reranking → citação

## Sessão 02 — FECHADA em 23/08/2026

**Concluído:** base de conhecimento NVIDIA ingerida, chunkada, embedada, indexada e **medida**.
16 tecnologias · 163.094 chars · **177 chunks estruturais + 204 no braço de controle** ·
gabarito de 20 perguntas · **9 decisões** (D-025 a D-033) · **29 testes**.

### Correção de escopo feita no início da sessão (D-031)

O plano original da 02 terminava com a tabela populada e deixava o harness de `recall@k` para a
04. Dois problemas: o critério de pronto da **03** já dizia *"cada incremento foi medido contra o
gabarito"* — dependendo de um artefato que ainda não existia; e a **02** decidia chunking sem
instrumento para medir a própria decisão. Busca densa pura e `recall@k` entraram aqui. BM25,
fusão e reranking continuaram intocados.

### O resultado — a régua já existe e já tem número

Gabarito de 20 perguntas, recuperação densa pura, 1024 dimensões:

| k | estrutural frouxo | fixo-800 frouxo | estrutural estrito | fixo-800 estrito |
|---|---|---|---|---|
| 1 | 89% | 84% | 68% | 58% |
| **3** | **100%** | **84%** | **79%** | **68%** |
| 5 | 100% | 100% | 84% | 74% |

`recall@5` satura nos dois braços — **k=3 é o ponto que discrimina.** Ver D-032.

### Três coisas que só apareceram medindo

| | O que se supunha | O que a medição mostrou |
|---|---|---|
| **Matryoshka** | trocar de dimensão exige re-embedar o corpus (D-014) | truncar 2048 localmente e renormalizar dá cos = **0.99999996** contra pedir à API. O sweep da 04 custa zero chamada (D-029) |
| **Limite do embedder** | o teto do chunk seria imposto pelo modelo | ele aceita **6.144 a 8.192 tokens** — o teto é escolha de precisão, não restrição técnica |
| **Abstenção** | um limiar sobre o score denso separaria "não sei" | **margem negativa** (−0.19). Similaridade mede tópico, não existência de resposta (D-033) |

E três coisas que a curadoria derrubou: `1.201 tokens/s`, `paged KV cache` e `Isaac GR00T` estão
em `contexto/03` mas **não estão nas páginas vivas** — o contexto foi escrito de uma versão
anterior. Perguntas ancoradas neles seriam impossíveis de acertar e o erro pareceria do
recuperador.

### Dívida deixada de propósito

| # | O que | Por quê |
|---|---|---|
| 1 | `src/agents/nvidia_rag.py` continua com a base provisória de 8 dores | trocar agora acoplaria o agente a uma assinatura que muda na 03 quando `buscar_hibrido()` existir |
| 2 | Terceiro braço de chunking (janela fixa **com** breadcrumb) | separaria "quanto vale a estrutura" de "quanto vale o breadcrumb". É um parâmetro `com_caminho=True`, não código novo. Cabe na 04 |
| 3 | `PISO_TOKENS`/`TETO_TOKENS` escolhidos por inspeção | viram medição na 04, junto com o sweep de dimensão |
| 4 | Janela do reranker não medida | **entra como primeira tarefa desta sessão** — ver abaixo |

---

## Pauta da sessão 03 — passos 6, 7 e 8

### Bloco 0 — Medir a janela do reranker (~15 min) — **bloqueante**

`TETO_TOKENS = 450` foi escolhido supondo janela de cross-encoder de 512, e **isso não foi
medido**. Se `llama-nemotron-rerank-1b-v2` aceitar menos, todo chunk acima do limite tem o final
truncado no rerank — e o trecho que responde a pergunta pode ser justamente o que se perde.
Mesmo método diferencial do `verificar_embedder.py`: passagem com a resposta no fim contra a
mesma passagem com a resposta no começo.

### Bloco 1 — BM25 em processo (passo 6a)
- [ ] `bm25s`, com `k1` e `b` **explícitos** — D-016 justifica a escolha por eles serem
      ajustáveis; deixá-los no default entregaria o argumento sem entregar a coisa
- [ ] Indexar `texto_indexado` (o mesmo campo que foi embedado), por estratégia
- [ ] **Previsão registrada em D-032, para confirmar ou derrubar:** a q14 (cuDF vs cuML) erra em
      k=1 nos dois braços densos porque os READMEs são quase idênticos. A âncora `cudf.pandas` é
      literal — se o BM25 não resolver esta, ele não está pagando o que custa

### Bloco 2 — Fusão (passo 6b)
- [ ] `buscar_hibrido(query, k, estrategia)` com a **mesma assinatura** de `buscar_denso`
- [ ] Peso denso × lexical **configurável**, e a razão é medida: a q05 pergunta em português
      sobre a palavra "Portuguese" numa página em inglês. Léxico não atravessa idioma (D-014),
      então peso lexical alto demais quebra exatamente o caso crosslingual que é o caminho
      principal do sistema real
- [ ] Comparar fusão por RRF contra soma ponderada, no gabarito

### Bloco 3 — Reranking (passo 7)
- [ ] `llama-nemotron-rerank-1b-v2`, preenchendo o terceiro score de `CitacaoRAG`
- [ ] **A q19 é o caso-teste:** em k=3 o chunk certo (NIM) já está entre os recuperados mas não
      em primeiro. Se o reranker serve para alguma coisa, é para promovê-lo. `recall@1` é a
      métrica que mede isso
- [ ] **Testar a hipótese de D-033:** o cross-encoder julga se a passagem *responde* a pergunta,
      não só se fala do assunto. Medir a margem de abstenção na q20 depois do rerank e comparar
      com os −0.1879 de hoje. Se continuar negativa, a abstenção sobe para a geração

### Bloco 4 — Citação (passo 8)
- [ ] Resposta com citação: trecho + `documento_url` + os três scores
- [ ] Só então trocar a base provisória de `src/agents/nvidia_rag.py`

## Medir cada incremento contra o gabarito

O critério de pronto desta sessão é o mesmo de sempre, e agora é executável: **cada bloco acima
roda `python scripts/avaliar_rag.py` antes e depois.** A linha de base a bater está em D-032.
Incremento que não mova a métrica é incremento que precisa de justificativa — ou de remoção.
