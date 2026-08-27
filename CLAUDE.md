# NVIDIA Startup AI Radar — Processo Seletivo Inteli Academy

> Este arquivo é carregado automaticamente em toda sessão do Claude Code aberta nesta pasta.
> Ele é o contexto mínimo. Os detalhes estão em `contexto/` — abra sob demanda.

## O que é

Plataforma **multi-agente** que recebe uma consulta em linguagem natural, recupera startups
brasileiras de uma base pré-populada, diagnostica a **maturidade AI-native** delas a partir de
texto não estruturado, consulta uma **base RAG de tecnologias NVIDIA** e gera um **briefing
executivo** para o gerente de Startups & VCs da NVIDIA Brasil captar startups para o
**NVIDIA Inception**.

**Pergunta norteadora:** como a NVIDIA pode identificar, atrair e nutrir startups brasileiras
AI-native num contexto em que os grandes labs de IA ameaçam startups que dependem apenas de
wrappers de LLM?

**Entrega:** implementação própria do projeto, seguindo o TAPI em `TAPI Processo Seletivo.md`.
**Prazo: 09/09/2026 às 23:59.**

## Barema — nota = Σ peso × (nível/4), níveis 0 a 4

| # | Critério | Peso |
|---|---|---|
| 1 | Sistema multiagente com LangGraph | 20 |
| 2 | RAG NVIDIA com reranking | 20 |
| 3 | Motor de recomendação | 20 |
| 4 | Interface web | **5** |
| 5 | **Vídeo de apresentação** | **20** |
| 6 | Diferencial do projeto | 5 |
| 7 | Repositório e documentação | 10 |

Níveis: 0 não entregue · 1 insuficiente · 2 cumpre o mínimo · 3 bom, com decisões técnicas
conscientes · 4 excelente, supera o esperado.

**Leitura estratégica — onde os pontos realmente estão:**
- Núcleo de IA (1+2+3) = **60** · Comunicação (vídeo + repo/docs) = **30** · Produto (interface + diferencial) = **10**
- O **vídeo vale o mesmo que o sistema multi-agente inteiro** e 4x a interface
- A **interface web é o Entregável 4 mas vale 5 pontos** — não investir uma semana nela
- Nível 2 em tudo = 50/100. Nível 3 em tudo = 75. A diferenciação está em subir de
  "cumpre o requisito" para "decisões técnicas conscientes"

## Critérios eliminatórios

1. Entrega fora do prazo sem alinhamento prévio
2. Ausência do vídeo de apresentação
3. Projeto que não executa **e** cujo vídeo não demonstra funcionamento real
4. **Código integralmente gerado sem compreensão** — o candidato precisa explicar as decisões
   de arquitetura do próprio projeto
5. Plágio de outro projeto

O TAPI é explícito: *"O uso de IA como ferramenta de desenvolvimento é permitido e esperado.
O que se avalia é a capacidade de tomar e defender decisões técnicas."*

## Como trabalhar neste projeto

O eliminatório nº 4 define o modo de trabalho aqui. Ao implementar qualquer coisa:

- **Explique a decisão antes de escrever o código.** Por que LangGraph e não uma chain simples,
  por que esse chunking, por que reranking cross-encoder e não bi-encoder, por que esse estado
  no grafo. O Vinícius precisa defender isso numa banca.
- **Ofereça a alternativa que foi descartada e o motivo.** É isso que vira resposta pronta
  quando o avaliador perguntar "por que não X?".
- **Nada de código mágico.** Se uma escolha só se justifica por conveniência, diga isso.
- Português nas explicações e na documentação.
- **Subagentes: evitar neste projeto.** Eles começam sem contexto e devolvem resultado pronto,
  que é o oposto do eliminatório nº 4 — o candidato precisa ter acompanhado a decisão para
  defendê-la. Detalhe em `projeto/guia-de-trabalho.md`.

