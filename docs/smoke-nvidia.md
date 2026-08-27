# Smoke test — build.nvidia.com

Gerado por `scripts/smoke_nvidia.py` em 27/08/2026 13:49.

| Capacidade | Resultado | Latência | Modelo |
|---|---|---|---|
| chat completion | falhou | — | `meta/llama-3.1-8b-instruct` |
| embedding | passou | 668 ms | `nvidia/llama-nemotron-embed-vl-1b-v2` |
| reranking | falhou | — | `nvidia/rerank-qa-mistral-4b` |

## Detalhes

### chat completion

```
HTTPStatusError: Client error '410 Gone' for url 'https://integrate.api.nvidia.com/v1/chat/completions'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/410
```

### embedding

```
dimensão pedida 1024 -> devolvida 1024 (bate)
PT  relevante 0.3456 vs irrelevante 0.0069 (ok)
EN  crosslingual 0.3844 vs irrelevante PT 0.0069 (ok)
```

### reranking

```
nenhum dos endpoints candidatos respondeu
```
