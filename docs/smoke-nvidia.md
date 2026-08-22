# Smoke test — build.nvidia.com

Gerado por `scripts/smoke_nvidia.py` em 22/08/2026 16:32.

| Capacidade | Resultado | Latência | Modelo |
|---|---|---|---|
| chat completion | passou | 755 ms | `meta/llama-3.1-8b-instruct` |
| embedding | passou | 593 ms | `nvidia/llama-nemotron-embed-1b-v2` |
| reranking | passou | 520 ms | `nvidia/llama-nemotron-rerank-1b-v2` |

## Detalhes

### chat completion

```
modelo: meta/llama-3.1-8b-instruct
tokens: 57 prompt + 38 completion
resposta: O NVIDIA Inception é um programa de aceleração de startups que oferece recursos, suporte e conectividade para empresas inovadoras que utilizam tecnologias NVIDI
```

### embedding

```
dimensão pedida 1024 -> devolvida 1024 (bate)
PT  relevante 0.3546 vs irrelevante 0.0049 (ok)
EN  crosslingual 0.4280 vs irrelevante PT 0.0049 (ok)
```

### reranking

```
endpoint que respondeu: https://ai.api.nvidia.com/v1/retrieval/nvidia/llama-nemotron-rerank-1b-v2/reranking
ordem: #1(-1.85) > #0(-14.79) > #2(-20.48)
topo = passagem #1 (correto — TensorRT-LLM é a resposta certa)
margem topo->2º: 12.94
```
