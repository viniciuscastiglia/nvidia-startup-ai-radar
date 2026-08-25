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
| **NeMo Retriever** (embedding e reranking) | família **Nemotron** | **DOIS EOLs, não um.** `llama-3.2-nv-embedqa/rerankqa-1b-v2` morreram em 18/05/2026 e os substitutos `llama-nemotron-embed/rerank-1b-v2` morreram em **25/08/2026**, todos HTTP 410 Gone. Atuais: `llama-nemotron-embed-vl-1b-v2` e `rerank-qa-mistral-4b`. **Este catálogo é perecível — rode `smoke_nvidia.py` antes de confiar nesta linha** (D-013, D-046) |
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
nisso. Base pequena e bem curada provavelmente vale mais que base grande e rasa — o barema avalia
a qualidade do raciocínio sobre os dados, não o tamanho do dataset.

### 4.2 Provedor de LLM e de embeddings
O TAPI não define. **Recomendação: NVIDIA NIM via build.nvidia.com** — créditos grátis que não
expiram, API OpenAI-compatible (funciona direto com LangChain/LangGraph), e coerência narrativa
com o case. Ver `03-stack-nvidia.md` §3.

**Risco a verificar antes de comprometer:** limite prático dos créditos grátis para o volume de
chamadas de um pipeline de 8 agentes rodando várias vezes em desenvolvimento. Vale testar cedo e
ter um fallback configurável por variável de ambiente.

### 4.3 Reranker
Três opções:
- **NeMo Retriever** (`llama-3.2-nv-rerankqa-1b-v2`, endpoint `/v1/ranking`) — grátis, coerente
  com o case, multilíngue. **Recomendado**
- **Cohere Rerank** — é o que o TAPI sugere, mas é pago
- **Cross-encoder local** (BGE, Jina) — sem custo de API, mas exige rodar o modelo

Usar o NeMo Retriever e **documentar a comparação com as alternativas** vale mais do que só
escolher: o barema premia decisão consciente, e essa é uma decisão fácil de defender.

### 4.4 Banco vetorial
Qdrant é o recomendado; ChromaDB, Pinecone e pgvector são explicitamente permitidos.
**pgvector** tem um argumento próprio: se o Postgres já está lá para as tabelas `startups` e
`documentos`, unificar reduz uma peça de infraestrutura — e simplificar a stack conscientemente
é uma decisão defensável. Qdrant tem melhor suporte nativo a busca híbrida.
Decidir junto com a implementação do passo 6 do pipeline RAG (busca híbrida vetorial + BM25).

### 4.5 Frontend
Livre, e vale **5 pontos**. O risco real é gastar dias aqui e perder pontos nos critérios de 20.
Mas atenção: **o vídeo (peso 20) exige demonstrar o projeto funcionando pela interface web** —
ou seja, a interface precisa ser boa o bastante para o demo não parecer quebrado. O alvo é
"funcional e limpa", não "impressionante".

### 4.6 Diferencial (peso 5)
**Candidato principal:** rodar o RAG inteiro na própria stack NVIDIA (build.nvidia.com + NeMo
Retriever para embedding e reranking). Empurra o critério 2 junto e dá o melhor argumento
possível no vídeo.

**Candidatos secundários, todos já mapeados no contexto:**
- Filtro de **elegibilidade do Inception** no Briefing Agent — o sistema recusar recomendar o
  programa para uma consultoria de IA, e explicar por quê (`03-stack-nvidia.md` §2)
- Modelo de **dois eixos** (maturidade AI-native × maturidade de stack) para priorizar prospects
  em vez de um rótulo único (`02-rubrica-ai-native.md` §4)
- **Harness de avaliação do RAG** — é o passo 9 da pipeline que o TAPI pede e quase ninguém entrega
- **NeMo Guardrails com retrieval rail** aplicado ao próprio RAG do projeto

---

## 5. Onde os pontos realmente estão

Recapitulando a matemática do barema, porque ela deve guiar a alocação dos 18 dias:

- **Núcleo de IA (critérios 1+2+3) = 60 pontos**
- **Comunicação (vídeo 20 + repo/docs 10) = 30 pontos** — 30% da nota não é código
- **Produto (interface 5 + diferencial 5) = 10 pontos**

Nível 2 ("cumpre o mínimo") em tudo dá **50/100**. Nível 3 ("bom, com decisões técnicas
conscientes") dá **75**. A diferença entre 50 e 75 não está em entregar mais features — está em
cada escolha técnica ter uma razão articulada.

**Implicações práticas:**
- O vídeo de 7 minutos merece preparação real, não gravação de última hora. Vale o mesmo que o
  sistema multi-agente inteiro
- O README merece as decisões de arquitetura escritas, com as alternativas descartadas
- Cada decisão tomada durante a implementação deve ser registrada na hora, enquanto o motivo
  está fresco — é o material do vídeo e do repositório
- **Eliminatório nº 4** — "código integralmente gerado sem compreensão": o Vinícius precisa
  conseguir explicar cada decisão. Ver a seção "Como trabalhar neste projeto" no `CLAUDE.md`

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
