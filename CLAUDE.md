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

## O que ordena o trabalho

Este sistema tem **um usuário real**: o gerente de Startups & VCs da NVIDIA Brasil, que precisa
decidir quais startups abordar e com qual argumento. E este repositório tem um **segundo leitor
real**: quem o abre para entender ou rodar — um colega, ou o próprio Vinícius daqui a seis meses.

> **A pergunta que ordena a fila: o que, hoje, faz este sistema falhar na mão de quem ia usar
> de verdade?**

Três regras saem daí:

1. **Não existe teto.** Uma parte do sistema estar boa nunca é razão para parar de melhorá-la. A
   razão para parar é sempre custo/benefício de engenharia — e ela vai escrita como decisão.
2. **A prioridade sai do defeito, não do peso.** O que ordena a fila é a gravidade do defeito para
   quem usa o sistema.
3. **Documenta-se para o leitor que não é você.** A alternativa descartada é registrada porque em
   seis meses ninguém lembra por quê — e porque decisão sem alternativa registrada não é revisável.

**Prazo é restrição; qualidade é o objetivo.** A escassez de tempo ordena o *quanto* se faz. Ela
nunca ordena o *quê* por contagem de pontos.

## Restrições da entrega

O case é avaliado por barema. A tabela de pesos mora em `contexto/01-tapi.md` — é registro da
especificação, e é lá que ela fica, porque peso de critério não é bom critério de priorização.
Aqui ficam as restrições duras, que são requisitos de verdade:

1. **Prazo:** 09/09/2026 às 23:59; fora dele só com alinhamento prévio
2. **O vídeo é obrigatório** — e a razão que importa é que um sistema que ninguém consegue ver não
   existe
3. **O projeto tem de executar**, e o vídeo tem de demonstrar funcionamento real
4. **Quem constrói precisa entender o que construiu.** Quem não entende cada peça não consegue
   evoluir, depurar nem defender o sistema
5. Autoria própria

O TAPI é explícito: *"O uso de IA como ferramenta de desenvolvimento é permitido e esperado.
O que se avalia é a capacidade de tomar e defender decisões técnicas."*

## Como trabalhar neste projeto

Quem não entende o que construiu não consegue evoluir nem depurar. Ao implementar qualquer coisa:

- **Explique a decisão antes de escrever o código.** Por que LangGraph e não uma chain simples,
  por que esse chunking, por que reranking cross-encoder e não bi-encoder, por que esse estado no
  grafo. Uma escolha sem razão articulada não é escolha — é acidente que ninguém consegue revisar.
- **Ofereça a alternativa que foi descartada e o motivo.** É o que torna a decisão reversível: sem
  ela, revisitar a escolha em duas semanas custa refazer a análise inteira.
- **Nada de código mágico.** Se uma escolha só se justifica por conveniência, diga isso.
- **Fixe o critério ANTES de medir.** É a disciplina que fez D-055, D-058 e D-072 valerem. Uma
  medição cujo alvo é decidido depois do placar não é medição.
- **Medir não é promover.** Registrar um resultado e mudar produção são dois atos.
- Português nas explicações e na documentação.
- **Subagentes: evitar neste projeto.** Eles começam sem contexto e devolvem resultado pronto —
  código que entra sem ninguém entender por quê é código que ninguém consegue evoluir depois.
  Ver `projeto/guia-de-trabalho.md`.
- **RODE O SISTEMA. Leitura de código não substitui execução (D-083).** Toda sessão que mexe em
  comportamento roda `python -m src.graph` **antes de fechar**, e olha a saída — não o traceback.
  Medido em 02/09: duas sessões de auditoria estática não acharam nenhum dos três defeitos que uma
  execução achou em uma hora — um bug que descartava a palavra "IA" da busca, entulho de página
  indexado, e a justificativa técnica citando a empresa errada. **Os três eram invisíveis no código
  e óbvios na saída.**
