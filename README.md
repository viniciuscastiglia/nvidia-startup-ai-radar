# NVIDIA Startup AI Radar

Plataforma multi-agente que analisa startups brasileiras, diagnostica sua maturidade
**AI-native** e recomenda tecnologias NVIDIA adequadas ao perfil de cada empresa — gerando um
briefing executivo para apoiar a captação de startups para o **NVIDIA Inception**.

> **Status:** em desenvolvimento.
> Projeto do Processo Seletivo do **Inteli Academy** (2026), a partir do TAPI do case
> desenvolvido pela liga em parceria com a NVIDIA.
> Entrega: 09/09/2026.

---

## O problema

Os grandes laboratórios de IA — OpenAI, Anthropic, Google DeepMind, Meta — deixaram de ser
apenas fornecedores de modelos fundacionais e subiram na cadeia de valor: hoje entregam agentes,
busca, voz, código, automação de workflows e produtos finais.

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

A partir de uma consulta em linguagem natural, o sistema:

1. traduz a consulta em critérios de busca sobre uma base de startups brasileiras
2. recupera as empresas e os documentos públicos relevantes
3. extrai dados estruturados do texto não estruturado (sites, blogs, vagas, notícias)
4. classifica a maturidade da empresa — **AI-native**, **AI-enabled** ou **non-AI**
5. valida se cada afirmação tem evidência rastreável na base
6. consulta uma base RAG de tecnologias NVIDIA, com busca híbrida e reranking
7. cruza o perfil da empresa com as tecnologias adequadas aos gaps identificados
8. gera um briefing executivo com justificativa técnica, de negócio e próxima ação

Toda conclusão do sistema aponta para o documento que a sustenta.

## Arquitetura

```
Consulta do usuário
  → Query Planner Agent       consulta em linguagem natural → critérios de busca
  → Retriever Agent           seleciona empresas e evidências na base
  → Extractor Agent           texto bruto → perfil estruturado
  → Startup Classifier Agent  AI-native | AI-enabled | non-AI
  → Evidence Validator Agent  as afirmações têm fonte suficiente?
  → NVIDIA RAG Agent          consulta a base de conhecimento NVIDIA
  → Reranker
  → Recommendation Agent      cruza perfil × tecnologias
  → Briefing Agent            relatório final
  → Interface web
```

Orquestração em **LangGraph** — escolhido sobre uma cadeia simples de prompts pela necessidade
de estado compartilhado, transições condicionais, checkpoints e retry entre os agentes.

## Stack

| Camada | Tecnologia |
|---|---|
| Orquestração multi-agente | LangGraph |
| Dados estruturados | PostgreSQL |
| Busca vetorial | *a definir* |
| Busca lexical | BM25 |
| Embeddings e reranking | *a definir* |
| LLM | *a definir* |
| Interface | *a definir* |

As decisões de stack e suas justificativas são registradas em
[`projeto/decisoes.md`](projeto/decisoes.md).

## Estrutura do repositório

```
.
├── CLAUDE.md                    contexto carregado automaticamente pelo Claude Code
├── TAPI Processo Seletivo.md    especificação original do case
├── contexto/                    referência estável sobre o case
│   ├── 01-tapi.md               requisitos, schema, barema
│   ├── 02-rubrica-ai-native.md  critérios de classificação AI-native
│   ├── 03-stack-nvidia.md       as 16 tecnologias + mapa dor → tecnologia
│   ├── 04-ecossistema-br.md     fontes de dados brasileiras
│   └── 05-achados-e-decisoes.md achados do levantamento e questões em aberto
└── projeto/                     execução
    ├── plano.md                 sequência de trabalho
    ├── decisoes.md              log de decisões de arquitetura
    └── guia-de-trabalho.md      método de trabalho
```

## Como rodar

*Em breve.*

## Decisões de arquitetura

Cada decisão técnica do projeto está registrada em
[`projeto/decisoes.md`](projeto/decisoes.md), com a alternativa descartada e o motivo da escolha.

## Créditos

Case original desenvolvido pelos membros do **Inteli Academy** em parceria com a **NVIDIA**.
Esta é uma implementação independente feita para o processo seletivo da liga.