## Arquitetura alvo (LangGraph — obrigatório, é o único nome citado no barema)

```
Consulta do usuário
  -> Query Planner Agent      NL -> critérios de busca + estratégia de análise
  -> Retriever Agent          seleciona empresas e documentos/evidências na base
  -> Extractor Agent          texto bruto -> perfil estruturado (empresa + stack)
  -> Startup Classifier Agent AI-native | AI-enabled | non-AI
  -> Evidence Validator Agent as afirmações têm fonte suficiente?
  -> NVIDIA RAG Agent         consulta a base de conhecimento NVIDIA
  -> Reranker
  -> Recommendation Agent     cruza perfil x tecnologias
  -> Briefing Agent           relatório final
  -> Interface web
```

## Stack

**Definido pelo TAPI:** LangGraph (obrigatório). PostgreSQL para dados estruturados,
Qdrant para vetores, BM25 para busca lexical, Cohere Rerank — todos *recomendados*, não obrigatórios.
Frontend livre.

**Fechado na sessão 01** (justificativas em `projeto/decisoes.md`):

| Camada | Escolha | Decisão |
|---|---|---|
| LLM dos agentes | ~~`meta/llama-3.1-8b-instruct`~~ **MORTO 27/08 (410) — EM ABERTO** | D-012, **D-064** |
| Embeddings | `nvidia/llama-nemotron-embed-vl-1b-v2`, **`dimensions=1024`** | D-014, **D-046** |
| Reranking | ~~`nvidia/rerank-qa-mistral-4b`~~ **MORTO 27/08 (404), sem substituto — EM ABERTO** | D-015, D-046, **D-064, D-065** |
| Vetores | pgvector no mesmo Postgres | D-016 |
| Busca lexical | `bm25s` em processo para o RAG · `tsvector` para documentos de startup | D-016 |
| Topologia | subgrafo de análise + fan-out por `Send` | D-007 |
| Chunking | estrutural por seção + breadcrumb prefixado · janela fixa como controle | D-025, D-027 |
| BM25 | `bm25s` método **`lucene`**, `k1=1.2`, `b=0.75`, tokenizador que dobra acento | D-036 |
| Fusão | **RRF** (`K=10`) de produção · soma ponderada como braço de controle medido | D-037 |
| Rerank | lê `texto_indexado` (com breadcrumb); janela real de **8192 tokens conjuntos** | D-034, D-038 |
| Saída estruturada | `with_structured_output(..., method="json_schema")` via `src/llm.py` | D-040 |
| Schema que vai ao LLM | tipo **estreito** por chamada — docstring de schema é **prompt** | D-045 |
| Consulta do RAG | rótulo da dor + `dor.evidencias[*].trecho` (a fala da startup) | D-043 |
| Harness | importa os defaults de `src.rag.pipeline`; **não trunca** o pool | D-044 |

> **Atenção — a stack de recuperação já morreu DUAS vezes, e isso é um risco de projeto, não uma
> anedota.** O catálogo de preview do build.nvidia.com aposenta modelos com **HTTP 410** em
> cadência de meses:
>
> | data | o que morreu |
> |---|---|
> | 18/05/2026 | `llama-3.2-nv-embedqa-1b-v2` e `llama-3.2-nv-rerankqa-1b-v2` — os que o TAPI cita (D-013) |
> | **25/08/2026 09:00Z** | `llama-nemotron-embed-1b-v2` e `llama-nemotron-rerank-1b-v2` — os substitutos (D-046) |
> | **27/08/2026** | **`meta/llama-3.1-8b-instruct` (410) e `rerank-qa-mistral-4b` (404)** — o LLM dos agentes e o ÚLTIMO reranker (D-064) |
>
> **ESTADO EM 27/08: só o EMBEDDING responde.** Chat 410, reranking 404 em 18 sondagens de
> path × modelo, e o catálogo vivo (84 modelos) não lista **nenhum** reranker. O embedder
> `llama-nemotron-embed-vl-1b-v2` sobreviveu — os 381 vetores estão intactos. **A escolha do passo
> 7 e do LLM está EM ABERTO (D-064, D-065)** e é o Bloco 0 da sessão 08.
>
> Nunca usar esses seis nomes. **Env var não protege contra isto:** trocar o embedder muda o
> espaço vetorial e invalida os 381 vetores — é `scripts/reembedar.py` mais re-medir a régua
> inteira. Ver D-046 e `contexto/03` §3.