- **"Efeito no vídeo" NÃO é critério de decisão técnica (D-084).** O vídeo é restrição de entrega,
  como o prazo: restrição diz *quanto* se faz, nunca *o quê*. Uma razão justificada pelo vídeo
  **vence em 07/09** — e na arguição, *"não cabia nos 7 minutos"* é resposta fraca. A régua é
  sempre: **defeito para quem usa · latência que o usuário sente · robustez · reversibilidade.**
  É D-078 (o barema fora da função objetivo) com outra roupa — voltou em 5 dias por outra porta,
  e escondeu o argumento bom contra P-10(b), que era o fornecedor único.

## Arquitetura alvo (LangGraph — obrigatório pelo TAPI)

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
| LLM dos agentes | `nvidia/nemotron-3.5-lightning-30b-a3b` — 1 vivo de 10 sondados | D-079 |
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
> - **`GET /v1/models` é o catálogo GLOBAL, não o que a conta pode chamar (D-070, corrigido por
>   D-079).** Um `404` ali é quase sempre **entitlement**, não morte; morte tem assinatura própria —
>   **HTTP 410 com a data de EOL no corpo**. `sondar_catalogo.py` separa os três casos. E **ser modelo
>   próprio da NVIDIA é condição necessária, não suficiente**: terceiros deram 0 vivos em 12.
> - **NÃO EXISTE AVISO PRÉVIO (D-079).** Nem campo na listagem, nem header `Sunset`/`Deprecation`.
>   Só a chamada real informa, e informa depois. **Rodar `smoke_nvidia.py` antes de gravar o vídeo e
>   antes de entregar é a única defesa que existe** — são 4 segundos, e o quarto EOL passou 13 horas
>   despercebido por ninguém ter rodado.
> - **EXISTE UMA QUARTA ASSINATURA, E ELA NÃO É MORTE: `LENTO` (D-080).** O modelo responde HTTP
>   200 acima do relógio — mediana medida de **51 s**, faixa 17-88 s. As três assinaturas de D-079
>   descrevem só respostas que CHEGAM; um **timeout não é conclusão**. O smoke separa os casos e
>   imprime a conduta. **`LENTO` NÃO justifica trocar de modelo** — em 02/09, lê-lo como EOL teria
>   aberto uma migração desnecessária a 5 dias do vídeo.
> - **Env var não protege o embedder.** Trocar o modelo muda o espaço vetorial e invalida os 377
>   vetores — é `scripts/reembedar.py` mais re-medir a régua inteira (D-046).
> - **O PASSO 7 TEM FORNECEDOR ÚNICO: `RERANK_PROVEDOR=nvidia` NÃO É OPÇÃO DESDE MAIO (D-097).**
>   `src/config.py` oferece três provedores e um deles está morto **desde 2026-05-18** — é a morte
>   que **D-013 registrou no primeiro dia** e que trouxe o Cohere, não novidade. `410` com a data
>   no corpo; os `404` do mesmo teste são **entitlement**, não morte (D-070). Consequência prática:
>   **o Cohere é ponto único de falha.** Rode `smoke_nvidia.py` antes de gravar e de entregar.
> - **A COTA MENSAL DA TRIAL DO COHERE ACABOU EM 03/09 (D-093).** `429` com *"limited to 1000
>   API calls / month"* — **não é o teto por minuto, é o do mês**, e ele não recupera sozinho.
>   **`RERANK_PROVEDOR=nenhum` roda tudo** — grafo completo e `pytest` 81 passed **em 6,5 s**,
>   contra 150-460 s com o Cohere ligado. Use isso como **default de desenvolvimento**; o
>   Cohere entra só quando se quer medir o passo 7.
> - **MAS NÃO JULGUE RECOMENDAÇÃO COM O RERANK DESLIGADO (D-097).** Em 03/09 uma auditoria quase
>   registrou como defeito grave o *"NVIDIA Healthcare recomendado para uma agtech"*. Era artefato
>   de `RERANK_PROVEDOR=nenhum`: com o passo 7 ligado, a Solinftec recebe **NVIDIA Isaac**, e ela
>   fabrica robô agrícola. **O modo barato serve para desenvolver, nunca para avaliar o que o
>   gerente veria.**
> - **O teto da trial do Cohere é pior que a documentação:** o 429 chega na 4ª chamada sequencial,
>   `retry-after` vem ausente, recuperação de ~26 s. Por isso `src/rag/rerank.py` tem limitador
>   proativo e retry. **Para o vídeo: ~2-3 min só de rerank num run completo** — a cena é uma
>   consulta com `MAX_STARTUPS` baixo, não o run inteiro (D-068).
> - **O que este projeto sabe e quase ninguém sabe** não é "usamos a stack NVIDIA" — é a
>   volatilidade de catálogo do fornecedor, medida com instrumento versionado (D-070). Vale porque
>   muda decisão de arquitetura: é o que justifica o provedor isolado em `src/config.py`.

