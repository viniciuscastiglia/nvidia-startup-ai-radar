<!-- Página 1 -->

Projeto: NVIDIA Startup AI Radar 
Processo Seletivo — Inteli Academy 
Sejam bem-vindos ao Processo Seletivo do Inteli Academy! 
 
O objetivo deste processo seletivo é proporcionar a vocês contato prático com as demandas e 
tecnologias trabalhadas dentro da liga. 
 
Neste documento, vocês terão acesso ao TAPI do projeto desenvolvido em parceria com a 
NVIDIA, realizado pelos membros do Inteli Academy em junho. O material contém todas as 
informações e orientações necessárias para o desenvolvimento. 
 
A entrega do Processo Seletivo será a implementação da própria versão desse projeto, 
seguindo o que está especificado neste TAPI. 
 
Nota sobre esta versão do TAPI: esta é uma adaptação do projeto original para o 
Processo Seletivo. A principal mudança é que não é necessário construir uma 
pipeline de scraping. Vocês podem montar uma base de startups já populada, e 
o foco da avaliação está na arquitetura multi-agente, no RAG com reranking, na 
qualidade das recomendações e na interface. 
 
Os entregáveis, barema e datas estão no final do documento. 
 
Boa Sorte! 
 
 
1. Contextualização do problema 
O mercado de inteligência artificial está passando por uma mudança estrutural. Grandes 
laboratórios como OpenAI, Anthropic, Google DeepMind, Meta e outros deixaram de atuar 
apenas como fornecedores de modelos fundacionais e passaram a subir na cadeia de valor.

---

<!-- Página 2 -->

Hoje, esses laboratórios oferecem APIs multimodais, agentes, ferramentas de produtividade, 
busca, voz, código, automação de workflows, memória, integrações corporativas e produtos 
finais para empresas. 
 
Esse movimento cria uma ameaça direta para startups de IA, principalmente para aquelas que 
se posicionam apenas como wrappers de LLMs. Uma startup que apenas conecta uma API da 
OpenAI, Anthropic ou outro provedor a uma interface gráfica, sem dados proprietários, sem 
workflow profundo, sem distribuição clara e sem otimização técnica, pode ser rapidamente 
substituída por funcionalidades nativas dos grandes labs. 
 
Ao mesmo tempo, surge uma oportunidade importante: startups podem se diferenciar ao se 
tornarem AI-native services. Nesse modelo, a empresa combina software, agentes de IA, dados 
proprietários, automação e serviço especializado para entregar resultados de negócio de ponta 
a ponta. Em vez de vender apenas uma ferramenta SaaS, a empresa passa a vender um 
resultado operacional aumentado por IA. 
 
Nesse contexto, a NVIDIA tem uma posição estratégica. Muitas startups usam IA, mas poucas 
otimizam toda a stack técnica. Em geral, founders começam usando APIs externas pela 
simplicidade, mas conforme crescem passam a enfrentar problemas de custo, latência, 
escalabilidade, governança, privacidade, avaliação, observabilidade e dependência de 
fornecedores. A stack da NVIDIA pode ajudar essas empresas a evoluir de protótipos baseados 
em APIs para sistemas de IA escaláveis, eficientes e preparados para produção. 
 
Este projeto propõe a construção de uma plataforma multi-agente capaz de analisar startups 
brasileiras a partir de uma base de dados pré-populada com informações públicas, 
diagnosticar sua maturidade técnica e recomendar tecnologias da NVIDIA adequadas ao perfil 
de cada empresa. A solução deve funcionar como uma ferramenta de inteligência para apoiar o 
gerente de Startups & VCs da NVIDIA no Brasil a atrair, qualificar e nutrir startups para o 
programa NVIDIA Inception. 
2. Objetivo do projeto 
Construir um sistema capaz de: 
 
