# Smoke test — build.nvidia.com

Gerado por `scripts/smoke_nvidia.py` em 08/09/2026 15:48.

| Capacidade | Resultado | Latência | Modelo |
|---|---|---|---|
| chat completion | passou | 6929 ms | `nvidia/nemotron-3.5-lightning-30b-a3b` |
| embedding | passou | 698 ms | `nvidia/llama-nemotron-embed-vl-1b-v2` |
| reranking | passou | 1581 ms | `rerank-v3.5` |

## Detalhes

### chat completion

```
modelo: nvidia/nemotron-3.5-lightning-30b-a3b
tokens: 37 prompt + 120 completion
resposta: Here's a thinking process:

1.  **Analyze User Input:**
   - **Constraint:** Respond in one short sentence in Portuguese
   - **Question:** "o que é o NVIDIA In
NOTA: o `content` cru comeca com o raciocinio do modelo. Isto e esperado (D-079) e NAO afeta a producao — `json_schema` devolve so o schema.
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
ordem: #1(0.2848) > #0(0.0152) > #2(0.0103)
topo = passagem #1 (correto — TensorRT-LLM é a resposta certa)
margem topo->2º: 0.2696 (relevance_score em [0,1] — as escalas NÃO se comparam entre provedores, D-068)
```