## O que está medido, e onde

Nenhum número vive aqui: números envelhecem e este arquivo é carregado em toda sessão.

| régua | onde | comando |
|---|---|---|
| ablação do RAG (r@k, e@k, os 5 motores) | **D-068** | `python scripts/avaliar_rag.py` |
| régua dos agentes (trivial × casador × juiz) | **D-072** | `python scripts/avaliar_agentes.py` |
| abstenção do passo 8 | **D-040** — re-medida em 02/09 no modelo atual | `--geracao` |
| filtro do Inception (falso positivo E negativo) | **D-085** | `--exclusoes` |
| `justificativa_tecnica`: seletor × os 150 primeiros | **D-086** | `--justificativas` |
| filtro do Inception, os 30 vereditos numa tabela | **D-094** | `varrer_elegibilidade.py` |
| classe das 30 + o custo de cada conserto na régua | **D-098, D-101** | `varrer_classes.py` |
| confiança do diagnóstico, os 4 braços | **D-098** | `medir_confianca.py` |

**A linha de base trivial é obrigatória em toda tabela de agente** (D-051) — é o `denso puro` deste
critério, e sem ela 49% de precisão parece bom em vez de "17 pontos acima de emitir tudo".

## Estado da base

- **30 startups** em `data/seed/*.yaml`, **93 documentos**, `url_fonte` verificadas **93/93**
  (D-090). **A M3 fechou** — é o piso de 30-50 que o TAPI recomenda. `ano_fundacao` literal em
  18 de 30, `estagio` em 11, `localizacao` em 9: baixo **de propósito**, porque só entra o que
  o documento diz LITERALMENTE — `null` faz o Briefing reportar *"requisito não verificado"*.
  **Duas camadas (D-062):** **8 com bloco `gabarito:`** — a régua dos critérios 1 e 3, e as únicas
  que movem número — e **22 como DADO, sem gabarito**, porque anotá-las seria calibrar contra o
  próprio gabarito. `avaliar_agentes.py` filtra por `gabarito` e imprime as duas contagens; sem
  esse filtro a precisão cai de 49% para 24% **em silêncio** (contrafactual medido em D-090).
  **As 10 chaves de `SETORES` têm empresa** — nenhuma consulta do vocabulário do planner devolve
  zero. **As 4 exclusões do Inception têm caso REAL:** consultoria (Deal), capital aberto
  (Zenvia/Nasdaq), cripto (Liqi/stablecoin), > 10 anos (**4 casos**: Agrorobótica, Agrotools, Automni e JetBov). **A Solinftec
  é o CASO-LIMITE, não um segundo caso** (D-097): tem 18 anos, o documento diz *"Criada há 18
  anos"* — idade, não ano — e a política de literalidade mantém `ano_fundacao: null`, então ela
  sai **ELEGÍVEL** com *"requisito não verificado"*. É o preço declarado da literalidade, e o
  Briefing o reporta em vez de inventar um ano.
  > **O gargalo da curadoria é o 3º documento, não a empresa** (D-090): `seed.py` exige 3
  > documentos e ≥ 2 TIPOS distintos, e 4 empresas boas caíram já coletadas.