**Em aberto:** framework de frontend (P-06) e quantas startups entram na base final.

**Régua dos agentes (M4, sessão 06):** 8 fixtures em `data/seed/*.yaml`, uma por decisão que ela
flipa, com bloco `gabarito:` estruturado que **não vai para o banco**. É o que faltava para os
critérios 1 e 3 (40 pontos) — antes eram 3 startups e as 3 `AI-native`, então um classificador
que devolvesse "AI-native" incondicionalmente passava em 3 de 3 (D-050, D-051).

| | trivial | **casador — produção** | juiz com LLM (n=3, D-056) |
|---|---|---|---|
| classe | 4/7 | **3/7** | 2–3 / 7 |
| maturidade_stack | 6/7 | **6/7** | 6/7 |
| confiança | 3/8 | **0/6** (+2 ambíguos) | 0/6 |
| elegível | 6/7 | **5/7** | 5–6 / 7 |
| motivo_exclusão | 6/7 | **5/7** | 5–6 / 7 |
| **dor — precisão** | 32% | **49%** | 50–62% |
| dor — recall | 100% | **100%** | 79–96% |
| discriminação | 1/8 | **8/8** | 8/8 |
| dor proibida emitida | 28 | **10** | 6–9 |

**A linha trivial é obrigatória na tabela** — é o `denso puro` deste critério. E ela expõe o
achado que justificou a sessão: **o casador perde do classificador trivial em 4 dos 5 campos** e
só ganha em dor (precisão 49% × 32%, discriminação 8/8 × 1/8). O valor dele está inteiro na
EXTRAÇÃO; a camada de classificação em cima é pior que constante (D-052, D-057).

**O Extractor com LLM (opção C: heurística gera candidato, LLM julga) foi medido e EMPATOU.**
D-055 exigia precisão ≥ 64% (49% + 0,15); a faixa em 3 execuções é **50–62%** — nem o melhor caso
alcança. O juiz varia entre execuções, e isso é argumento a mais contra pô-lo numa demo ao vivo. `USAR_JUIZ_LLM = False` é resultado de medição,
não esquecimento — liga com `--juiz`. O achado que vale mais que o número: **enumerar modos de
falha no prompt ensinou o 8b a recitá-los** — a primeira versão fez 22% de precisão e devolvia a
regra do prompt como justificativa (D-056).

**Correção do diagnóstico da dívida nº 6:** a afirmação *"o Extractor produz o mesmo conjunto de
dores para toda startup"* está **refutada** — sobre 8 fixtures diversas ele produz 8 conjuntos
distintos. Era artefato de uma base com 3 startups, todas de saúde. O que sobrevive é o outro
lado: precisão de 49%, e são as dores ERRADAS que poluem a consulta (D-052).

**Achado aberto, não pago:** o filtro do Inception exclui por **menção**, não por identidade. A
Axenya (prospect prioritário) é recusada por *"Integramos consultoria, dados e operação clínica"*
e a Freedom por um **parceiro** ser *"auditoria, consultoria e tributos"*. Fronteira de palavra não
resolve — é julgamento de sujeito. Ver D-052, achado 3.

**Base de startups (M3, parcial):** **8 startups** em `data/seed/*.yaml`, 24 documentos, todas as
`url_fonte` verificadas. Não é a M3 (30-50) — é o subconjunto que serve de gabarito aos agentes.

