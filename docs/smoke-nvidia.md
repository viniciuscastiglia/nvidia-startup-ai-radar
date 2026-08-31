# Smoke test — build.nvidia.com

Gerado por `scripts/smoke_nvidia.py` em 31/08/2026 18:28.

| Capacidade | Resultado | Latência | Modelo |
|---|---|---|---|
| chat completion | passou | 1808 ms | `nvidia/nemotron-3-nano-30b-a3b` |
| embedding | passou | 592 ms | `nvidia/llama-nemotron-embed-vl-1b-v2` |
| reranking | passou | 1193 ms | `rerank-v3.5` |

## Detalhes

### chat completion

```
modelo: nvidia/nemotron-3-nano-30b-a3b
tokens: 37 prompt + 120 completion
resposta: O NVIDIA Inception é um programa de aceleração para startups de IA que oferece recursos, mentoria e suporte
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
