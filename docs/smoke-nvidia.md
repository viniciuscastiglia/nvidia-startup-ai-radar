# Smoke test — build.nvidia.com

Gerado por `scripts/smoke_nvidia.py` em 28/08/2026 08:21.

| Capacidade | Resultado | Latência | Modelo |
|---|---|---|---|
| chat completion | passou | 1451 ms | `nvidia/nemotron-3-nano-30b-a3b` |
| embedding | passou | 615 ms | `nvidia/llama-nemotron-embed-vl-1b-v2` |
| reranking | passou | — | `nvidia/rerank-qa-mistral-4b` |

## Detalhes

### chat completion

```
modelo: nvidia/nemotron-3-nano-30b-a3b
tokens: 37 prompt + 120 completion
resposta: O NVIDIA Inception é um programa de aceleração de startups focado em IA, que ofere
```

### embedding

```
dimensão pedida 1024 -> devolvida 1024 (bate)
PT  relevante 0.3456 vs irrelevante 0.0069 (ok)
EN  crosslingual 0.3844 vs irrelevante PT 0.0069 (ok)
```

### reranking

```
RERANK_PROVEDOR=nenhum: o passo 7 sai do caminho de propósito e a resposta
vira a ordem da busca híbrida (95% r@1, 100% r@3 — D-046). Não é falha.
```