**Base de conhecimento NVIDIA (M2):** 16 tecnologias em `data/nvidia/fontes.yaml`, 177 chunks
estruturais + 204 de controle em `chunks_nvidia`, gabarito de **24 perguntas (19 com resposta,
5 sem)** em `data/avaliacao/gabarito.yaml`. **Os 9 passos do pipeline do TAPI estão fechados.**

Medido em **25/08, na stack pós-EOL** (D-046). Os números das sessões 02/03 foram produzidos por
dois modelos que não existem mais e **não são reproduzíveis** — estão preservados no `decisoes.md`
com a data, não aqui:

| motor | r@1 | r@3 | r@5 | e@1 | e@3 | e@5 |
|---|---|---|---|---|---|---|
| denso puro — linha de base | 95% | 100% | 100% | 79% | 79% | 84% |
| lexical (BM25) | 58% | 63% | 74% | 42% | 47% | 63% |
| híbrido (RRF K=10) | 95% | 100% | 100% | 79% | 79% | 79% |
| rerank sobre denso | 95% | 100% | 100% | 84% | 95% | 95% |
| **rerank sobre híbrida — produção** | **95%** | **100%** | **100%** | **84%** | **95%** | **100%** |

A troca de stack **melhorou** a recuperação (o denso puro sozinho já faz os 95% de r@1 que antes
exigiam o reranker), e o reranking continua pagando no critério estrito: e@3 de 79% → 95%.

**O braço lexical passou a pagar, e por uma pergunta só.** Na stack antiga `rerank_denso` e
`rerank_hibrido` davam números idênticos; agora diferem em **e@5, 95% vs 100%**. O braço de
controle (`--truncar-pool`) mostra que o ganho vem do **pool maior**, não da fusão, e o
diagnóstico é a **q17**: a âncora (`Evaluator`) não é recuperada pelo braço denso de jeito nenhum
e entra só pelo BM25. É **1 pergunta em 19** e só em e@5 — o tamanho honesto está em D-037,
Atualização 2.

**Abstenção: nenhum limiar sobre score funciona** — nem a cosseno densa (margem −0,2251) nem o
logit do cross-encoder (**−11,0039**). Ela vive no passo 8, como campo estruturado da geração
(D-033, D-035, D-040). Acurácia medida em 3 execuções: **20–22 de 24** — é faixa, não número, e
**a assimetria "nunca alucina" está refutada**: a q23 inventou "60%" em 1 das 3 (D-040, Atualização 3).

**`json_schema` vs `function_calling`, agora com n=5** (D-047): 4/5 · 0/5 · 0/5. A decisão fica; o
argumento muda de *"o método impede a alucinação"* para *"reduz de 3/3 para 1/5"*.

**O `nvidia_rag` consulta o pipeline real**, com a linguagem literal da startup e não com um
rótulo de dor (D-043).

**Diferencial — EM REVISÃO desde 27/08, e a frase antiga tinha um fato falso.** Ela dizia
"embedding e reranking do NeMo Retriever no lugar do Cohere (pago)". **O Cohere tem trial key
gratuita** cobrindo Command, Embed e Rerank (1.000 chamadas/mês, Rerank a 10 req/min, vedada a uso
comercial — o que não se aplica a um processo seletivo). Ver D-065.

E o reranking do NeMo Retriever **não existe mais** (D-064): 18 sondagens de path × modelo, todas
404/410. Hoje o que resta de fato é o **embedding** rodando na stack NVIDIA.

A reformulação que D-046 já tinha proposto, e que sobrevive a tudo isto: *"o Diferencial não é usar
a stack NVIDIA; é ter medido a propriedade do fornecedor que ninguém mediu"* — três EOLs em três
meses, com data, e um projeto que continua rodando. **A decisão do passo 7 está em aberto.**

## Comandos

