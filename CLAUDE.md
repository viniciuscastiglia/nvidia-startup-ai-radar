# NVIDIA Startup AI Radar — Processo Seletivo Inteli Academy

> Carregado automaticamente em toda sessão do Claude Code aberta nesta pasta.
> É o **contexto mínimo e durável** — não status, não diário de bordo. O que aconteceu está em
> `projeto/decisoes.md`; o que está aberto, em `projeto/sessao-atual.md`.

## O que é

Plataforma **multi-agente** que recebe uma consulta em linguagem natural, recupera startups
brasileiras de uma base pré-populada, diagnostica a **maturidade AI-native** delas a partir de
texto não estruturado, consulta uma **base RAG de tecnologias NVIDIA** e gera um **briefing
executivo** para o gerente de Startups & VCs da NVIDIA Brasil captar startups para o
**NVIDIA Inception**.

**Pergunta norteadora:** como a NVIDIA pode identificar, atrair e nutrir startups brasileiras
AI-native num contexto em que os grandes labs de IA ameaçam startups que dependem apenas de
wrappers de LLM?

**Entrega:** implementação própria, seguindo o TAPI em `TAPI Processo Seletivo.md`.
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
- Núcleo de IA (1+2+3) = **60** · Comunicação (vídeo + repo/docs) = **30** · Produto (interface +
  diferencial) = **10**
- O **vídeo vale o mesmo que o sistema multi-agente inteiro** e 4x a interface
- A **interface web é o Entregável 4 mas vale 5 pontos** — não investir uma semana nela
- Nível 2 em tudo = 50/100. Nível 3 em tudo = 75. A diferenciação está em subir de "cumpre o
  requisito" para "decisões técnicas conscientes"

## Critérios eliminatórios

1. Entrega fora do prazo sem alinhamento prévio
2. Ausência do vídeo de apresentação
3. Projeto que não executa **e** cujo vídeo não demonstra funcionamento real
4. **Código integralmente gerado sem compreensão** — o candidato precisa explicar as decisões de
   arquitetura do próprio projeto
5. Plágio de outro projeto

O TAPI é explícito: *"O uso de IA como ferramenta de desenvolvimento é permitido e esperado.
O que se avalia é a capacidade de tomar e defender decisões técnicas."*

## Como trabalhar neste projeto

O eliminatório nº 4 define o modo de trabalho. Ao implementar qualquer coisa:

- **Explique a decisão antes de escrever o código.** Por que LangGraph e não uma chain simples,
  por que esse chunking, por que reranking cross-encoder e não bi-encoder, por que esse estado no
  grafo. O Vinícius precisa defender isso numa banca.
- **Ofereça a alternativa que foi descartada e o motivo.** É isso que vira resposta pronta quando
  o avaliador perguntar "por que não X?".
- **Nada de código mágico.** Se uma escolha só se justifica por conveniência, diga isso.
- **Fixe o critério ANTES de medir.** É a disciplina que fez D-055, D-058 e D-072 valerem. Uma
  medição cujo alvo é decidido depois do placar não é medição.
- **Medir não é promover.** Registrar um resultado e mudar produção são dois atos.
- Português nas explicações e na documentação.
- **Subagentes: evitar neste projeto.** Eles começam sem contexto e devolvem resultado pronto, que
  é o oposto do eliminatório nº 4. Ver `projeto/guia-de-trabalho.md`.

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

**Definido pelo TAPI:** LangGraph (obrigatório). PostgreSQL, Qdrant, BM25 e Cohere Rerank — todos
*recomendados*, não obrigatórios. Frontend livre.

| Camada | Escolha | Decisão |
|---|---|---|
| LLM dos agentes | `nvidia/nemotron-3-nano-30b-a3b` — 1 utilizável de 10 sondados | D-067 |
| Embeddings | `nvidia/llama-nemotron-embed-vl-1b-v2`, `dimensions=1024` | D-014, D-046 |
| Reranking | Cohere `rerank-v3.5` (provedor via env: `cohere`/`nvidia`/`nenhum`) | D-068 |
| Vetores | pgvector no mesmo Postgres | D-016 |
| Busca lexical | `bm25s` em processo para o RAG · `tsvector` para documentos de startup | D-016 |
| Topologia | subgrafo de análise + fan-out por `Send` | D-007 |
| Chunking | estrutural por seção + breadcrumb prefixado · janela fixa como controle | D-025, D-027 |
| BM25 | método `lucene`, `k1=1.2`, `b=0.75`, tokenizador que dobra acento | D-036 |
| Fusão | RRF (`K=10`) de produção · soma ponderada como braço de controle medido | D-037 |
| Saída estruturada | `with_structured_output(..., method="json_schema")` via `src/llm.py` | D-040, D-069 |
| Schema que vai ao LLM | tipo **estreito** por chamada — docstring de schema é **prompt** | D-045 |
| Consulta do RAG | rótulo da dor + `dor.evidencias[*].trecho` (a fala da startup) | D-043 |

