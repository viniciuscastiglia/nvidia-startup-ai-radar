# Log de decisões de arquitetura

Registro append-only. **Uma entrada por decisão, escrita no momento em que ela é tomada.**

Este arquivo tem três usos, e é por isso que ele é o hábito de maior alavancagem do projeto:

- **Eliminatório nº 4** do barema — *"o candidato precisa explicar as decisões de arquitetura do
  próprio projeto"*
- **Vídeo** (peso 20) — é o roteiro pronto
- **Repositório e documentação** (peso 10) — vira a seção de arquitetura do README

## Formato

```
## D-NNN — Título curto
**Data:** DD/MM/AAAA
**Decisão:** o que foi escolhido.
**Alternativas descartadas:** o que mais estava na mesa.
**Motivo:** por que esta e não as outras. Qual o trade-off aceito.
**Reversível?** fácil / caro / irreversível — e o que dispararia a revisão.
```

O campo **Alternativas descartadas** é o mais importante: é literalmente a pergunta que o
avaliador vai fazer.

---

## D-001 — Python 3.12 em vez do 3.14 do sistema
**Data:** 22/08/2026
**Decisão:** ambiente conda dedicado com Python 3.12.
**Alternativas descartadas:** usar o `python3` do sistema (Anaconda, 3.14.6).
**Motivo:** 3.14 é recente demais para o ecossistema. Bibliotecas com dependências compiladas
(drivers de Postgres, tokenizers, clientes de vector DB) frequentemente ainda não publicaram
wheel para 3.14, o que força build a partir do fonte e custa horas de depuração que não têm nada
a ver com o projeto. 3.12 é a versão com melhor cobertura de wheels no ecossistema de IA hoje.
**Reversível?** Fácil — é só recriar o ambiente.

---

## D-002 — Provedor de LLM, embedding e rerank atrás de variáveis de ambiente
**Data:** 22/08/2026
**Decisão:** `src/config.py` expõe `LLM`, `EMBEDDING` e `RERANK` lidos do `.env`. Nenhum agente
conhece o nome "NVIDIA" — todos recebem `base_url` + `modelo`.
**Alternativas descartadas:** instanciar o cliente da NVIDIA direto em cada agente.
**Motivo:** o risco nº 1 do `plano.md` é os créditos grátis do build.nvidia.com não sustentarem
8 agentes rodando dezenas de vezes por dia. A abstração custa ~100 linhas hoje; descobrir no dia
04/09 que os créditos acabaram e ter que mexer em 8 agentes custa o projeto. Trade-off aceito:
uma camada de indireção que, se a NVIDIA funcionar bem, nunca será exercida.
**Reversível?** Fácil, mas a assimetria importa: adicionar depois é caro, remover é trivial.

---

## D-003 — `langchain-openai` como cliente, não `langchain-nvidia-ai-endpoints`
**Data:** 22/08/2026
**Decisão:** falar com a NVIDIA pelo cliente OpenAI, trocando só o `base_url`.
**Alternativas descartadas:** `langchain-nvidia-ai-endpoints`, o SDK oficial da integração.
**Motivo:** os endpoints NIM são OpenAI-compatible por design (`contexto/03` §1) — é literalmente
o argumento de venda do produto. Usar o cliente genérico (a) tira uma dependência, (b) faz o
código de D-002 funcionar com qualquer provedor sem `if`, e (c) demonstra no vídeo a própria tese
do NIM: "migrar não exige mudar código". Trade-off: perde-se açúcar sintático específico da NVIDIA.
**Reversível?** Fácil — é trocar a classe do cliente em um lugar só.

---

## D-004 — conda para o ambiente de desenvolvimento + `requirements.txt` pinado
**Data:** 22/08/2026 · fecha a pendência **P-07**
**Decisão:** ambiente conda `case-nvidia` (Python 3.12.13) para desenvolver, `requirements.txt`
com versões exatas (`pip freeze`) para reprodução.
**Alternativas descartadas:** `uv` (mais rápido, lockfile melhor) · Poetry (gestão de projeto
mais completa).
**Motivo:** `uv` não está instalado na máquina e ambos exigem que quem for avaliar instale um
gerenciador a mais antes de rodar o projeto. `requirements.txt` roda em qualquer Python. O critério
aqui não é elegância de tooling — é atrito de reprodução para o avaliador, que conta no critério 7.
Trade-off aceito: `requirements.txt` não é lockfile de verdade (não trava dependências transitivas
por hash).
**Reversível?** Fácil.

