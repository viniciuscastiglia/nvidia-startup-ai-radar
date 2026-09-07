# NVIDIA Startup AI Radar

Plataforma **multi-agente** que recebe uma consulta em linguagem natural, recupera startups
brasileiras de uma base pré-populada, diagnostica a **maturidade AI-native** de cada uma a partir
de texto não estruturado, consulta uma **base RAG de tecnologias NVIDIA** e gera um **briefing
executivo** para apoiar a captação de startups para o **NVIDIA Inception**.

> Projeto do Processo Seletivo do **Inteli Academy** (2026), a partir do TAPI do case desenvolvido
> pela liga em parceria com a NVIDIA. Implementação independente.

---

## O problema

Os grandes laboratórios de IA — OpenAI, Anthropic, Google DeepMind, Meta — deixaram de ser apenas
fornecedores de modelos fundacionais e subiram na cadeia de valor: hoje entregam agentes, busca,
voz, código, automação de workflows e produtos finais.

Isso ameaça diretamente startups posicionadas apenas como **wrappers de LLM** — quem só conecta
uma API a uma interface, sem dado proprietário, sem workflow profundo e sem otimização técnica,
pode ser substituído por funcionalidade nativa dos próprios labs.

A saída para essas empresas é evoluir para **AI-native services**: vender resultado operacional,
não ferramenta. E é exatamente nessa transição que a NVIDIA tem argumento — founders começam com
APIs externas pela simplicidade e, ao crescer, batem em custo, latência, escalabilidade,
governança, privacidade, avaliação, observabilidade e dependência de fornecedor.

**Pergunta norteadora:** como a NVIDIA pode identificar, atrair e nutrir startups brasileiras
AI-native nesse contexto?

## O que o sistema faz

A partir de uma consulta em português, o sistema traduz a consulta em critérios de busca **e numa
estratégia de análise**, recupera empresas e documentos públicos, extrai um perfil estruturado do
texto bruto, classifica a maturidade (**AI-native** / **AI-enabled** / **non-AI**), valida se cada
afirmação tem evidência rastreável, checa a elegibilidade para o Inception, consulta a base RAG de
tecnologias NVIDIA com busca híbrida e reranking, e monta um briefing com justificativa técnica,
justificativa de negócio, prioridade, complexidade, próxima ação e as fontes de tudo.

**Toda conclusão do sistema aponta para o documento que a sustenta.** `Afirmacao` não existe sem
`list[Evidencia]` — rastreabilidade é propriedade do tipo, não disciplina do programador.

Três coisas que valem ser vistas rodando:

- **O sistema recusa recomendar.** O filtro do Inception exclui consultoria, capital aberto,
  cripto e empresas com mais de 10 anos — com a frase do documento que provou a exclusão. E ele
  separa *"a base prova que é consultoria"* de *"a base não prova que tem developer"*: só o
  primeiro exclui.
- **O RAG recusa responder o que não sabe.** Acurácia de abstenção de **23/24** sobre um gabarito
  de 24 perguntas, das quais 5 não têm resposta no corpus. Quando os trechos falam do assunto mas
  não contêm o fato, ele diz o que faltou em vez de inventar.
- **O reranking mostra o que fez.** A tela põe lado a lado a ordem da busca híbrida e a do
  cross-encoder para a mesma consulta, com o deslocamento de cada passagem.

## Arquitetura

```
Consulta do usuário
  → Query Planner Agent       NL → critérios de busca + estratégia de análise
  → Retriever Agent           seleciona empresas e documentos na base (SQL + tsvector)
  → ┌─ subgrafo de análise, um fan-out por empresa (Send) ────────────────┐
    │  Extractor Agent          texto bruto → perfil estruturado          │
    │  Startup Classifier       AI-native | AI-enabled | non-AI + stack   │
    │  Evidence Validator       as afirmações têm fonte suficiente?       │
    │  Elegibilidade            filtro do NVIDIA Inception                │
    │  NVIDIA RAG Agent         busca híbrida + reranking na base NVIDIA  │
    │  Recommendation Agent     cruza perfil × tecnologias                │
    └──────────────────────────────────────────────────────────────────────┘
  → Briefing Agent            relatório final (defer=True: só depois de todas)
  → Interface web             FastAPI + SSE, com o run transmitido nó a nó
```