-​
Consultar e filtrar, a partir de uma base pré-populada, startups brasileiras com sinais de 
uso intensivo de IA. 
-​
Estruturar e interpretar as informações públicas já coletadas sobre essas empresas. 
-​
Avaliar possíveis gaps na stack de IA da empresa. 
-​
Consultar uma base de conhecimento sobre tecnologias NVIDIA. 
-​
Recomendar as tecnologias NVIDIA mais adequadas para a startup analisada. 
-​
Gerar um briefing executivo para apoiar abordagem comercial, técnica e comunitária 
pelo NVIDIA Inception.

---

<!-- Página 3 -->

3. Pergunta norteadora 
Como a NVIDIA pode identificar, atrair e nutrir startups brasileiras AI-native em um 
contexto no qual os grandes labs de IA estão ameaçando startups que dependem apenas 
de wrappers de LLM? 
4. Escopo da solução 
O sistema deve possuir uma pipeline multi-agente que, a partir de uma consulta do usuário, 
deve recuperar empresas relevantes da base pré-populada, estruturar as informações 
textuais associadas a elas, classificar a maturidade AI-native da empresa, validar as evidências 
utilizadas e consultar uma base RAG com tecnologias NVIDIA para gerar recomendações 
personalizadas. 
 
Fora de escopo: construção de crawlers, scrapers ou qualquer pipeline de coleta 
automatizada de dados na web. A base de startups pode já estar pronta. Enriquecimento por 
fontes externas é opcional. 
 
O frontend fica livre para os alunos escolherem. O foco principal do projeto está na arquitetura 
de IA, nos agentes, no raciocínio sobre os dados, no RAG com reranking e na qualidade das 
recomendações. 
5. Tecnologias principais 
5.1 LangGraph 
LangGraph será utilizado para criar o sistema multi-agente. Diferentemente de uma cadeia 
simples de prompts, o LangGraph permite modelar um fluxo de trabalho com estado, nós, 
transições condicionais, checkpoints, retry, intervenção humana e controle mais robusto sobre o 
comportamento dos agentes. 
 
Agentes sugeridos: 
 
-​
Query Planner Agent: transforma a consulta em linguagem natural do usuário em 
critérios de busca sobre a base de startups (setor, porte, estágio, palavras-chave, sinais 
de IA) e define a estratégia de análise. 
-​
Retriever Agent: consulta a base pré-populada e seleciona as empresas e os 
documentos/evidências relevantes para a consulta. 
-​
Extractor Agent: transforma o conteúdo textual não estruturado da base (descrições, 
trechos de sites, notícias, vagas) em dados estruturados sobre a empresa e sua stack. 
-​
Startup Classifier Agent: classifica a empresa como AI-native, AI-enabled ou non-AI.

---

<!-- Página 4 -->

-​
Evidence Validator Agent: valida se as afirmações extraídas possuem evidências e 
fontes suficientes na base. 
-​
NVIDIA RAG Agent: consulta a base de conhecimento de tecnologias NVIDIA. 
-​
Recommendation Agent: cruza o perfil da startup com as tecnologias NVIDIA. 
-​
Briefing Agent: gera o relatório final para o gerente de Startups & VCs. 
 
 
5.2 Base de startups pré-populada 
Em vez de coletar dados na web, os alunos podem montar manualmente uma base com 
informações públicas já coletadas sobre startups brasileiras. Essa base é o ponto de partida da 
pipeline. 
 
Estrutura mínima sugerida: 
 
Tabela startups 
 
-​
id 
-​
nome 
-​
site 
-​
setor / vertical 
-​
estagio (pre-seed, seed, série A, etc.) 
-​
localizacao 
-​
descricao_curta 
-​
ano_fundacao 
-​
tamanho_time (aproximado) 
 
Tabela documentos (conteúdo textual bruto, um-para-muitos com startups) 
 
-​
id 
-​
startup_id 
-​
tipo (site institucional, blog, notícia, vaga, perfil de founder, release) 
-​
titulo 
-​
conteudo_texto (texto limpo, não estruturado) 
-​
url_fonte 
-​
data_publicacao 
 
