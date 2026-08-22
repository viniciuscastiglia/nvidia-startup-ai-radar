# Sessão 01 — Decisões de stack e fatia vertical

**Objetivo:** sair da sessão com o pipeline inteiro executando ponta a ponta com 5 startups,
mesmo que cada agente ainda seja um stub burro.

**Por que essa ordem:** o eliminatório nº 3 do barema é *"projeto que não executa"*. Ter algo
end-to-end rodando no dia 1 mata esse risco de vez. Além disso, o formato do estado do grafo só
se revela errado quando os 8 nós tentam usá-lo — descobrir isso agora custa uma hora; descobrir
no dia 05/09 custa o projeto.

**Duração estimada:** 4 a 5 horas. Pode ser quebrada em duas sessões no corte do Bloco 3.

**Não fazer nesta sessão:** lógica de verdade em qualquer agente, interface, base grande de
startups, ingestão do RAG. Tudo isso vem depois e depende das decisões daqui.

---

## Bloco 0 — Ambiente (~15 min)

- [ ] Criar o ambiente Python **3.12** (o `python3` do sistema é 3.14.6, novo demais — várias
      libs do ecossistema ainda não têm wheel compilado):
      ```bash
      conda create -n case-nvidia python=3.12 -y
      conda activate case-nvidia
      ```
- [ ] Instalar o núcleo: `langgraph`, `langchain-core`, `psycopg[binary]`, `python-dotenv`, `pydantic`
- [ ] `pip freeze > requirements.txt` (ou usar `pyproject.toml` — decidir e registrar)
- [ ] Criar `.env.example` com os nomes das variáveis, sem valores

> `.gitignore` já bloqueia `.env`. **Nunca commitar chave de API.**

## Bloco 1 — Validar o build.nvidia.com (~30 min) — **bloqueante**

Esta é a dependência que pode invalidar as decisões do Bloco 2. Resolver antes de tudo.

- [ ] Criar conta em https://build.nvidia.com e gerar API key
- [ ] Guardar como `NVIDIA_API_KEY` no `.env`
- [ ] Três smoke tests, um por capacidade que o projeto vai usar:
  - [ ] **chat completion** — endpoint OpenAI-compatible, trocando só o `base_url`
  - [ ] **embedding** — `llama-3.2-nv-embedqa-1b-v2`, testar com **texto em português**
  - [ ] **reranking** — `llama-3.2-nv-rerankqa-1b-v2`, endpoint `/v1/ranking`, com query e 3 passagens
- [ ] Anotar: latência de cada chamada e quanto de crédito foi consumido
- [ ] **Decisão:** adotar a stack NVIDIA ou acionar fallback?

**Critério de decisão:** o pipeline tem 8 agentes e vai rodar dezenas de vezes por dia em
desenvolvimento. Se o crédito não sustentar isso, adotar NVIDIA só para embedding e reranking
(onde ele é diferencial de verdade) e usar outro provedor para os LLMs dos agentes. Em qualquer
caso, deixar o provedor configurável por variável de ambiente desde o início.

## Bloco 2 — Fechar as decisões de stack (~45 min)

Cada uma vai para `projeto/decisoes.md` **com a alternativa descartada e o motivo**.

- [ ] **LLM dos agentes** — depende do Bloco 1
- [ ] **Embeddings** — `llama-3.2-nv-embedqa-1b-v2` é multilíngue (26 idiomas, inclui português),
      com dimensão Matryoshka configurável. Decidir também **qual dimensão** e por quê
- [ ] **Reranker** — NeMo Retriever (grátis) vs Cohere Rerank (o que o TAPI sugere, pago) vs
      cross-encoder local. Ver `contexto/05-achados-e-decisoes.md` §4.3
- [ ] **Banco vetorial** — Qdrant vs pgvector. O critério real: o passo 6 do pipeline RAG exige
      **busca híbrida (vetorial + BM25)**. Qdrant tem suporte nativo melhor; pgvector elimina uma
      peça de infra já que o Postgres estará lá de qualquer jeito. Decidir olhando para como o
      BM25 vai ser implementado, não em abstrato
- [ ] **Gerenciamento de dependências** — pip + requirements vs uv vs poetry

## Bloco 3 — Desenhar o estado do LangGraph (~60 min) — **a decisão mais consequente**

O estado define o que cada agente enxerga e o que produz. Errar aqui custa refatoração dos 8 nós.

