# 03 — Stack NVIDIA: a base de conhecimento e o motor de recomendação

Levantado das documentações oficiais listadas na §8.2 do TAPI, em 21-22/08/2026.
Serve para dois propósitos: alimentar a **base RAG** (Entregável 2) e dar lastro técnico ao
**motor de recomendação** (Entregável 3).

> Ver `05-achados-e-decisoes.md` para os rebrands ocorridos desde a redação do TAPI em junho.

---

## 1. As 16 tecnologias

### NVIDIA NIM — microservices de inferência
https://www.nvidia.com/en-us/ai-data-science/products/nim-microservices/

Containers pré-construídos e otimizados para deploy de modelos em qualquer infraestrutura
acelerada por NVIDIA. Empacota: modelo + engine de inferência otimizada (TensorRT-LLM, vLLM ou
SGLang) + API padrão + dependências de runtime.

- **API OpenAI-compatible**: `POST /v1/completions`, `POST /v1/chat/completions`. Trocar o
  `base_url` do SDK da OpenAI é suficiente — o código não muda
- Deploy com um comando: `docker run nvcr.io/nim/publisher_name/model_name`. Kubernetes-native
- Três formas de consumo: endpoints hospedados em DGX Cloud (protótipo), self-hosted, ou parceiro
- **Benchmark citado:** Llama 3.1 8B em H100 — **1.201 tokens/s contra 613** de baseline (~2x).
  200+ usuários concorrentes. Deploy em ~5 minutos
- **Privacidade:** self-hosting mantém o dado dentro da infra do cliente
- Licença: free tier no NVIDIA Developer Program para protótipo; **produção exige NVIDIA AI Enterprise**

**Quando recomendar:** startup dependente de API externa que já sente custo, latência ou tem
requisito de privacidade/soberania de dado. É a recomendação de entrada mais frequente.

### TensorRT-LLM — otimização de inferência
https://github.com/NVIDIA/TensorRT-LLM · Apache 2.0

Biblioteca open source com API Python para definir LLMs, kernels customizados e runtime.

- **Quantização:** FP8, FP4, INT8, INT4 com AWQ (activation-aware weight quantization)
- **Algorítmico:** speculative decoding (~3x de throughput), prefill-decode disaggregation,
  paged KV cache e reuso de KV cache, chunked context, multiblock attention (>3x em sequências longas no H200)
- **Paralelismo:** tensor, pipeline, context, data e wide expert parallelism (MoE)
- **Kernels:** fusão, XQA kernel (2.4x mais throughput em Llama-70B no mesmo orçamento de latência), CUDA graphs
- **Números:** Llama 4 Maverick >40.000 tok/s em B200 · Llama 2-13B ~12.000 tok/s em H200 ·
  Llama-70B 6.7x sobre baseline A100 · DeepSeek-R1 em Blackwell rompendo 1.000 TPS/usuário
- Modelos: Llama 3.1/3.2/3.3/4, DeepSeek V3/R1, Mixtral, GPT-OSS, Falcon-180B, Stable Diffusion 3
- Hardware: H100, H200, B200, L4, L40, RTX, A100

**Quando recomendar:** dor específica de latência ou custo por token com carga de LLM própria.
Costuma vir junto de NIM (que já embute TensorRT-LLM) ou Triton.

### Triton Inference Server — serving em produção
https://developer.nvidia.com/triton-inference-server · docs: https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/

Hoje chamado **Dynamo-Triton**; open source e parte do NVIDIA AI Enterprise.

- Backends: TensorRT, PyTorch, ONNX, OpenVINO, Python, RAPIDS FIL, vLLM
- **Dynamic batching**, sequence batching, execução concorrente de modelos, instance groups
- **Model ensembles** e business logic scripting para pipelines multi-modelo
- Roda em GPU NVIDIA, aceleradores de terceiros, CPU x86 e ARM, Kubernetes, cloud e on-prem
- Observabilidade via Prometheus; response cache, rate limiter, tracing
- APIs: OpenAI-compatible, KServe, bindings Python/C/C++/Java

