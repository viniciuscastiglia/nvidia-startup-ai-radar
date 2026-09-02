# Smoke test — build.nvidia.com

Gerado por `scripts/smoke_nvidia.py` em 02/09/2026 08:40.

| Capacidade | Resultado | Latência | Modelo |
|---|---|---|---|
| chat completion | lento | 46830 ms | `nvidia/nemotron-3.5-lightning-30b-a3b` |
| embedding | passou | 598 ms | `nvidia/llama-nemotron-embed-vl-1b-v2` |
| reranking | passou | 248 ms | `rerank-v3.5` |

## Detalhes

### chat completion

```
modelo: nvidia/nemotron-3.5-lightning-30b-a3b
tokens: 37 prompt + 120 completion
resposta: Here's a thinking process:

1.  **Analyze User Input:**
   - **Language:** Portuguese
   - **Constraint:** One sentence only ("uma frase curta")
   - **Question
NOTA: o `content` cru comeca com o raciocinio do modelo. Isto e esperado (D-079) e NAO afeta a producao — `json_schema` devolve so o schema.
LENTO: 47 s contra ~10 s esperados. A capacidade EXISTE — isto nao e EOL.
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