> ### O risco que define este projeto: o catálogo de preview é perecível
>
> A stack de recuperação já morreu **três vezes em três meses** — 18/05, 25/08 e 27/08/2026, sempre
> com HTTP 410/404. Detalhe e datas em **D-013, D-046, D-064**. Consequências operacionais:
>
> - **`GET /v1/models` NÃO é prova de nada (D-070).** 9 dos 10 candidatos mortos estavam listados,
>   inclusive o que D-064 recomendou por nome. **Só chamada real conta:**
>   `python scripts/sondar_catalogo.py --structured`. O catálogo encolhe entre execuções.
> - **Env var não protege o embedder.** Trocar o modelo muda o espaço vetorial e invalida os 381
>   vetores — é `scripts/reembedar.py` mais re-medir a régua inteira (D-046).
> - **O teto da trial do Cohere é pior que a documentação:** o 429 chega na 4ª chamada sequencial,
>   `retry-after` vem ausente, recuperação de ~26 s. Por isso `src/rag/rerank.py` tem limitador
>   proativo e retry. **Para o vídeo: ~2-3 min só de rerank num run completo** — a cena é uma
>   consulta com `MAX_STARTUPS` baixo, não o run inteiro (D-068).
> - **O Diferencial não é "usar a stack NVIDIA"** — é ter medido uma propriedade do fornecedor que
>   ninguém mede, com instrumento versionado (D-070).

## O que está medido, e onde

Nenhum número vive aqui: números envelhecem e este arquivo é carregado em toda sessão.

| régua | onde | comando |
|---|---|---|
| ablação do RAG (r@k, e@k, os 5 motores) | **D-068** | `python scripts/avaliar_rag.py` |
| régua dos agentes (trivial × casador × juiz) | **D-072** | `python scripts/avaliar_agentes.py` |
| abstenção do passo 8 | **D-040** — *do modelo morto, ver P-15* | `--geracao` |
| filtro do Inception (falso positivo E negativo) | **D-071** | `--exclusoes` |

**A linha de base trivial é obrigatória em toda tabela de agente** (D-051) — é o `denso puro` deste
critério, e sem ela 49% de precisão parece bom em vez de "17 pontos acima de emitir tudo".

## Estado da base

- **8 startups** em `data/seed/*.yaml`, 24 documentos, `url_fonte` verificadas. **Não é a M3
  (30-50)** — é o subconjunto que serve de gabarito aos agentes (D-050, D-062).
- **16 tecnologias NVIDIA**, 177 chunks estruturais + 204 de controle, gabarito de **24 perguntas**
  (19 com resposta, 5 sem). **Os 9 passos do pipeline do TAPI estão fechados.**

## Comandos

```bash
conda activate case-nvidia                 # Python 3.12.13

python scripts/smoke_nvidia.py             # valida as 3 capacidades da stack — FALHA ALTO
python scripts/sondar_catalogo.py --structured --rerank   # o que está VIVO no catálogo (D-070)
psql -d case_nvidia -f scripts/init_db.sql # schema (idempotente)
python scripts/seed.py --verificar-urls    # semeia e confere que toda url_fonte resolve
python scripts/seed.py --so-validar        # valida as fixtures sem tocar no banco
python scripts/verificar_embedder.py       # Matryoshka e limite de entrada do embedder
python scripts/verificar_reranker.py       # janela do reranker e curva de diluição
python scripts/verificar_cohere.py --janela --throttle 15  # ordena? janela? quantas req/min?
python scripts/ingerir_nvidia.py --so-validar  # chunking sem tocar banco nem API
python scripts/ingerir_nvidia.py           # ingere as 16 tecnologias (upsert idempotente)
python scripts/reembedar.py --so-validar   # conta chunks e lotes sem tocar API nem banco
python scripts/reembedar.py                # re-embeda do BANCO quando o embedder mudar (D-046)

# RAG — a régua do critério 2
python scripts/avaliar_rag.py --validar    # gabarito vs corpus, incl. PROVA de ausência
python scripts/avaliar_rag.py              # ablação nos defaults de PRODUÇÃO (D-044)
python scripts/avaliar_rag.py --truncar-pool   # braço de controle: trunca a união antes do rerank
python scripts/avaliar_rag.py --por-pergunta   # onde cada motor põe o documento esperado
python scripts/avaliar_rag.py --varredura      # grade de fusão — zero chamada de API
python scripts/avaliar_rag.py --geracao        # passo 8: acurácia de abstenção sobre as 24
python scripts/avaliar_rag.py --rerank-provedor nenhum   # o passo 7 fora do caminho
python scripts/medir_saida_estruturada.py -n 5           # re-mede D-047

# Agentes — a régua dos critérios 1 e 3
python scripts/avaliar_agentes.py --validar    # gabarito, evidência literal, teto do casador
python scripts/avaliar_agentes.py --baseline   # a linha trivial, obrigatória na tabela
python scripts/avaliar_agentes.py              # extrator + classificador + validador (zero API)
python scripts/avaliar_agentes.py --exclusoes  # filtro do Inception: falso positivo E negativo
python scripts/avaliar_agentes.py --juiz       # LIGA o juiz do Extractor — ~52 chamadas
python scripts/avaliar_agentes.py --rubrica    # braço REPROVADO (D-060)
python scripts/avaliar_agentes.py --confianca-diagnostico  # braço REPROVADO (D-059)
python scripts/avaliar_agentes.py --motor ponta-a-ponta    # inclui nvidia_rag: CUSTA API

python -m src.graph "sua consulta aqui"    # roda o pipeline ponta a ponta (thread novo por run)
python -m src.graph --thread <id> "..."    # retoma um run pelo thread_id que o CLI imprime
python scripts/diagramas.py                # regenera os .mmd a partir do grafo compilado
pytest -q                                  # exigem Postgres e a API (o grafo roda de verdade)
python scripts/coletar.py <url>            # auxiliar de curadoria: texto real de uma página
```

