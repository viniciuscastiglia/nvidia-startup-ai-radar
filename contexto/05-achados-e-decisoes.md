# 05 — Achados e decisões em aberto

Levantado em 21-22/08/2026. Registra o que mudou desde a redação do TAPI (junho/2026),
as inconsistências encontradas, e o que ainda precisa ser decidido antes de codar.

---

## 1. Rebrands da NVIDIA desde junho/2026

O TAPI usa nomes que a NVIDIA já mudou. Nenhum invalida o projeto, mas citar as duas
nomenclaturas demonstra que a fonte atual foi consultada — vale ponto no vídeo e no repositório.

| Nome no TAPI | Nome atual | Observação |
|---|---|---|
| **RAPIDS** | **CUDA-X Data Science** | Rebrand em **11/08/2026**; funcionalidade idêntica. cuDF, cuML, cuGraph e cuxfilter seguem com os mesmos nomes |
| **Triton Inference Server** | **Dynamo-Triton** | Continua open source; agora parte do NVIDIA AI Enterprise. **NVIDIA Dynamo** é o framework distribuído de serving em escala de datacenter que trabalha junto |
| **NVIDIA Clara** | *desmembrado* | **Não existe mais como marca guarda-chuva.** O portfólio de Healthcare & Life Sciences hoje é BioNeMo, MONAI, Parabricks, Holoscan SDK e Isaac for Healthcare |
| **NeMo Retriever** (embedding e reranking) | família **Nemotron** | **TRÊS EOLs.** 18/05, 25/08 e 27/08/2026, todos HTTP 410/404. **Do NeMo Retriever só o embedding sobreviveu** — não há reranker no catálogo da NVIDIA (D-064, D-070). Atual: `llama-nemotron-embed-vl-1b-v2`; o passo 7 é Cohere `rerank-v3.5` (D-068). **Este catálogo é perecível — rode `sondar_catalogo.py` antes de confiar nesta linha, porque estar em `/v1/models` não é estar vivo** |
| **NVIDIA Riva** | família **Nemotron Speech** | Riva segue sendo o nome do produto; os modelos são apresentados como Nemotron Speech, ~40 idiomas |

## 2. Inconsistências do próprio TAPI