**Quando recomendar:** a startup serve vários modelos, ou mistura LLM com modelos clássicos,
ou precisa de batching e utilização de GPU decentes em produção.

### NVIDIA NeMo — ciclo de vida de agentes e modelos
https://www.nvidia.com/en-us/ai-data-science/products/nemo/

Suíte aberta *"agent-first"* para especialização, otimização e governança de agentes.
Quatro fases:

| Fase | Componentes |
|---|---|
| **Build** | **Curator** (limpa e filtra dado multimodal) · **Data Designer** (dataset sintético de domínio) · **Anonymizer** (anonimização context-aware de PII) · **Safe Synthesizer** (sintético sem mapeamento 1:1) · **Evaluator** (benchmark acadêmico, LLM-as-judge, custom) |
| **Deploy** | **NIM** · **Guardrails** · **Auditor** (vulnerabilidades antes de produção) |
| **Optimize** | **Relay** (observabilidade de agentes) · **Customizer** (fine-tuning e alinhamento com dado de domínio) · **Framework** (treino em escala) · **RL** (post-training) · **Gym** (ambientes simulados para RL agêntico) |
| **Improve** | data flywheel: monitoramento realimenta retreino |

**Quando recomendar:** a startup tem dado proprietário e precisa customizar modelo; ou não tem
processo de avaliação (NeMo Evaluator resolve o gap mais comum e mais invisível).

### NeMo Guardrails — governança de agentes
https://github.com/NVIDIA/NeMo-Guardrails

Toolkit open source que adiciona guardrails programáveis entre a aplicação e o LLM.

**Os cinco tipos de rail:**
1. **Input rails** — processam a mensagem antes do LLM; rejeitam ou mascaram PII
2. **Dialog rails** — controlam o fluxo via mensagens canônicas em **Colang**
3. **Retrieval rails** — filtram chunks em cenário de RAG, impedindo conteúdo impróprio de chegar ao LLM
4. **Execution rails** — validam entrada e saída de actions e tool calls
5. **Output rails** — filtram ou redigem a resposta antes de devolver ao usuário

- **Colang**: DSL parecida com Python para modelagem de diálogo (v1.0 default, v2.0 disponível)
- Estrutura: `config.yml` · `config.py` · `actions.py` · `rails.co`
- Mitiga: jailbreak e prompt injection, toxicidade, alucinação, fuga de tópico, exposição de PII,
  falta de grounding factual
- Integração LangChain: `export NEMOGUARDRAILS_LLM_FRAMEWORK=langchain` — envolve qualquer `Runnable`
- Uso: `pip install nemoguardrails`; `RailsConfig.from_path()` + `LLMRails.generate()`;
  também servidor CLI, Docker e endpoint `/v1/chat/completions`
- Tem comando `nemoguardrails evaluate` para rails de tópico, fact-checking, moderação e alucinação

**Quando recomendar:** a startup opera agente em contato com cliente final, ou atua em setor
regulado, ou não tem nenhum controle de comportamento. Note o **retrieval rail** — é o argumento
específico para quem tem RAG em produção.

> Vale usar no próprio projeto: o retrieval rail é diretamente aplicável ao RAG do Entregável 2.

### RAPIDS / CUDA-X Data Science
https://rapids.ai/ (redireciona) → https://developer.nvidia.com/topics/ai/data-science/cuda-x-data-science-libraries

Coleção de bibliotecas otimizadas para acelerar data science em GPU.
**A marca RAPIDS passou a ser CUDA-X em 11/08/2026**; funcionalidade idêntica.