Orquestração em **LangGraph**, e não numa cadeia de prompts: a topologia usa `Send` (uma empresa
por chamada), `defer=True` (o briefing só roda quando todas as branches terminam), `retry_policy`
(falha transitória de provedor não derruba a análise) e `error_handler` por nó (a etapa que falha
registra o erro e **preserva** o que as anteriores produziram). Uma chain usaria zero disso.

O **pipeline de RAG tem os 9 passos** que o TAPI especifica, um módulo por passo em `src/rag/`.
O passo 8 — geração com citação e abstenção — é acessível pela interface, em `POST /api/perguntar`.

## Stack

| Camada | Escolha | Decisão |
|---|---|---|
| Orquestração multi-agente | LangGraph — subgrafo + fan-out por `Send` | D-007 |
| LLM dos agentes | `nvidia/nemotron-3.5-lightning-30b-a3b` (1 vivo de 10 sondados) | D-079 |
| Embeddings | `nvidia/llama-nemotron-embed-vl-1b-v2`, `dimensions=1024` | D-014, D-046 |
| Reranking | Cohere `rerank-v3.5` — provedor por env var | D-068 |
| Dados estruturados | PostgreSQL 17 | D-006 |
| Busca vetorial | pgvector, no mesmo Postgres | D-016 |
| Busca lexical | `bm25s` em processo para o RAG · `tsvector` para startups | D-016 |
| Fusão | RRF (`K=10`), com soma ponderada como braço de controle medido | D-037 |
| Saída estruturada | `with_structured_output(..., method="json_schema")` | D-040 |
| Interface | FastAPI + uvicorn, front à mão, run ao vivo por SSE | D-107 |

> **O provedor de LLM, embedding e rerank fica atrás de `src/config.py`** — nenhum agente conhece
> a NVIDIA. Isso não é abstração gratuita: o catálogo de preview do `build.nvidia.com` aposentou
> modelos usados por este projeto **quatro vezes em quatro meses**, sempre com HTTP 410 e sem
> aviso prévio. `python scripts/smoke_nvidia.py` valida as três capacidades em 4 segundos, e é a
> primeira coisa a rodar quando algo parecer quebrado.

## Como rodar

**Pré-requisitos:** Python 3.12, e Postgres 17 (local ou pelo Docker abaixo).

```bash
# 1. ambiente
conda env create -f environment.yml && conda activate case-nvidia
#    sem conda: python3.12 -m venv .venv && source .venv/bin/activate
#               && pip install -r requirements.txt

# 2. credenciais
cp .env.example .env         # e preencha NVIDIA_API_KEY e COHERE_API_KEY
#    NVIDIA_API_KEY  -> build.nvidia.com, créditos grátis
#    COHERE_API_KEY  -> dashboard.cohere.com/api-keys, trial gratuita de 1.000 chamadas/mês

# 3. banco — escolha UM dos dois caminhos
#    (a) Postgres local:
createdb case_nvidia
psql -d case_nvidia -f scripts/init_db.sql
#    (b) Docker (sobe na porta 5433 e roda o schema sozinho):
docker compose up -d
#        e no .env:  DATABASE_URL=postgresql://postgres:postgres@localhost:5433/case_nvidia

# 4. popular
python scripts/seed.py                  # 30 startups, 93 documentos
python scripts/ingerir_nvidia.py        # 16 tecnologias -> 377 chunks, do cache versionado

# 5. rodar
python -m src.web                       # interface em http://127.0.0.1:8000
python -m src.graph "fintechs brasileiras usando IA"    # ou pela linha de comando
```

**Sem chave de rerank o projeto roda**: `RERANK_PROVEDOR=nenhum` tira o passo 7 do caminho e a
busca híbrida sozinha faz 95% de recall@1. Use isso para desenvolver — a suíte passa em 7 s em vez
de 150-460 s. **Mas não julgue as recomendações assim**: quem decide qual tecnologia a empresa
recebe é o reranker (D-097). `COHERE_REQ_POR_MIN=10` é o teto da trial, e ele importa: o 429 chega
na 4ª chamada sequencial.

**A base de conhecimento NVIDIA é versionada.** `data/nvidia/cache/` traz as 16 páginas como elas
estavam em 06/09/2026, então a ingestão **não depende da rede** e o corpus de quem clona é o corpus
medido. `--refetch` re-baixa e imprime o que mudou.

### Verificar que está tudo de pé

