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
| P-07 | Gerenciamento de dependências | pip + requirements vs uv vs poetry |
| P-08 | Como o Postgres sobe para quem for avaliar | Postgres.app local vs docker-compose |