- **cuDF** — dataframes; acelera pandas, Polars e Spark **sem mudança de código**, até 20x
- **cuML** — ML; 50x mais rápido que scikit-learn, suporta UMAP e HDBSCAN sem mudança de código
- **cuGraph** — grafos; 48x sobre NetworkX, milhões de nós
- **cuxfilter** — visualização interativa com filtragem multidimensional em datasets de 100M+ linhas
- Integração com **Dask** e **Apache Spark** para múltiplos nós
- Casos citados: detecção de fraude 100x mais rápida no treino (bunq), análise financeira 100x
  (Capital One), análise genômica de 10 horas para 3 minutos (TGen)

### cuDF
https://docs.rapids.ai/api/cudf/stable/

API de dataframe compatível com pandas rodando em GPU. O acelerador **`cudf.pandas`** é
zero-code-change: intercepta as operações do pandas via proxy objects e roteia para GPU quando
vale a pena, com **fallback automático para CPU** no que não é suportado.
Também entrega o **GPU engine do Polars** (`cudf.polars`).

**Quando recomendar:** pipeline de ETL ou feature engineering em pandas que virou gargalo.
O argumento de venda é o zero-code-change — barreira de adoção quase nula.

### cuML
https://docs.rapids.ai/api/cuml/stable/

ML acelerado em GPU com compatibilidade de API com scikit-learn. **`cuml.accel`** acelera código
existente de scikit-learn, umap-learn e hdbscan sem alteração nenhuma.
**50+ algoritmos**: clustering (DBSCAN, K-Means), regressão (Linear, Ridge, Lasso),
árvores (Random Forest), redução de dimensionalidade (PCA, UMAP, t-SNE), nearest neighbors, SVM.
**10–50x** sobre CPU. Multi-GPU e multi-nó via Dask.

### CUDA Toolkit
https://developer.nvidia.com/cuda-toolkit

Ambiente de desenvolvimento para aplicações aceleradas por GPU: compilador C/C++, bibliotecas
aceleradas, runtime, e Nsight Developer Tools para profiling e otimização.
Modelos de programação: CUDA C/C++, **CUDA Tile C++**, **cuTile Python**.
Plataformas: Windows, WSL, ARM, Jetson.

**Quando recomendar:** raramente como primeira recomendação. É para quem já tem kernel custom ou
gargalo que nenhuma biblioteca de alto nível resolve. Recomendar CUDA para quem só precisa de
cuDF é sinal de motor de recomendação raso.

### NVIDIA Riva — speech AI
https://developer.nvidia.com/riva

Modelos abertos e acelerados para fala e tradução, hoje apresentados como família
**Nemotron Speech**: ASR, TTS, NMT e speech-to-speech em ~40 idiomas.

- **ASR em 12 idiomas, incluindo português** — árabe, inglês, francês, alemão, hindi, italiano,
  japonês, coreano, mandarim, **português**, russo, espanhol
- **TTS** em inglês, alemão, italiano, mandarim e espanhol, com voz e entonação customizáveis
- **NMT** texto-texto, fala-texto e fala-fala em até 32 idiomas
- Deploy: cloud, on-prem, edge, embarcado, containers NIM, endpoints em build.nvidia.com
- Totalmente customizável: fine-tuning em dataset próprio

**Quando recomendar:** voz, call center, transcrição. **O suporte a português no ASR é o
argumento decisivo no mercado brasileiro** — vale citar explicitamente na justificativa técnica.
Nota: o TTS ainda não cobre português, o que é uma limitação honesta a registrar.

### NVIDIA Omniverse — simulação, 3D e digital twins
https://www.nvidia.com/en-us/omniverse/

Plataforma para construir mundos simulation-ready onde times de physical AI treinam, testam e
validam sistemas antes do mundo real.

- **OpenUSD** para interoperabilidade e troca de dados de cena 3D
- **ovrtx** — rendering RTX e geração de saída sintética de sensores
- **ovphysx** — simulação de física (sobre Newton Physics): movimento, contatos, comportamento
- **SimReady** — valida assets OpenUSD contra requisitos de simulação
- Formas de começar: bibliotecas, agent skills, **blueprints** (build.nvidia.com), samples
- Relação com **Cosmos**: Omniverse é o ambiente de simulação 3D; Cosmos é a plataforma de world
  models que gera dado sintético fotorrealista. Trabalham juntos