O campo conteudo_texto é intencionalmente não estruturado: é sobre ele que o Extractor 
Agent, o Classifier Agent e o Evidence Validator Agent devem trabalhar. A rastreabilidade das 
afirmações via url_fonte continua sendo requisito — toda conclusão do sistema sobre uma 
startup precisa apontar para o documento que a sustenta.

---

<!-- Página 5 -->

Recomendação de volume: entre 30 e 80 startups, com pelo menos 3 documentos por 
empresa, e diversidade de perfis (AI-native, AI-enabled e non-AI) para que a classificação seja 
de fato exercitada. 
 
 
5.3 RAG com reranking 
O RAG será usado para armazenar e consultar conhecimentos sobre tecnologias NVIDIA, 
conceitos de AI-native services, stack de IA, NVIDIA Inception e materiais de apoio. 
 
Pipeline recomendada: 
 
1.​ Ingestão de documentos: blogs, documentações, vídeos transcritos, whitepapers e 
páginas oficiais. 
2.​ Limpeza e normalização do texto. 
3.​ Chunking semântico dos documentos. 
4.​ Geração de embeddings. 
5.​ Armazenamento em vector database. 
6.​ Busca híbrida: busca vetorial + busca lexical. 
7.​ Reranking dos trechos recuperados. 
8.​ Geração da resposta com citações. 
9.​ Avaliação de qualidade da resposta. 
 
Tecnologias recomendadas: 
 
-​
Qdrant, mas é permitido o uso de outros bancos como ChromaDB, Pinecone ou 
pgvector como banco vetorial. 
-​
PostgreSQL para dados estruturados de empresas. 
-​
BM25 para busca lexical. 
-​
Cohere Rerank para a estratégia de reranking. 
5.4 Base de conhecimento NVIDIA 
A base de conhecimento deve conter informações sobre tecnologias NVIDIA e seus casos de 
uso. O objetivo é permitir que o sistema recomende a tecnologia certa com base no problema 
identificado na startup. 
 
Tecnologias NVIDIA a incluir: 
 
-​
NVIDIA Inception: programa para startups, benefícios, comunidade, credits, suporte 
técnico e go-to-market. 
-​
NVIDIA NIM: microservices para deploy de modelos de IA otimizados.

---

<!-- Página 6 -->

-​
NVIDIA NeMo: treinamento, customização, avaliação e guardrails para modelos 
generativos. 
-​
NeMo Guardrails: controle de comportamento de assistentes e agentes. 
-​
NVIDIA Triton Inference Server: serving de modelos em produção. 
-​
TensorRT-LLM: otimização de inferência de LLMs. 
-​
NVIDIA RAPIDS: aceleração de pipelines de dados com GPU. 
-​
cuDF: processamento de dataframes em GPU. 
-​
cuML: machine learning acelerado em GPU. 
-​
CUDA: programação paralela em GPU. 
-​
NVIDIA Riva: ASR, TTS e modelos de voz. 
-​
NVIDIA Omniverse: simulação, 3D e digital twins. 
-​
NVIDIA Isaac: robotics, simulação e autonomia. 
-​
NVIDIA Clara: healthcare e life sciences. 
-​
NVIDIA Morpheus: cybersecurity com IA acelerada. 
-​
NVIDIA AI Enterprise: plataforma empresarial para IA em produção. 
5.5 Motor de recomendação 
O motor de recomendação deve cruzar o perfil da empresa com os possíveis gaps técnicos 
identificados. 
 
Exemplos de recomendação: 
 
-​
Se a startup usa LLMs em atendimento ao cliente, mas depende apenas de APIs 
externas: recomendar NIM, NeMo Guardrails, Triton e benchmark de custo/latência. 
-​
Se a startup processa grandes volumes de dados tabulares: recomendar RAPIDS, cuDF 
e cuML. 
-​
Se a startup faz voz, call center ou transcrição: recomendar NVIDIA Riva e NIM. 
-​
Se a startup atua em saúde: considerar Clara, MONAI, NIM, NeMo Guardrails e AI 
Enterprise. 
-​
Se a startup faz robotics ou simulação: recomendar Isaac, Omniverse e GPUs NVIDIA. 
-​
Se a startup sofre com latência de inferência: recomendar Triton, TensorRT-LLM e 
batching. 
-​
Se a startup precisa de governança em agentes: recomendar NeMo Guardrails e 
avaliação com NeMo. 
 
