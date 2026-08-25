# Smoke test — build.nvidia.com

Gerado por `scripts/smoke_nvidia.py` em 25/08/2026 09:39.

| Capacidade | Resultado | Latência | Modelo |
|---|---|---|---|
| chat completion | passou | 1038 ms | `meta/llama-3.1-8b-instruct` |
| embedding | passou | 599 ms | `nvidia/llama-nemotron-embed-vl-1b-v2` |
| reranking | passou | 630 ms | `nvidia/rerank-qa-mistral-4b` |

## Detalhes

### chat completion

```
modelo: meta/llama-3.1-8b-instruct
tokens: 57 prompt + 62 completion
resposta: O NVIDIA Inception é um programa de aceleração de startups que oferece recursos, suporte e tecnologia para ajudar as empresas a desenvolver soluções inovadoras 
```

### embedding

```
dimensão pedida 1024 -> devolvida 1024 (bate)
PT  relevante 0.3456 vs irrelevante 0.0069 (ok)
EN  crosslingual 0.3844 vs irrelevante PT 0.0069 (ok)
```

### reranking

```
endpoint que respondeu: https://ai.api.nvidia.com/v1/retrieval/nvidia/reranking
ordem: #1(-4.39) > #2(-15.30) > #0(-16.50)
topo = passagem #1 (correto — TensorRT-LLM é a resposta certa)
margem topo->2º: 10.90
```