Para avaliar sem Postgres local: `docker compose up -d` (porta 5433) e ajustar `DATABASE_URL`.

> **Antes de medir qualquer coisa:** limpe o `__pycache__`. Uma edição que preserva o tamanho do
> arquivo pode ser invisível para o Python, e a régua mede a versão anterior sem avisar (D-060).

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
- **Fixtures do seed em `data/seed/*.yaml`**, uma startup por arquivo. `perfil_alvo` e `gabarito`
  são anotação de curadoria e **não entram no banco**
- **Provedor de LLM/embedding/rerank só via `src/config.py`** — nenhum agente conhece a NVIDIA

## Estrutura e índice

`contexto/` é **referência estável** sobre o case — só muda se um fato mudar.
`projeto/` é **vivo**.

| Arquivo | Abrir quando |
|---|---|
| `projeto/sessao-atual.md` | **no início de qualquer sessão** — o que está aberto e as decisões pendentes |
| `projeto/decisoes.md` | **sempre que uma decisão for tomada** — escrever na hora. É o material de defesa, o roteiro do vídeo e a seção de arquitetura do README |
| `projeto/plano.md` | sequência dos 18 dias, marcos e riscos |
| `projeto/guia-de-trabalho.md` | método de trabalho e manutenção desta documentação |
| `contexto/01-tapi.md` | precisar do requisito exato: schema, os 7 campos do output, pipeline de 9 passos, regras do vídeo |
| `contexto/02-rubrica-ai-native.md` | for mexer no Extractor, no Classifier ou no Evidence Validator — é a rubrica que o TAPI não fornece |
| `contexto/03-stack-nvidia.md` | for mexer na base de conhecimento ou no motor de recomendação |
| `contexto/04-ecossistema-br.md` | for popular a base de startups ou precisar de `url_fonte` legítimo |
| `contexto/05-achados-e-decisoes.md` | achados do levantamento e o que ficou sem resposta |
| **[Anatomia do Radar](https://claude.ai/code/artifact/dc527bde-f149-49f8-87a5-3105197cc2e2)** | documento de estudo: os 9 agentes, os 9 passos e o que está medido |
| `scripts/avaliar_agentes.py` | a régua dos agentes: o que se conta e por que a linha trivial existe |
| `data/avaliacao/gabarito.yaml` | as 24 perguntas do RAG, com documento-fonte esperado |
| `data/avaliacao/exclusoes.yaml` | a régua do filtro do Inception, com os dois lados medidos separados |
| `data/nvidia/fontes.yaml` | manifesto curado das 16 fontes do RAG |

`TAPI Processo Seletivo.md` é a fonte original — não editar.

## Regra permanente

Toda decisão técnica vai para `projeto/decisoes.md` **no momento em que é tomada**, com a
alternativa descartada e o motivo. O log guarda a **decisão**, não o caderno de laboratório: um
número só fica se é verdade sobre o sistema que roda hoje; se o instrumento morreu, fica a
conclusão (D-073).

---
*Contexto levantado em 21-22/08/2026 a partir do TAPI e das ~40 fontes que ele lista.*