- **16 tecnologias NVIDIA**, 175 chunks estruturais + 202 de controle, gabarito de **24 perguntas**
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
python scripts/avaliar_agentes.py --justificativas  # o seletor do trecho técnico vs. os 150 primeiros
python scripts/varrer_elegibilidade.py         # o veredito das 30 numa tabela, zero API (D-094)
python scripts/varrer_elegibilidade.py --motivos   # com a evidência de cada recusa
python scripts/varrer_classes.py               # o veredito de CLASSE das 30, com quadrante (D-098)
python scripts/varrer_classes.py --custo-desenhos  # o que cada conserto custa NA RÉGUA
python scripts/medir_confianca.py              # os 4 braços da confiança do diagnóstico (D-098)
python scripts/medir_cobertura.py              # o que o filtro do Inception NÃO lê, e o custo de mostrar tudo (D-102)
python scripts/medir_cobertura.py --terceiro   # por que varrer o documento inteiro quebra o veto
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
| `projeto/revisao-pontos-cegos.md` | **envelope lacrado da revisão do plano** — abre com os limites da auditoria (pode ler sempre) e fecha com a lista de quem fez o plano, que só deve ser lida DEPOIS de você ter escrito a sua |
| `projeto/decisoes.md` | **sempre que uma decisão for tomada** — escrever na hora. É o material de defesa, o roteiro do vídeo e a seção de arquitetura do README |
| `projeto/plano.md` | **plano dos dias finais** — todo item aberto com destino, portões e eliminatórios · [versão visual](https://claude.ai/code/artifact/b6d37462-6743-43c1-ac6d-da5a15af7839) |
| `projeto/guia-de-trabalho.md` | método de trabalho e manutenção desta documentação |
| `contexto/01-tapi.md` | precisar do requisito exato: schema, os 7 campos do output, pipeline de 9 passos, regras do vídeo, tabela do barema |
| `contexto/02-rubrica-ai-native.md` | for mexer no Extractor, no Classifier ou no Evidence Validator — é a rubrica que o TAPI não fornece |
| `contexto/03-stack-nvidia.md` | for mexer na base de conhecimento ou no motor de recomendação |
| `contexto/04-ecossistema-br.md` | for popular a base de startups ou precisar de `url_fonte` legítimo |
| `contexto/05-achados-e-decisoes.md` | achados do levantamento e o que ficou sem resposta |
| **[Anatomia do Radar](https://claude.ai/code/artifact/dc527bde-f149-49f8-87a5-3105197cc2e2)** | documento de estudo: os 9 agentes, os 9 passos e o que está medido |
| `scripts/avaliar_agentes.py` | a régua dos agentes: o que se conta e por que a linha trivial existe |
| `data/avaliacao/gabarito.yaml` | as 24 perguntas do RAG, com documento-fonte esperado |
| `data/avaliacao/exclusoes.yaml` | a régua do filtro do Inception, com os dois lados medidos separados |
| `data/avaliacao/justificativas.yaml` | a régua da `justificativa_tecnica` — 30 chunks de amostra semeada, rotulados **antes** do seletor |
| `data/nvidia/fontes.yaml` | manifesto curado das 16 fontes do RAG |

`TAPI Processo Seletivo.md` é a fonte original — não editar.

## Regra permanente

Toda decisão técnica vai para `projeto/decisoes.md` **no momento em que é tomada**, com a
alternativa descartada e o motivo. O log guarda a **decisão**, não o caderno de laboratório: um
número só fica se é verdade sobre o sistema que roda hoje; se o instrumento morreu, fica a
conclusão (D-073).

---
*Contexto levantado em 21-22/08/2026 a partir do TAPI e das ~40 fontes que ele lista.*