**MONAI** aparece nos exemplos de recomendação da §5.5 ("Se a startup atua em saúde: considerar
Clara, MONAI, NIM, NeMo Guardrails e AI Enterprise") mas **não** está na lista de tecnologias da
§5.4 nem nas fontes da §8.

→ **Resolvido:** o desmembramento do Clara mostra que MONAI está sim no line-up atual de saúde da
NVIDIA. A base de conhecimento deve incluí-lo, com fonte própria (https://monai.io/ e
https://www.nvidia.com/en-us/clara/), senão a regra de recomendação de saúde fica sem lastro no RAG.

**Canal de submissão e formato de entrega** não constam em lugar nenhum do documento.
**Individual ou em grupo** também não é dito — a linguagem ("o candidato", "o aluno") sugere
individual. Ambos valem uma pergunta direta à liga.

## 3. Links quebrados

Cinco das 23 fontes das §7.1 e §7.2 estão mortas ou degradadas.
Detalhe completo em `04-ecossistema-br.md`. Resumo:

- `startupbase.com.br` — domínio sem registro DNS (era a melhor base pública, 12.800 startups)
- `acestartups.com.br` — domínio serve conteúdo de aposta
- `exame.com/bussola/startups/` — 404
- `inovativabrasil.com.br` — fora do ar até 25/10/2026 (legislação eleitoral)
- `bossainvest.com` — injeção de spam SEO

Redirects a corrigir: `rapids.ai` → developer.nvidia.com/topics/ai/data-science/cuda-x-data-science-libraries ·
`endeavor.org.br` → brasil.endeavor.org · `cubo.network` → cubo.itau

---

## 4. Decisões em aberto

### 4.1 Como popular a base de startups
**O problema:** 90 a 240 documentos com `url_fonte` real, sem scraping, e sem o StartupBase.
É o maior sumidouro de esforço do projeto e o TAPI não diz como fazer.

**Encaminhamento sugerido:** Cubo Itaú como eixo de descoberta (o hub de AI dá o recorte, os
outros 13 dão os casos AI-enabled e non-AI), notícias grátis para volume, vagas para densidade de
sinal. Estratégia detalhada em `04-ecossistema-br.md` §3.

**A decidir:** quantas startups (30 é o mínimo, 80 o teto) e quanto do tempo dos 18 dias alocar
nisso. Base pequena e bem curada vale mais que base grande e rasa — mas há um piso, e ele não é
opinião: **uma base pequena demais não discrimina.** Com 8 fixtures a régua satura, e o gargalo de
vocabulário do Classifier fica insolúvel porque não há variedade linguística suficiente para o
modelo separar os casos (P-12).

### 4.2 Provedor de LLM e de embeddings — **RESOLVIDA** (D-012, D-067)
NVIDIA NIM via build.nvidia.com, API OpenAI-compatible, provedor atrás de env var (D-002).

**O risco que esta seção mandou verificar não era o certo.** Ela apontava o *limite de créditos*;
o que de fato mordeu, três vezes, foi o **EOL de modelo**. Os créditos nunca acabaram. O LLM atual
é `nvidia/nemotron-3-nano-30b-a3b`, escolhido por **eliminação medida** — 1 utilizável de 10
candidatos sondados com chamada real (D-067).

### 4.3 Reranker — **RESOLVIDA** (D-068), e esta seção tinha um fato FALSO

> **Corrigido em 31/08/2026.** Esta seção dizia *"**Cohere Rerank** — é o que o TAPI sugere, mas é
> **pago**"*. **É falso, e era verificável em 22/08:** a Cohere tem trial key gratuita cobrindo
> Rerank (1.000 chamadas/mês, 10 req/min, vedada a uso comercial — o que não se aplica a um
> processo seletivo). Foi essa afirmação que eliminou a única contingência que o projeto tinha, e
> ela custou três meses. Ver **D-065**, que é a decisão que nomeou o erro de método: o rigor foi
> aplicado à escolha técnica e não à **premissa que eliminou as alternativas**.

**A produção roda Cohere `rerank-v3.5`** desde 28/08. O requisito técnico que decide é específico
deste projeto: as perguntas são em português e o corpus é em inglês, então **todo par do passo 7 é
crosslingual** — e `rerank-v3.5` é multilíngue, a mesma propriedade que sempre justificou o NeMo.

As alternativas, com o estado real de cada uma:
- **NeMo Retriever** — **não existe mais.** 9 sondagens de path × modelo em 28/08, todas 404/410,
  e zero modelos com `rank` no nome entre os 83 do catálogo (D-064, D-070)
- **Cross-encoder local** (BGE, Jina) — a única opção sem chave, sem quota e sem EOL, e a resposta
  certa se a trial do Cohere apertar. Custo medido antes de decidir: `torch` são 900 MB no Linux
  x86_64 de quem avalia, mais 27 pacotes e 1,1-2,3 GB de pesos. **Registrado como não medido, não
  como pior** (D-068)
- **Provedor `nenhum`** — degradação graciosa: sem chave, o passo 7 sai do caminho e a resposta
  vira a ordem da híbrida, que sozinha faz 95% r@1. Quem clona o repositório sem chave de rerank
  ainda vê o sistema funcionar em vez de receber um stack trace

### 4.4 Banco vetorial
Qdrant é o recomendado; ChromaDB, Pinecone e pgvector são explicitamente permitidos.
**pgvector** tem um argumento próprio: se o Postgres já está lá para as tabelas `startups` e
`documentos`, unificar reduz uma peça de infraestrutura — e simplificar a stack conscientemente
é uma decisão defensável. Qdrant tem melhor suporte nativo a busca híbrida.
Decidir junto com a implementação do passo 6 do pipeline RAG (busca híbrida vetorial + BM25).

### 4.5 Frontend
Livre. É a **única superfície pela qual alguém que não lê código consegue julgar o sistema** — e o
vídeo exige demonstrar o projeto funcionando por ela. O erro fácil é gastar dias em polimento
enquanto a saída que a interface exibe continua sem lastro; o erro oposto é entregar uma tela que
mostra o trabalho bom de um jeito que parece quebrado.

O que decide o escopo não é orçamento de esforço, é a pergunta de produto: **o que o gerente
precisa ver, em que ordem, para conseguir abordar a startup no dia seguinte?** Decisão em aberto
(P-06).

### 4.6 O que este projeto sabe e quase ninguém sabe — **REFORMULADO** (D-070)
**A formulação original não sobreviveu aos fatos.** Ela era *"rodar o RAG inteiro na própria stack
NVIDIA — NeMo Retriever para embedding **e reranking**"*. O reranking do NeMo **não existe mais**
(D-064), e o que resta rodando na stack NVIDIA é o embedding e o LLM dos agentes.

**O que o projeto de fato mediu, e que quase ninguém mede:** a **volatilidade de catálogo do
fornecedor**, com instrumento versionado (`scripts/sondar_catalogo.py`). Três EOLs em três meses,
com data e método; a constatação de que `GET /v1/models` **lista modelos que devolvem 404**; e um
sistema que continuou rodando através dos três, porque o provedor está isolado em `src/config.py` e
nenhum agente conhece a NVIDIA. Ver D-070.

Isso não vale por ser incomum — vale porque **muda decisão de arquitetura**: é a medição que
justifica o custo de manter provedor isolado atrás de env var em vez de chamar o SDK direto.

**Candidatos secundários, todos já mapeados no contexto:**
- Filtro de **elegibilidade do Inception** no Briefing Agent — o sistema recusar recomendar o
  programa para uma consultoria de IA, e explicar por quê (`03-stack-nvidia.md` §2)
- Modelo de **dois eixos** (maturidade AI-native × maturidade de stack) para priorizar prospects
  em vez de um rótulo único (`02-rubrica-ai-native.md` §4)
- **Harness de avaliação do RAG** — é o passo 9 da pipeline que o TAPI pede e quase ninguém entrega
- **NeMo Guardrails com retrieval rail** aplicado ao próprio RAG do projeto

---

## 5. O que ordena o trabalho

**Não é a aritmética do barema.** Esta seção já foi uma recapitulação dos pesos por critério, com a
instrução de que ela *"deve guiar a alocação dos 18 dias"* — e era a instrução errada, porque peso
de critério mede o que a avaliação valoriza e não diz nada sobre onde o sistema está quebrado
(D-078). A tabela de pesos continua registrada como especificação em `01-tapi.md`.

O que ordena está no `CLAUDE.md` §"O que ordena o trabalho": **o defeito, medido pelo custo que ele
impõe a quem ia usar o sistema.**

Três práticas que a versão antiga desta seção acertava, e que sobrevivem com outra razão:

- **O vídeo de 7 minutos merece preparação real.** Não por valer 20 — porque é a única forma de o
  trabalho ser visto por quem não vai clonar o repositório.
- **O README leva as decisões de arquitetura, com as alternativas descartadas.** Não para render no
  critério 7 — porque quem clona precisa saber por que o sistema é assim antes de mexer nele.
- **Cada decisão é registrada na hora.** Não como material de defesa — porque decisão sem
  alternativa registrada não é revisável, e reconstituir o motivo depois produz justificativa em vez
  de razão.

---

## 6. O que não foi obtido

**Transcrições dos 3 vídeos do YouTube da §8.1** — a plataforma não é acessível por fetch.
Só foi possível recuperar os títulos:
- *"NVIDIA Inception: Construindo o futuro da AI com uma comunidade de startups"* — https://youtu.be/NmZDQSdUVUQ
- *"Panorama I.A com: Andrei Golfeto (NVIDIA)"* — https://www.youtube.com/live/fWfkE6cibwQ
- Playlist de tecnologias NVIDIA — https://youtube.com/playlist?list=PLBaUJRFQ-j_WJZdZfFNsgUWDWF1Ldjp_X
  (não retornou os títulos dos vídeos)

Os dois primeiros são material sobre o Inception e a comunidade de startups — provável
sobreposição com o que já está em `03-stack-nvidia.md` §2 e `04-ecossistema-br.md` §4.
A playlist de tecnologias provavelmente cobre o que já está em `03-stack-nvidia.md` §1.

**Se assistir, vale anotar:** números atualizados do Inception no Brasil, como o time da NVIDIA
descreve o processo de qualificação de startups, e qualquer critério de priorização que eles
usem — isso alimentaria diretamente o Recommendation e o Briefing Agent.

**`build.nvidia.com`** deu timeout no fetch direto; os dados vieram de busca e de
`docs.api.nvidia.com`. Vale confirmar no navegador o limite exato dos créditos grátis antes de
comprometer a arquitetura com essa dependência.