- Parceiros: Adobe, Blender, Cadence, Dassault, Hexagon, Azure, PTC, Schneider, Siemens

**Casos:** digital twin de planta industrial, simulação de robôs, geração de dado sintético,
simulação de veículo autônomo, fábrica digital.

### NVIDIA Isaac — robótica
https://developer.nvidia.com/isaac

| Componente | Função |
|---|---|
| **Isaac Sim** | simulação com física, geração de dado sintético antes do hardware |
| **Isaac Lab** | framework de robot learning (RL e outros métodos) |
| **Isaac ROS** | integração com ROS: percepção, planejamento, controle |
| **Isaac GR00T** | foundation model para manipulação e decisão robótica |
| **Isaac Manipulator / Perceptor** | controle de braço robótico e percepção do ambiente |

Hardware: Jetson, AGX Orin, Thor. Fluxo sim-to-real com dado sintético.
Casos: AMRs, manipuladores, humanoides.

### Saúde — o que substituiu o "Clara"
https://www.nvidia.com/en-us/clara/

**A NVIDIA não apresenta mais "Clara" como marca guarda-chuva unificada.** Hoje o portfólio de
Healthcare & Life Sciences é:

| Plataforma | Função | Números |
|---|---|---|
| **BioNeMo** | IA para biologia e descoberta de fármacos: design molecular, virtual screening, predição de estrutura de proteína, design de binder | treino 2x mais rápido, inferência 6x |
| **MONAI** | framework aberto de IA para imagem médica, sobre PyTorch: segmentação e registro 2D/3D, reporting, workflows multimodais | 8M+ downloads, 4.000+ projetos |
| **Parabricks** | genômica acelerada por GPU: BWA-MEM, GATK, DeepVariant | **100x** em WGS, 50% menos custo de compute |
| **Holoscan SDK** | runtime real-time para physical AI e processamento de sensores | escala de Jetson Nano a DGX, dezenas a centenas de Gb/s |
| **Isaac for Healthcare** | robótica e simulação: ultrassom autônomo, autonomia cirúrgica, teleoperação | arquitetura treino-simulação-runtime |

> Isso resolve a inconsistência do MONAI que o TAPI cria: ele aparece nos exemplos de
> recomendação da §5.5 mas não na lista de tecnologias da §5.4. Ele está sim no line-up atual.

### NVIDIA Morpheus — cybersecurity
https://developer.nvidia.com/morpheus-cybersecurity

Framework acelerado por GPU para filtrar, processar e classificar grandes volumes de dado de
segurança em **streaming**. Arquitetura de pipelines com estágios modulares.

Casos: detecção de phishing e spear phishing · **digital fingerprinting** (impressão digital de
cada usuário da rede para detectar anomalia) · anomalous behavior profiling · detecção de fraude
com **GNN** · detecção de informação sensível · ameaça interna e priorização de alertas.

Integra **RAPIDS FIL** (Forest Inference Library) e **Triton**.
Consumo: open source no GitHub, workflows prontos no NGC (Helm charts, notebooks), ou AI Enterprise.

### NVIDIA AI Enterprise — a camada comercial
https://www.nvidia.com/en-us/data-center/products/ai-enterprise/

Suíte comercial que reúne **NIM, NeMo, Omniverse, Run:ai (orquestração de GPU), CUDA-X, RAPIDS,
Triton e Blueprints** num pacote suportado e pronto para produção.

**O que se compra que o open source não dá:**
- branches de produção com ciclo de vida estendido e suporte enterprise
- patching de vulnerabilidade e containers **STIG-hardened**
- **estabilidade de API** — reduz risco de integração
- supply chain de software segura
- orquestração: *"até 10x mais disponibilidade de GPU"* e *"até 5x mais utilização"*

Licença **por GPU por ano**; trial de 90 dias on-prem; disponível nos marketplaces de
AWS, Google Cloud e Azure.

