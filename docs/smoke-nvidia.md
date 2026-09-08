# Smoke test — build.nvidia.com

Gerado por `scripts/smoke_nvidia.py` em 08/09/2026 09:21.

| Capacidade | Resultado | Latência | Modelo |
|---|---|---|---|
| chat completion | lento | — | `nvidia/nemotron-3.5-lightning-30b-a3b` |
| embedding | passou | 597 ms | `nvidia/llama-nemotron-embed-vl-1b-v2` |
| reranking | passou | 259 ms | `rerank-v3.5` |

## Detalhes

### chat completion

```
modelo: nvidia/nemotron-3.5-lightning-30b-a3b
a chamada direta falhou: ReadTimeout (teto 120 s)
diagnostico: VIVO-LENTO — HTTP 200 — primeiro token em 191 s. O modelo esta VIVO; o que estourou foi o relogio, nao o catalogo.
-> NAO MIGRE. Subir LLM_TIMEOUT, ou aceitar a latencia e planejar o video com ela.
```

### embedding

```
dimensão pedida 1024 -> devolvida 1024 (bate)
PT  relevante 0.3456 vs irrelevante 0.0069 (ok)
EN  crosslingual 0.3844 vs irrelevante PT 0.0069 (ok)
```

### reranking

```
provedor: cohere · modelo: rerank-v3.5
ordem: #1(0.2849) > #0(0.0152) > #2(0.0104)
topo = passagem #1 (correto — TensorRT-LLM é a resposta certa)
margem topo->2º: 0.2698 (relevance_score em [0,1] — as escalas NÃO se comparam entre provedores, D-068)
```