```bash
conda activate case-nvidia                 # Python 3.12.13

python scripts/smoke_nvidia.py             # valida as 3 capacidades da stack NVIDIA
psql -d case_nvidia -f scripts/init_db.sql # schema (idempotente)
python scripts/seed.py --verificar-urls    # semeia e confere que toda url_fonte resolve
python scripts/seed.py --so-validar        # valida as fixtures sem tocar no banco
python scripts/verificar_embedder.py       # Matryoshka e limite de entrada do embedder
python scripts/ingerir_nvidia.py --so-validar  # chunking sem tocar banco nem API
python scripts/ingerir_nvidia.py           # ingere as 16 tecnologias (upsert idempotente)
python scripts/reembedar.py --so-validar   # conta chunks e lotes sem tocar API nem banco
python scripts/reembedar.py                # re-embeda do BANCO quando o embedder mudar (D-046)
python scripts/verificar_reranker.py       # janela do reranker e curva de diluição (D-034)
python scripts/avaliar_rag.py --validar    # gabarito vs corpus, incl. PROVA de ausência
python scripts/avaliar_rag.py              # ablação nos defaults de PRODUÇÃO (D-044)
python scripts/avaliar_rag.py --truncar-pool   # braço de controle: trunca a união antes do rerank
python scripts/avaliar_rag.py --por-pergunta   # onde cada motor põe o documento esperado
python scripts/avaliar_rag.py --varredura      # grade de fusão — zero chamada de API
python scripts/avaliar_rag.py --geracao        # passo 8: acurácia de abstenção sobre as 24
python scripts/avaliar_agentes.py --validar    # régua dos agentes: gabarito, evidência literal, teto do casador
python scripts/avaliar_agentes.py --baseline   # a linha de base trivial, obrigatória na tabela
python scripts/avaliar_agentes.py              # extrator + classificador + validador (zero API)
python scripts/avaliar_agentes.py --exclusoes  # filtro do Inception: falso positivo E falso negativo
python scripts/avaliar_agentes.py --rubrica    # braço REPROVADO: rubrica em degraus do Classifier (D-060)
python scripts/avaliar_agentes.py --confianca-diagnostico  # braço REPROVADO: confiança da evidência do diagnóstico (D-059)
python scripts/avaliar_agentes.py --juiz       # LIGA o juiz com LLM do Extractor — ~52 chamadas
python scripts/avaliar_agentes.py --motor ponta-a-ponta   # inclui nvidia_rag: CUSTA API
# ATENÇÃO — QUEBRADOS desde o EOL de 27/08 (D-064), até o Bloco 0 da sessão 08 fechar:
#   `python -m src.graph` e `pytest` param no reranker (404); o passo 8 para no LLM (410).
#   O que continua rodando: TODA a régua (`avaliar_agentes.py`, zero API) e 52 dos 53 testes.
python -m src.graph "sua consulta aqui"    # roda o pipeline ponta a ponta (thread novo por run)
python -m src.graph --thread <id> "..."    # retoma um run pelo thread_id que o CLI imprime
python scripts/diagramas.py                # regenera os .mmd a partir do grafo compilado
pytest -q                                  # 53 testes — exigem Postgres e a API (o grafo roda de verdade)
python scripts/coletar.py <url>            # auxiliar de curadoria: texto real de uma página
```

Para quem for avaliar sem Postgres local: `docker compose up -d` (porta 5433) e ajustar
`DATABASE_URL` no `.env`.

## Convenções

- **Um agente por módulo** em `src/agents/`, cada um exportando `node(state) -> dict`
- **Dois estados**: `EstadoRadar` (grafo pai) e `EstadoAnalise` (subgrafo). Ver `src/state.py`
- **Nada é afirmado sem `list[Evidencia]`** — `Afirmacao` é a unidade que os agentes produzem
- **Passo do pipeline RAG = módulo em `src/rag/`**: `limpeza` (2), `chunking` (3), `busca` (6a
  denso), `lexical` (6a léxico), `fusao` (6b), `rerank` (7), `geracao` (8). `pipeline.py` **não é
  um passo** — é a composição, e existe para evitar ciclo de import. `responder()` é a porta de
  entrada do RAG para o resto do sistema