**Quando recomendar:** startup em escala com cliente corporativo, exigência de compliance, ou
que precisa de SLA. Recomendar AI Enterprise para pre-seed é ruído — a complexidade e o custo
não se justificam.

---

## 2. NVIDIA Inception — o programa (o destino de todo briefing)

https://www.nvidia.com/en-us/startups/

Gratuito, **sem taxa de inscrição, sem mensalidade e sem equity**. Sem deadline e sem cohort.

### Elegibilidade — vira regra de negócio no Briefing Agent

**Requisitos:**
- pelo menos **um developer** empregado
- empresa **oficialmente incorporada**
- **site ativo**
- **menos de 10 anos** de existência
- **não exige geração de receita**

**Exclui explicitamente:**
- consultorias e firmas de desenvolvimento terceirizado
- empresas ligadas a criptomoeda
- cloud service providers
- revendedores e distribuidores
- **empresas de capital aberto**

> Implementar esse filtro é um diferencial barato e alto: o sistema **recusar** recomendar
> Inception para uma consultoria de IA — e explicar por quê — é exatamente o tipo de decisão
> consciente que separa nível 2 de nível 4 no barema. A base de startups deveria conter ao menos
> um caso inelegível para exercitar isso.

### Benefícios

| Categoria | O que inclui |
|---|---|
| **Treinamento** | cursos self-paced grátis do **Deep Learning Institute (DLI)**, workshops com desconto, acesso aos fóruns de desenvolvedores, newsletter exclusiva |
| **Ferramentas e hardware** | SDKs, bibliotecas de modelos e plataformas · **preço preferencial em hardware e software** (funciona como rebate, não venda direta) · **créditos de cloud grátis** da NVIDIA e de parceiros |
| **Capital** | **Inception Capital Connect** · conexões via **NVIDIA VC Alliance** · eventos curados com startups, VCs e executivos |
| **Mercado e marca** | badge oficial de membro, conteúdo co-branded, assets de marketing, apresentações estratégicas, oportunidades de go-to-market conforme o engajamento cresce |
| **Eventos** | presença em GTC, KubeCon, Supercomputing, Microsoft Ignite, AWS re:Invent, NeurIPS, Oracle AI World |

**Processo:** aplicação com dados de negócio e produto → revisão da NVIDIA → aceite → atualizar
perfil no Inception Portal → acesso aos benefícios personalizados.

**Ressalva registrada pela própria NVIDIA:** não há garantia de acesso a inventário de GPU de
disponibilidade limitada, e o preço preferencial pode mudar.

---

## 3. build.nvidia.com — o catálogo de APIs

Conta grátis, **100+ modelos**, **créditos grátis que não expiram**, endpoints
**OpenAI-compatible**. É a porta de entrada de baixo atrito para a stack NVIDIA — e o caminho
para usar a própria stack no projeto.

### NeMo Retriever — embedding e reranking

> **Verificado por chamada real em 22/08/2026.** Os modelos que o TAPI e a documentação de
> junho citavam **não existem mais**: os endpoints `llama-3.2-nv-embedqa-1b-v2` e
> `llama-3.2-nv-rerankqa-1b-v2` respondem **HTTP 410 Gone**, com a mensagem
> *"This endpoint has reached its end of life on 2026-05-18"*. A tabela abaixo é o que
> responde hoje, medido com `scripts/smoke_nvidia.py`.