O output da recomendação deve conter: 
 
-​
Tecnologias NVIDIA recomendadas. 
-​
Justificativa técnica. 
-​
Justificativa de negócio. 
-​
Nível de prioridade. 
-​
Complexidade de implementação.

---

<!-- Página 7 -->

-​
Próxima ação sugerida para o time NVIDIA. 
-​
Evidências usadas (com link para a fonte na base). 
6. Arquitetura proposta 
Fluxo de alto nível: 
 
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
7. Origem dos dados da base de startups 
As fontes abaixo são as que originaram os dados da base entregue. A lista serve como 
referência de contexto e para eventual conferência manual de uma evidência. 
7.1 Fontes principais no Brasil 
-​
Sites oficiais das startups 
-​
Blogs oficiais das startups 
-​
Páginas de carreiras das startups 
-​
Perfis públicos de founders 
-​
StartSe: https://www.startse.com/ 
-​
Distrito: https://distrito.me/ 
-​
Latitud: https://www.latitud.com/ 
-​
Cubo Itaú: https://cubo.network/ 
-​
ACE Startups: https://acestartups.com.br/ 
-​
Endeavor Brasil: https://endeavor.org.br/ 
-​
Abstartups: https://abstartups.com.br/ 
-​
Bossa Invest: https://bossainvest.com/ 
-​
Anjos do Brasil: https://www.anjosdobrasil.net/ 
-​
Darwin Startups: https://www.darwinstartups.com/

---

<!-- Página 8 -->

-​
Liga Ventures: https://liga.ventures/ 
-​
WOW Aceleradora: https://www.wow.ac/ 
-​
InovAtiva Brasil: https://www.inovativabrasil.com.br/ 
-​
100 Open Startups: https://www.openstartups.net/ 
7.2 Fontes de notícias e sinais públicos 
-​
Brazil Journal: https://braziljournal.com/ 
-​
NeoFeed: https://neofeed.com.br/ 
-​
Exame Startups: https://exame.com/bussola/startups/ 
-​
Startups.com.br: https://startups.com.br/ 
-​
Pequenas Empresas & Grandes Negócios: https://revistapegn.globo.com/ 
-​
Valor Econômico: https://valor.globo.com/ 
-​
Meio & Mensagem: https://www.meioemensagem.com.br/ 
-​
Mobile Time: https://www.mobiletime.com.br/ 
8. Fontes para base de conhecimento NVIDIA 
8.1 Materiais de apoio do case 
-​
Sequoia — AI services: https://sequoiacap.com/article/services-the-new-software/ 
-​
Emergence Capital — AI-native services playbook: 
https://www.emcap.com/thoughts/the-ai-native-services-playbook 
-​
NVIDIA AI 5-layer cake: https://blogs.nvidia.com/blog/ai-5-layer-cake/ 
-​
Playlist de tecnologias NVIDIA: 
https://youtube.com/playlist?list=PLBaUJRFQ-j_WJZdZfFNsgUWDWF1Ldjp_X 
-​
Comunidade startups NVIDIA: https://youtu.be/NmZDQSdUVUQ 
-​
Benefícios Inception: https://www.youtube.com/live/fWfkE6cibwQ 
8.2 Documentações oficiais NVIDIA 
-​
NVIDIA Inception: https://www.nvidia.com/en-us/startups/ 
-​
NVIDIA NIM: https://www.nvidia.com/en-us/ai-data-science/products/nim-microservices/ 
-​
NVIDIA API Catalog: https://build.nvidia.com/ 
-​
NVIDIA NeMo: https://www.nvidia.com/en-us/ai-data-science/products/nemo/ 
-​
NeMo Guardrails: https://github.com/NVIDIA/NeMo-Guardrails 
-​
NVIDIA Triton Inference Server: https://developer.nvidia.com/triton-inference-server 
-​
Triton docs: 
https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/ 
-​
TensorRT-LLM: https://github.com/NVIDIA/TensorRT-LLM 
-​
NVIDIA RAPIDS: https://rapids.ai/ 
-​
cuDF: https://docs.rapids.ai/api/cudf/stable/ 
-​
cuML: https://docs.rapids.ai/api/cuml/stable/