- **`Passagem` é interno ao RAG, `CitacaoRAG` é o contrato com os agentes** (D-041). A conversão
  acontece em `para_citacao`, na borda
- **Todo acesso a LLM passa por `src/llm.py`** — e sempre com `method="json_schema"` (D-040)
- **Fixtures do seed em `data/seed/*.yaml`**, uma startup por arquivo. `perfil_alvo` é anotação
  de curadoria e **não entra no banco**
- **Provedor de LLM/embedding/rerank só via `src/config.py`** — nenhum agente conhece a NVIDIA

## Estrutura e índice

`contexto/` é **referência estável** sobre o case — só muda se um fato mudar.
`projeto/` é **vivo** — atualizado conforme o trabalho anda.

| Arquivo | Abrir quando |
|---|---|
| `contexto/01-tapi.md` | precisar do requisito exato: schema das tabelas, os 7 campos do output, pipeline RAG de 9 passos, regras do vídeo |
| `contexto/02-rubrica-ai-native.md` | for implementar o Extractor, o Classifier ou o Evidence Validator — é a rubrica que o TAPI não fornece |
| `contexto/03-stack-nvidia.md` | for montar a base de conhecimento ou o motor de recomendação |
| `contexto/04-ecossistema-br.md` | for popular a base de startups ou precisar de `url_fonte` legítimo |
| `contexto/05-achados-e-decisoes.md` | antes de decidir stack, ou se algo do TAPI parecer desatualizado |
| `projeto/plano.md` | no início de qualquer sessão — sequência dos 18 dias, marcos e riscos |
| `projeto/sessao-NN.md` | pauta executável da sessão corrente; abre com o fechamento da anterior |
| `projeto/sessao-05.md` | o EOL de 25/08, o code review e os 3 achados de agente **não pagos** — abrir antes de tocar na M4 |
| `projeto/sessao-06.md` | a régua dos agentes, o Extractor medido e o empate de D-055 — abrir antes de mexer no Classifier |
| `projeto/sessao-07.md` | **o terceiro EOL, as duas reprovações do Bloco 1 e o teto que faltava — abrir ANTES de qualquer coisa** |
| `scripts/avaliar_agentes.py` | a régua dos agentes: o que se conta, como o ambíguo é registrado, e por que a linha trivial existe |
| `data/avaliacao/exclusoes.yaml` | a régua do filtro do Inception: pares mínimos, falso positivo E falso negativo medidos separados (D-061) |
| `data/nvidia/fontes.yaml` | manifesto curado das 16 fontes do RAG — de onde busca vs. o que cita |
| `data/avaliacao/gabarito.yaml` | as 20 perguntas com documento-fonte esperado; é a régua do RAG |
| `projeto/decisoes.md` | **sempre que uma decisão for tomada** — escrever na hora |
| `projeto/conceitos.md` | antes de cada sessão: os 10 conceitos de IA que sustentam o núcleo e o vídeo, com o que estudar de cada um |
| `projeto/guia-de-trabalho.md` | método de trabalho e manutenção desta documentação |

`TAPI Processo Seletivo.md` é a fonte original — não editar.

## Regra permanente

Toda decisão técnica tomada nesta sessão vai para `projeto/decisoes.md` **no momento em que é
tomada**, com a alternativa descartada e o motivo. Esse arquivo é simultaneamente o material de
defesa do eliminatório nº 4, o roteiro do vídeo (peso 20) e a seção de arquitetura do README
(peso 10). Reconstituir isso depois é impossível.

---
*Contexto levantado em 21-22/08/2026 a partir do TAPI e das ~40 fontes que ele lista.*