| Papel | Modelo atual | Endpoint | Medido em 22/08 |
|---|---|---|---|
| Embedding | **`nvidia/llama-nemotron-embed-1b-v2`** | `https://integrate.api.nvidia.com/v1/embeddings` | 593 ms · 2048 dims nativas, **aceita `dimensions`** (Matryoshka) |
| Embedding | `nvidia/nemotron-3-embed-1b` | idem | 679 ms · 2048 dims, **não trunca** (HTTP 400 em `dimensions`) |
| Embedding | `nvidia/nv-embedqa-e5-v5` | idem | 494 ms · 1024 dims nativas |
| Reranking | **`nvidia/llama-nemotron-rerank-1b-v2`** | `https://ai.api.nvidia.com/v1/retrieval/nvidia/llama-nemotron-rerank-1b-v2/reranking` | 520 ms · margem topo→2º de **12.94** |
| Reranking | `nvidia/llama-nemotron-rerank-vl-1b-v2` | idem, com o nome do modelo no path | 535 ms · margem **3.24** (multimodal, separa menos em texto puro) |

**Dois detalhes que só aparecem chamando:**

1. **A URL de reranking embute o nome do modelo no path.** Trocar de reranker exige trocar a
   URL junto — por isso `src/config.py` guarda a URL completa em vez de `base_url` + sufixo.
2. **Os embedders são assimétricos:** exigem `input_type="query"` ou `"passage"`. Embedar um
   documento como se fosse consulta degrada a recuperação silenciosamente — não dá erro.

**Qualidade medida em português e crosslingual** (consulta PT sobre custo/latência de inferência,
contra passagem PT relevante, passagem EN relevante e passagem PT irrelevante):

| Modelo | PT relevante | EN relevante | PT irrelevante | Leitura |
|---|---|---|---|---|
| `llama-nemotron-embed-1b-v2` | 0.3546 | 0.4280 | 0.0049 | separa 70x · crosslingual real |
| `nemotron-3-embed-1b` | 0.5241 | 0.5460 | 0.1137 | separa bem, mas preso em 2048 dims |
| `nv-embedqa-e5-v5` | 0.4648 | 0.3107 | 0.3096 | **crosslingual falha** — 0.3107 vs 0.3096 é ruído |

> **Por que isso importa para o projeto:** substitui o Cohere Rerank (pago) que o TAPI recomenda,
> resolve embedding de documentos em português, e entrega o argumento mais forte possível no
> vídeo — *"usei a própria stack que o sistema recomenda"*. Melhor candidato a Diferencial (peso 5)
> que também empurra o critério 2 (peso 20).

---

## 4. Mapa dor observável → tecnologia

A tabela abaixo é o núcleo do motor de recomendação. As dores da coluna 1 são as oito que o
próprio TAPI lista na contextualização: custo, latência, escalabilidade, governança, privacidade,
avaliação, observabilidade e dependência de fornecedor.

| Dor observável na startup | Tecnologia | Justificativa técnica curta |
|---|---|---|
| Depende só de API externa; custo/latência/privacidade | **NIM** | self-host com API OpenAI-compatible, migração sem mudar código; 2x tok/s no benchmark H100 |
| Latência de inferência de LLM | **TensorRT-LLM** | quantização FP8/FP4/INT4-AWQ, speculative decoding ~3x, paged KV cache |
| Serve vários modelos em produção; GPU subutilizada | **Triton (Dynamo-Triton)** | dynamic batching, execução concorrente, ensembles, métricas Prometheus |
| Agente em contato com cliente, sem controle de comportamento | **NeMo Guardrails** | 5 rails incl. retrieval rail; Colang; integra LangChain |
| Setor regulado, risco de PII | **NeMo Guardrails** + **NeMo Anonymizer** | mascaramento de PII em input e output |
| Tem dado proprietário mas não customiza modelo | **NeMo Customizer / Framework / RL** | fine-tuning e alinhamento com dado de domínio |
| Não mede qualidade do que entrega | **NeMo Evaluator** | benchmark acadêmico, LLM-as-judge, custom |
| Não sabe se o agente regrediu | **NeMo Relay** + **Auditor** | observabilidade de agentes, varredura de vulnerabilidade |
| ETL / feature engineering em pandas travando | **cuDF** (`cudf.pandas`) | zero-code-change com fallback CPU; até 20x |
| ML clássico lento (sklearn) | **cuML** (`cuml.accel`) | 50+ algoritmos, 10–50x, drop-in |
| Análise de grafo / anti-fraude em rede | **cuGraph** | 48x sobre NetworkX |
| Voz, call center, transcrição | **Riva** | **ASR com português**; TTS, NMT; deploy via NIM |
| Saúde: imagem médica | **MONAI** (+ **Holoscan** se dispositivo) | segmentação/registro 2D e 3D sobre PyTorch |
| Saúde: genômica | **Parabricks** | 100x em WGS, 50% menos custo |
| Saúde: descoberta de fármacos | **BioNeMo** | design molecular, virtual screening, estrutura de proteína |
| Robótica, simulação, digital twin | **Isaac** + **Omniverse** (+ **Cosmos**) | sim-to-real com dado sintético; OpenUSD |
| Cybersecurity, fraude, anomalia em streaming | **Morpheus** | pipelines streaming, digital fingerprinting, GNN |
| Cliente corporativo, compliance, SLA | **AI Enterprise** | STIG-hardened, CVE patching, estabilidade de API |
| Gargalo que nenhuma biblioteca resolve | **CUDA Toolkit** | kernels custom, Nsight para profiling |
| Startup elegível, qualquer estágio | **Inception** | grátis, sem equity, DLI, créditos, VC Alliance |