---

<!-- Página 9 -->

-​
CUDA Toolkit: https://developer.nvidia.com/cuda-toolkit 
-​
NVIDIA Riva: https://developer.nvidia.com/riva 
-​
NVIDIA Omniverse: https://www.nvidia.com/en-us/omniverse/ 
-​
NVIDIA Isaac: https://developer.nvidia.com/isaac 
-​
NVIDIA Clara: https://www.nvidia.com/en-us/clara/ 
-​
NVIDIA Morpheus: https://developer.nvidia.com/morpheus-cybersecurity 
-​
NVIDIA AI Enterprise: https://www.nvidia.com/en-us/data-center/products/ai-enterprise/ 
9. Entregáveis esperados 
 
 
Entregável 1 — Sistema multi-agente com LangGraph Sistema com agentes especializados 
para planejamento da consulta, recuperação na base, extração, classificação, validação de 
evidências, RAG e recomendação.  
 
Entregável 2 — RAG NVIDIA com reranking Base de conhecimento contendo materiais 
NVIDIA e mecanismo de recuperação com reranking e citações. 
 
Entregável 3 — Motor de recomendação Sistema que recomenda tecnologias NVIDIA a partir 
do perfil da startup. 
 
Entregável 4 — Interface web Dashboard ou aplicação web para consulta, visualização de 
empresas, recomendações e exportação de briefing. 
 
Entregável 5 — Diferencial do projeto Desenvolver algo único no seu projeto, para fins de 
diferenciação e destaque competitivo. 
 
 
 
10. Barema e datas 
 
 
A nota final vai de 0 a 100 e é composta pela soma ponderada dos critérios abaixo. Cada 
critério é avaliado em uma escala de nível, e a pontuação é peso × (nível / 4). 
Escala de níveis 
Nível 
Significado

---

<!-- Página 10 -->

0 
Não entregue ou não executa 
1 
Insuficiente — existe, mas não cumpre o requisito 
2 
Suficiente — cumpre o requisito mínimo 
3 
Bom — cumpre bem, com decisões técnicas conscientes 
4 
Excelente — supera o esperado, com profundidade e 
cuidado 
 
Distribuição de pesos 
# 
Critério 
Peso 
1 Sistema multiagente com LangGraph 
20 
2 RAG NVIDIA com reranking 
20 
3 Motor de recomendação 
20 
4 Interface web 
5 
5 Vídeo de apresentação 
20 
6 Diferencial do projeto 
5 
7 Repositório e documentação 
10 
 
Total 
100 
 
 
Critérios eliminatórios 
●​ Entrega fora do prazo sem alinhamento prévio. 
●​ Ausência do vídeo de apresentação. 
●​ Projeto que não executa e cujo vídeo não demonstra funcionamento real. 
●​ Código integralmente gerado sem compreensão: o candidato precisa explicar as 
decisões de arquitetura do próprio projeto. 
●​ Plágio de outro projeto.

---

<!-- Página 11 -->

Sobre o vídeo 
O vídeo deve ter duração máxima de até 7 minutos, e o aluno deve explicar como realizou a 
arquitetura dos seus agentes e sistema rag, além de demonstrar na prática o projeto funcional 
por meio da interface web.  
 
Observação 
O uso de IA como ferramenta de desenvolvimento é permitido e esperado. O que se avalia é a 
capacidade de tomar e defender decisões técnicas. 
 
Datas 
 
Entrega Final do Projeto: 09/09 às 23:59h