---

## D-005 — Smoke test como script versionado com asserções semânticas
**Data:** 22/08/2026
**Decisão:** `scripts/smoke_nvidia.py`, em HTTP cru, que além de checar HTTP 200 verifica: se a
dimensão Matryoshka pedida é a devolvida, se o embedding separa relevante de irrelevante **em
português**, se funciona **crosslingual** (consulta PT × passagem EN) e se o reranker coloca a
passagem certa no topo. Grava latências em `docs/smoke-nvidia.md`.
**Alternativas descartadas:** `curl` descartável no terminal · passar por `langchain-openai`.
**Motivo:** três razões. (1) Um teste que só checa 200 não prova nada útil — a pergunta real é se
o modelo funciona em português e entre idiomas, porque a base NVIDIA é em inglês e os documentos
das startups em português; se o crosslingual falhasse, a arquitetura do RAG mudaria. (2) HTTP cru
torna a falha inequívoca: é do endpoint, não da biblioteca. (3) Vira evidência reproduzível para
o avaliador e a fonte dos números de latência do vídeo.
**Reversível?** Irrelevante — é ferramenta de apoio, não arquitetura.

---

## D-006 — Fan-in do grafo por `defer=True`, retry e isolamento de erro por nó
**Data:** 22/08/2026
**Decisão:** usar quatro recursos do LangGraph 1.2 que uma chain de prompts não tem: `defer=True`
no nó de Briefing (só executa quando o run está terminando, ou seja, depois de todas as análises
paralelas), `retry_policy` por nó, `error_handler` por nó, e `cache_policy` em desenvolvimento.
**Alternativas descartadas:** arestas condicionais manuais contando quantas análises voltaram ·
try/except dentro de cada nó · nenhum cache.
**Motivo:** o TAPI justifica LangGraph por "estado, transições condicionais, checkpoints, retry e
intervenção humana". Se o projeto usa LangGraph só como executor linear, a escolha vira decorativa
e o critério 1 fica em nível 2. Cada recurso aqui resolve um problema concreto e diferente:
`defer` resolve o fan-in sem contador manual; `retry_policy` cobre falha transitória de LLM;
`error_handler` impede que uma startup com dado ruim derrube as outras quatro; `cache_policy`
evita queimar crédito re-rodando o mesmo nó em desenvolvimento — que amarra direto com o risco
nº 1 do `plano.md`.
**Reversível?** Fácil, um parâmetro por nó. Verificado na API do langgraph 1.2.11 instalado.

---

## Decisões pendentes

Levantadas em `contexto/05-achados-e-decisoes.md` §4, a serem fechadas na sessão 01:

| # | Decisão | Encaminhamento sugerido |
|---|---|---|
| P-01 | Provedor de LLM dos agentes | NVIDIA via build.nvidia.com — **validar créditos antes** |
| P-02 | Modelo de embedding e dimensão | `llama-3.2-nv-embedqa-1b-v2` (multilíngue, inclui português); dimensão Matryoshka a definir |
| P-03 | Reranker | NeMo Retriever `llama-3.2-nv-rerankqa-1b-v2` (grátis) vs Cohere Rerank (sugerido pelo TAPI, pago) vs cross-encoder local |
| P-04 | Banco vetorial | Qdrant vs pgvector — decidir olhando para como o BM25 da busca híbrida será implementado |
| P-05 | Topologia do grafo | pipeline por startup com fan-out (`Send`) vs processamento em lote |
| P-06 | Framework de frontend | vale 5 pontos; alvo é funcional e limpo |
| ~~P-07~~ | ~~Gerenciamento de dependências~~ | **resolvida em D-004** — conda + requirements.txt pinado |
| P-08 | Como o Postgres sobe para quem for avaliar | Postgres.app local vs docker-compose |
