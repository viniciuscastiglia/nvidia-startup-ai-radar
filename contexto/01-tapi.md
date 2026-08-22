# 01 — O que o TAPI pede

Destilado de `TAPI Processo Seletivo.md` (11 páginas). Fonte original preservada na raiz.
Projeto: **NVIDIA Startup AI Radar**, desenvolvido pelo Inteli Academy com a NVIDIA em junho/2026.
Esta é a adaptação para o Processo Seletivo.

---

## Contextualização do problema (por que o projeto existe)

Grandes laboratórios — OpenAI, Anthropic, Google DeepMind, Meta — deixaram de ser apenas
fornecedores de modelos fundacionais e subiram na cadeia de valor: hoje oferecem APIs
multimodais, agentes, produtividade, busca, voz, código, automação de workflows, memória,
integrações corporativas e produtos finais.

Isso cria **ameaça direta a startups que se posicionam apenas como wrappers de LLM** — quem só
conecta uma API a uma interface gráfica, sem dados proprietários, sem workflow profundo, sem
distribuição clara e sem otimização técnica, pode ser substituído por funcionalidade nativa dos labs.

A oportunidade é virar **AI-native service**: combinar software, agentes, dados proprietários,
automação e serviço especializado para entregar resultado de negócio ponta a ponta — vender um
resultado operacional aumentado por IA, não uma ferramenta SaaS.

**Onde entra a NVIDIA:** muitas startups usam IA, poucas otimizam a stack técnica. Founders
começam com APIs externas pela simplicidade e, ao crescer, enfrentam **custo, latência,
escalabilidade, governança, privacidade, avaliação, observabilidade e dependência de
fornecedores**. A stack NVIDIA leva de protótipo em API a sistema de produção.

> Essa lista de sete dores é o gatilho de recomendação. Ver `03-stack-nvidia.md`.

## Objetivo do sistema

1. Consultar e filtrar, a partir de base pré-populada, startups brasileiras com sinais de uso intensivo de IA
2. Estruturar e interpretar as informações públicas já coletadas
3. Avaliar possíveis gaps na stack de IA da empresa
4. Consultar base de conhecimento sobre tecnologias NVIDIA
5. Recomendar as tecnologias NVIDIA mais adequadas
6. Gerar briefing executivo para abordagem comercial, técnica e comunitária pelo NVIDIA Inception

## Escopo

**Dentro:** pipeline multi-agente que, a partir de uma consulta, recupera empresas relevantes,
estrutura o texto associado, classifica a maturidade AI-native, valida as evidências e consulta
uma base RAG de tecnologias NVIDIA para gerar recomendações personalizadas.

**Fora:** construção de crawlers, scrapers ou qualquer pipeline de coleta automatizada na web.
A base de startups pode já estar pronta. Enriquecimento por fontes externas é **opcional**.

Frontend é livre. O foco da avaliação está na arquitetura de IA, nos agentes, no raciocínio
sobre os dados, no RAG com reranking e na qualidade das recomendações.

---

## Os 8 agentes sugeridos (LangGraph)

O TAPI justifica o LangGraph sobre uma cadeia simples de prompts: permite modelar fluxo com
**estado, nós, transições condicionais, checkpoints, retry e intervenção humana**.

| Agente | Responsabilidade |
|---|---|
| **Query Planner** | transforma a consulta em linguagem natural em critérios de busca sobre a base (setor, porte, estágio, palavras-chave, sinais de IA) e define a estratégia de análise |
| **Retriever** | consulta a base pré-populada e seleciona empresas e documentos/evidências relevantes |
| **Extractor** | transforma conteúdo textual não estruturado (descrições, trechos de sites, notícias, vagas) em dados estruturados sobre a empresa e sua stack |
| **Startup Classifier** | classifica como **AI-native**, **AI-enabled** ou **non-AI** |
| **Evidence Validator** | valida se as afirmações extraídas têm evidências e fontes suficientes na base |
| **NVIDIA RAG** | consulta a base de conhecimento de tecnologias NVIDIA |
| **Recommendation** | cruza o perfil da startup com as tecnologias NVIDIA |
| **Briefing** | gera o relatório final para o gerente de Startups & VCs |

### Fluxo de alto nível

```
Consulta do usuário
  -> Query Planner Agent
  -> Retriever Agent (base pré-populada de startups)
  -> Extractor Agent
  -> Perfil estruturado da startup
  -> Startup Classifier Agent
  -> Evidence Validator Agent
  -> Diagnóstico de maturidade AI-native
  -> NVIDIA RAG Agent
  -> Reranker
  -> Recommendation Agent
  -> Briefing Agent
  -> Interface web
```

---

## Base de startups — schema mínimo sugerido

### Tabela `startups`
`id` · `nome` · `site` · `setor / vertical` · `estagio` (pre-seed, seed, série A, etc.) ·
`localizacao` · `descricao_curta` · `ano_fundacao` · `tamanho_time` (aproximado)

### Tabela `documentos` (1:N com startups)
`id` · `startup_id` · `tipo` (site institucional, blog, notícia, vaga, perfil de founder, release) ·
`titulo` · `conteudo_texto` (texto limpo, **não estruturado**) · `url_fonte` · `data_publicacao`

### Duas regras que o TAPI grifa

1. **`conteudo_texto` é não estruturado de propósito.** É sobre ele que o Extractor, o Classifier
   e o Evidence Validator devem trabalhar. Estruturar demais na base mata o trabalho dos agentes —
   e o avaliador percebe.
