# Smoke test — build.nvidia.com

Gerado por `scripts/smoke_nvidia.py` em 28/08/2026 07:56.

| Capacidade | Resultado | Latência | Modelo |
|---|---|---|---|
| chat completion | passou | 1484 ms | `nvidia/nemotron-3-nano-30b-a3b` |
| embedding | passou | 609 ms | `nvidia/llama-nemotron-embed-vl-1b-v2` |
| reranking | falhou | — | `nvidia/rerank-qa-mistral-4b` |

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
nenhum dos endpoints candidatos respondeu
```
