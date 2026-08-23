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
| LLM dos agentes | `meta/llama-3.1-8b-instruct` via build.nvidia.com | D-012 |
| Embeddings | `nvidia/llama-nemotron-embed-1b-v2`, **`dimensions=1024`** | D-014 |
| Reranking | `nvidia/llama-nemotron-rerank-1b-v2` (text-only, não o VL) | D-015 |
| Vetores | pgvector no mesmo Postgres | D-016 |
| Busca lexical | `bm25s` em processo para o RAG · `tsvector` para documentos de startup | D-016 |
| Topologia | subgrafo de análise + fan-out por `Send` | D-007 |
| Chunking | estrutural por seção + breadcrumb prefixado · janela fixa como controle | D-025, D-027 |

> **Atenção — os modelos que o TAPI cita estão mortos.** `llama-3.2-nv-embedqa-1b-v2` e
> `llama-3.2-nv-rerankqa-1b-v2` respondem **HTTP 410 Gone** desde 18/05/2026. Nunca usar esses
> nomes. Ver D-013 e `contexto/03` §3.

**Em aberto:** framework de frontend (P-06) e quantas startups entram na base final.

**Base de conhecimento NVIDIA (M2, sessão 02):** 16 tecnologias em `data/nvidia/fontes.yaml`,
177 chunks estruturais + 204 de controle em `chunks_nvidia`, gabarito de 20 perguntas em
`data/avaliacao/gabarito.yaml`. Linha de base medida: **recall@3 = 100% estrutural contra 84%
da janela fixa** (D-032). A abstenção **não** sai de limiar sobre score denso (D-033).

**Diferencial:** o RAG roda inteiro na própria stack NVIDIA — embedding e reranking do NeMo
Retriever no lugar do Cohere (pago). Dá o argumento "usei a stack que o sistema recomenda".

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
python scripts/avaliar_rag.py --validar    # confere o gabarito CONTRA o corpus
python scripts/avaliar_rag.py -k 3         # recall@k: estrutural vs braço de controle
python -m src.graph "sua consulta aqui"    # roda o pipeline ponta a ponta (thread novo por run)
python -m src.graph --thread <id> "..."    # retoma um run pelo thread_id que o CLI imprime
python scripts/diagramas.py                # regenera os .mmd a partir do grafo compilado
pytest -q                                  # 29 testes
python scripts/coletar.py <url>            # auxiliar de curadoria: texto real de uma página
```

Para quem for avaliar sem Postgres local: `docker compose up -d` (porta 5433) e ajustar
`DATABASE_URL` no `.env`.

## Convenções

- **Um agente por módulo** em `src/agents/`, cada um exportando `node(state) -> dict`
- **Dois estados**: `EstadoRadar` (grafo pai) e `EstadoAnalise` (subgrafo). Ver `src/state.py`
- **Nada é afirmado sem `list[Evidencia]`** — `Afirmacao` é a unidade que os agentes produzem
- **Passo do pipeline RAG = módulo em `src/rag/`**: `limpeza` (passo 2), `chunking` (3), `busca` (6)
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