```bash
python scripts/smoke_nvidia.py            # as 3 capacidades da stack, em 4 s
RERANK_PROVEDOR=nenhum pytest -q          # 128 testes
python scripts/avaliar_rag.py             # a régua do RAG: ablação dos 5 motores
python scripts/avaliar_agentes.py         # a régua dos agentes, com a linha de base trivial
```

## O que está medido, e onde

Este projeto mede o que afirma, e registra **também o que reprovou**. Nenhum número vive neste
README — eles envelhecem, e cada um tem um comando que o reproduz:

| régua | comando |
|---|---|
| ablação do RAG (recall@k, evidência@k, os 5 motores) | `python scripts/avaliar_rag.py` |
| abstenção do passo 8, sobre 24 perguntas (5 sem resposta) | `python scripts/avaliar_rag.py --geracao` |
| extrator + classificador + validador, contra 8 fixtures com gabarito | `python scripts/avaliar_agentes.py` |
| **a linha de base trivial**, obrigatória em toda tabela de agente | `python scripts/avaliar_agentes.py --baseline` |
| filtro do Inception — falso positivo **e** falso negativo, nunca somados | `python scripts/avaliar_agentes.py --exclusoes` |
| relevância da recomendação: as 7 regras de exemplo do TAPI | `python scripts/avaliar_agentes.py --regras-tapi` |
| o veredito de elegibilidade das 30, numa tabela para LER | `python scripts/varrer_elegibilidade.py` |

Três disciplinas que valem mais que os números:

1. **A linha de base trivial é obrigatória.** Sem ela, "49% de precisão" parece bom em vez de
   "17 pontos acima de emitir tudo". Em um dos critérios o motor **perde** da linha trivial, e o
   número está registrado com a causa junto em vez de escondido.
2. **O critério é fixado ANTES de medir.** Várias hipóteses deste projeto foram **reprovadas** por
   essa regra — e ficaram registradas como reprovadas, com o comando que as derruba.
3. **Medir não é promover.** Registrar um resultado e mudar produção são dois atos separados.

## Estrutura do repositório

```
.
├── src/
│   ├── graph.py                 topologia LangGraph: grafo pai + subgrafo + fan-out
│   ├── state.py                 os dois estados e os tipos de domínio (Afirmacao, Evidencia…)
│   ├── config.py                provedor de LLM/embedding/rerank — o isolamento que importa
│   ├── agents/                  um agente por módulo, cada um exportando `node(state) -> dict`
│   ├── rag/                     um módulo POR PASSO do pipeline: limpeza, chunking, busca,
│   │                            lexical, fusao, rerank, geracao (+ pipeline.py, a composição)
│   └── web/                     FastAPI + SSE, e o front em `estatico/`
├── scripts/                     ingestão, seed, e as RÉGUAS (avaliar_*, varrer_*, medir_*)
├── data/
│   ├── seed/                    30 startups, uma por arquivo YAML
│   ├── nvidia/                  manifesto das 16 fontes + o cache versionado delas
│   └── avaliacao/               os gabaritos: RAG, exclusões, justificativas, regras do TAPI
├── tests/                       128 testes
├── contexto/                    referência estável sobre o case (TAPI, rubrica, stack, fontes)
└── projeto/                     o log de decisões, o plano e a pauta corrente
```

## Decisões de arquitetura

**[`projeto/decisoes.md`](projeto/decisoes.md) é a parte deste repositório que vale mais a
leitura.** São 112 decisões técnicas, cada uma com **a alternativa que foi descartada e o motivo**
— porque decisão sem alternativa registrada não é revisável, e em seis meses ninguém lembra por
quê. Ele registra também o que **deu errado**: hipóteses reprovadas pela própria régua, defeitos
que só apareceram rodando o sistema, e ao menos uma auditoria cujos achados caíram na verificação.

- [`projeto/plano.md`](projeto/plano.md) — todo item aberto com destino: fazer, aceitar ou decidir
- [`projeto/sessao-atual.md`](projeto/sessao-atual.md) — a pauta corrente
- [`contexto/`](contexto/) — o levantamento que precedeu o código: requisitos do TAPI, a rubrica
  AI-native que o TAPI não fornece, as 16 tecnologias NVIDIA e o ecossistema brasileiro

## Créditos

Case original desenvolvido pelos membros do **Inteli Academy** em parceria com a **NVIDIA**.
Esta é uma implementação independente feita para o processo seletivo da liga.