### Regras de qualidade para o Recommendation Agent

1. **Prioridade vem do gap, não do rótulo.** Ver o modelo de dois eixos em `02-rubrica-ai-native.md`
2. **Complexidade de implementação tem que ser honesta.** `cudf.pandas` é zero-code-change;
   migrar para Triton com TensorRT-LLM é projeto de semanas. Tratar os dois como iguais denuncia
   motor raso
3. **Recomendação sem evidência não sai.** Se a base não tem documento que sustente a dor,
   o correto é não recomendar — ou recomendar com confiança baixa e dizer o que falta descobrir
4. **Não empilhar tecnologia.** Recomendar 8 produtos para uma seed é ruído. Duas ou três com
   próxima ação clara valem mais
5. **O estágio muda a recomendação.** Pre-seed → Inception e créditos. Série A com carga real →
   NIM e TensorRT-LLM. Série B com cliente corporativo → AI Enterprise

---

## 5. URLs oficiais (fontes da §8.2 do TAPI, todas verificadas em 22/08/2026)

| Tecnologia | URL |
|---|---|
| NVIDIA Inception | https://www.nvidia.com/en-us/startups/ |
| NVIDIA NIM | https://www.nvidia.com/en-us/ai-data-science/products/nim-microservices/ |
| NVIDIA API Catalog | https://build.nvidia.com/ |
| NVIDIA NeMo | https://www.nvidia.com/en-us/ai-data-science/products/nemo/ |
| NeMo Guardrails | https://github.com/NVIDIA/NeMo-Guardrails |
| Triton Inference Server | https://developer.nvidia.com/triton-inference-server |
| Triton docs | https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/ |
| TensorRT-LLM | https://github.com/NVIDIA/TensorRT-LLM |
| RAPIDS / CUDA-X | https://developer.nvidia.com/topics/ai/data-science/cuda-x-data-science-libraries |
| cuDF | https://docs.rapids.ai/api/cudf/stable/ |
| cuML | https://docs.rapids.ai/api/cuml/stable/ |
| CUDA Toolkit | https://developer.nvidia.com/cuda-toolkit |
| NVIDIA Riva | https://developer.nvidia.com/riva |
| NVIDIA Omniverse | https://www.nvidia.com/en-us/omniverse/ |
| NVIDIA Isaac | https://developer.nvidia.com/isaac |
| Saúde (ex-Clara) | https://www.nvidia.com/en-us/clara/ |
| NVIDIA Morpheus | https://developer.nvidia.com/morpheus-cybersecurity |
| NVIDIA AI Enterprise | https://www.nvidia.com/en-us/data-center/products/ai-enterprise/ |

Materiais de apoio conceituais (§8.1) estão em `02-rubrica-ai-native.md`.