2. **Rastreabilidade é requisito duro.** *"Toda conclusão do sistema sobre uma startup precisa
   apontar para o documento que a sustenta."* Aparece duas vezes no documento (§5.2 e §5.5).

### Volume recomendado
**30 a 80 startups**, com **pelo menos 3 documentos por empresa**, e **diversidade de perfis**
(AI-native, AI-enabled e non-AI) para que a classificação seja de fato exercitada.
→ entre 90 e 240 documentos.

---

## Pipeline RAG — os 9 passos pedidos

1. Ingestão de documentos: blogs, documentações, vídeos transcritos, whitepapers, páginas oficiais
2. Limpeza e normalização do texto
3. **Chunking semântico** dos documentos
4. Geração de embeddings
5. Armazenamento em vector database
6. **Busca híbrida: vetorial + lexical**
7. **Reranking** dos trechos recuperados
8. Geração da resposta **com citações**
9. **Avaliação de qualidade da resposta**

> O passo 9 é o mais ignorado e o que mais separa nível 2 de nível 4 no critério 2.
> Entregar um harness de avaliação do RAG é evidência direta de "decisão técnica consciente".

**Tecnologias recomendadas (não obrigatórias):** Qdrant como banco vetorial — permitido usar
ChromaDB, Pinecone ou pgvector · PostgreSQL para dados estruturados · BM25 para busca lexical ·
Cohere Rerank para reranking.

---

## Base de conhecimento NVIDIA — as 16 tecnologias a incluir

Inception · NIM · NeMo · NeMo Guardrails · Triton Inference Server · TensorRT-LLM · RAPIDS ·
cuDF · cuML · CUDA · Riva · Omniverse · Isaac · Clara · Morpheus · AI Enterprise

Detalhamento técnico de cada uma em `03-stack-nvidia.md`.

## Motor de recomendação — exemplos de regra dados pelo TAPI

- LLM em atendimento ao cliente, mas só com APIs externas → **NIM, NeMo Guardrails, Triton** + benchmark de custo/latência
- Grandes volumes de dados tabulares → **RAPIDS, cuDF, cuML**
- Voz, call center ou transcrição → **Riva, NIM**
- Saúde → **Clara, MONAI, NIM, NeMo Guardrails, AI Enterprise**
- Robotics ou simulação → **Isaac, Omniverse**, GPUs NVIDIA
- Latência de inferência → **Triton, TensorRT-LLM**, batching
- Governança em agentes → **NeMo Guardrails**, avaliação com NeMo

### Os 7 campos obrigatórios do output

1. Tecnologias NVIDIA recomendadas
2. Justificativa **técnica**
3. Justificativa **de negócio**
4. Nível de prioridade
5. Complexidade de implementação
6. **Próxima ação sugerida para o time NVIDIA**
7. **Evidências usadas, com link para a fonte na base**

---

## Entregáveis

| # | Entregável | Descrição |
|---|---|---|
| 1 | Sistema multi-agente com LangGraph | agentes especializados para planejamento, recuperação, extração, classificação, validação de evidências, RAG e recomendação |
| 2 | RAG NVIDIA com reranking | base de conhecimento com materiais NVIDIA e recuperação com reranking e citações |
| 3 | Motor de recomendação | recomenda tecnologias NVIDIA a partir do perfil da startup |
| 4 | Interface web | dashboard ou app para consulta, visualização de empresas, recomendações e exportação de briefing |
| 5 | Diferencial do projeto | algo único, para diferenciação e destaque competitivo |

## Barema

Nota de 0 a 100. Soma ponderada: **pontuação = peso × (nível / 4)**.

| Nível | Significado |
|---|---|
| 0 | Não entregue ou não executa |
| 1 | Insuficiente — existe, mas não cumpre o requisito |
| 2 | Suficiente — cumpre o requisito mínimo |
| 3 | Bom — cumpre bem, com decisões técnicas conscientes |
| 4 | Excelente — supera o esperado, com profundidade e cuidado |

| # | Critério | Peso |
|---|---|---|
| 1 | Sistema multiagente com LangGraph | 20 |
| 2 | RAG NVIDIA com reranking | 20 |
| 3 | Motor de recomendação | 20 |
| 4 | Interface web | 5 |
| 5 | Vídeo de apresentação | 20 |
| 6 | Diferencial do projeto | 5 |
| 7 | Repositório e documentação | 10 |
| | **Total** | **100** |

### Critérios eliminatórios
- Entrega fora do prazo sem alinhamento prévio
- Ausência do vídeo de apresentação
- Projeto que não executa e cujo vídeo não demonstra funcionamento real
- Código integralmente gerado sem compreensão: o candidato precisa explicar as decisões de
  arquitetura do próprio projeto
- Plágio de outro projeto

### Sobre o vídeo (peso 20 — igual ao sistema multi-agente inteiro)
Duração **máxima de 7 minutos**. O aluno deve:
- explicar como realizou a **arquitetura dos seus agentes**
- explicar o **sistema RAG**
- **demonstrar na prática o projeto funcional** pela interface web

### Observação do TAPI
*"O uso de IA como ferramenta de desenvolvimento é permitido e esperado. O que se avalia é a
capacidade de tomar e defender decisões técnicas."*

## Data

**Entrega final do projeto: 09/09/2026 às 23:59.**
É a única data no documento — não há checkpoints intermediários.
O TAPI não informa canal de submissão nem se a entrega é individual ou em grupo
(a linguagem — "o candidato", "o aluno" — sugere individual).