- [ ] Modelar o estado (Pydantic ou TypedDict) respondendo:
  - o que o **Query Planner** produz que o **Retriever** consome?
  - o **Extractor** escreve um perfil estruturado — qual o schema dele?
  - **onde ficam as evidências?** A rastreabilidade é requisito duro do TAPI: toda conclusão
    aponta para um documento. Isso precisa estar no estado desde o primeiro commit, não ser
    remendado depois
  - o **Evidence Validator** rejeita ou apenas anota confiança? (ver `contexto/02` §6)
- [ ] **Decidir a topologia:** uma consulta retorna N startups. O pipeline de análise roda uma vez
      por startup e depois agrega, ou processa todas juntas? Se for por startup, olhar a API
      `Send` do LangGraph para fan-out. Essa decisão muda o formato do estado inteiro
- [ ] Definir onde entra **checkpointing** (o TAPI cita checkpoints e retry como justificativa
      para LangGraph — usar isso de fato é o que separa nível 2 de nível 3 no critério 1)
- [ ] Registrar a decisão de topologia em `projeto/decisoes.md`

> Vale entrar em **plan mode** (Shift+Tab duas vezes) neste bloco.

## Bloco 4 — Postgres, schema e seed (~60 min)

- [ ] Subir o Postgres (já existe Postgres.app na máquina; alternativa é docker-compose —
      decidir pensando em quem vai rodar o projeto para avaliar)
- [ ] Criar o schema conforme `contexto/01-tapi.md`: tabelas `startups` e `documentos`
- [ ] Script de seed versionado (não inserir dado na mão sem script — o avaliador precisa
      conseguir reproduzir)
- [ ] **Semear 5 startups × 3 documentos**, escolhidas de propósito para exercitar os agentes:

  | # | Perfil | Para exercitar |
  |---|---|---|
  | 1 | claramente **AI-native** — vende resultado, tem vaga técnica de peso | o caminho feliz |
  | 2 | **AI-enabled / wrapper** — marketing de IA, vaga só de integração de API | a distinção central da rubrica |
  | 3 | **non-AI** | o caso negativo |
  | 4 | **inelegível ao Inception** — consultoria de IA, ou cripto, ou capital aberto | a regra de negócio das exclusões (`contexto/03` §2) |
  | 5 | **evidência fraca** — só um documento útil, ou documento antigo | o Evidence Validator |

  Fonte para escolher: o hub de AI do Cubo Itaú, mais os outros hubs para os casos não-IA.
  Ver `contexto/04-ecossistema-br.md` §3.

- [ ] **`url_fonte` tem que ser real e resolver.** O avaliador checa isso em segundos.
      Documento com URL inventada derruba a credibilidade do projeto inteiro

## Bloco 5 — Grafo esqueleto rodando (~45 min)

- [ ] Criar os 8 nós como stubs que só leem e escrevem o estado
- [ ] Ligar as arestas conforme o fluxo do TAPI
- [ ] Rodar de ponta a ponta com uma consulta real (ex.: *"startups brasileiras de saúde usando IA"*)
- [ ] Confirmar que o estado chega íntegro no Briefing Agent
- [ ] Exportar o diagrama do grafo (`graph.get_graph().draw_mermaid_png()`) — vai servir no
      README e no vídeo

## Bloco 6 — Fechar a sessão (~15 min)

- [ ] Atualizar `projeto/decisoes.md` com tudo que foi decidido
- [ ] Adicionar a seção **Comandos** no `CLAUDE.md` (subir o banco, rodar o grafo, seed)
- [ ] Commits com o *porquê* na mensagem
- [ ] Anotar o que ficou pendente para a sessão 02

---

## Critérios de pronto

A sessão só está concluída quando:

1. `python -m src.graph` (ou equivalente) roda sem erro e imprime o estado final
2. As 5 startups e os 15 documentos estão no Postgres, via script reproduzível
3. Os três smoke tests do build.nvidia.com passaram, com latência anotada
4. `projeto/decisoes.md` tem pelo menos 5 decisões registradas com alternativa e motivo
5. Tudo commitado

## Perguntas para me fazer durante a sessão

- *"Me explica as opções de X e recomenda uma"* — antes de qualquer implementação
- *"Por que não Y?"* — em toda escolha; a resposta é o que o avaliador vai perguntar
- No fim: *"me faz 5 perguntas difíceis sobre o estado do grafo que a gente acabou de desenhar"*
