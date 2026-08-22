"""NVIDIA RAG — consulta a base de conhecimento das tecnologias NVIDIA.

STUB DA SESSÃO 01, e o mais "oco" dos oito de propósito: a base de conhecimento ainda não
existe. Ela é a M2 (26-30/08), com os 9 passos do pipeline que o TAPI pede — chunking semântico,
embeddings, busca híbrida, reranking, citação e avaliação.

O que este stub JÁ FAZ e que importa: devolve `CitacaoRAG` com os TRÊS scores separados
(denso, lexical, rerank). Guardar os três desde agora é o que permite, no vídeo, mostrar o
reranker mudando a ordem — e é o que o harness de avaliação do passo 9 vai medir. Se o formato
carregasse um score só, essa demonstração seria impossível sem refatorar.

A consulta é montada a partir das DORES que o Extractor observou, não do texto livre da
consulta do usuário. Ver contexto/03 §4: a dor é a chave de junção com a tabela de tecnologias.
"""

from __future__ import annotations

from src.state import CitacaoRAG, EstadoAnalise

# Placeholder até a M2. Os textos vieram de contexto/03 §1 e as URLs são as oficiais
# verificadas em 22/08 — mesmo no stub, citação aponta para fonte que resolve.
BASE_PROVISORIA: dict[str, tuple[str, str]] = {
    "custo": ("NVIDIA NIM", "https://www.nvidia.com/en-us/ai-data-science/products/nim-microservices/"),
    "latencia": ("TensorRT-LLM", "https://github.com/NVIDIA/TensorRT-LLM"),
    "escalabilidade": ("Triton Inference Server", "https://developer.nvidia.com/triton-inference-server"),
    "governanca": ("NeMo Guardrails", "https://github.com/NVIDIA/NeMo-Guardrails"),
    "privacidade": ("NVIDIA NIM", "https://www.nvidia.com/en-us/ai-data-science/products/nim-microservices/"),
    "avaliacao": ("NVIDIA NeMo", "https://www.nvidia.com/en-us/ai-data-science/products/nemo/"),
    "observabilidade": ("NVIDIA NeMo", "https://www.nvidia.com/en-us/ai-data-science/products/nemo/"),
    "dependencia_fornecedor": ("NVIDIA NIM", "https://www.nvidia.com/en-us/ai-data-science/products/nim-microservices/"),
}

TRECHOS = {
    "NVIDIA NIM": ("Containers pré-construídos que empacotam modelo, engine de inferência otimizada e "
                   "API OpenAI-compatible. Trocar o base_url do SDK é suficiente — o código não muda. "
                   "Benchmark citado: Llama 3.1 8B em H100 a 1.201 tokens/s contra 613 de baseline."),
    "TensorRT-LLM": ("Quantização FP8, FP4, INT8 e INT4-AWQ, speculative decoding com ~3x de throughput, "
                     "paged KV cache e reuso de KV cache."),
    "Triton Inference Server": ("Dynamic batching, execução concorrente de modelos e ensembles, com "
                                "métricas Prometheus. Hoje chamado Dynamo-Triton."),
    "NeMo Guardrails": ("Cinco tipos de rail entre a aplicação e o LLM, incluindo retrieval rail que "
                        "filtra chunks em cenário de RAG. Integra com LangChain."),
    "NVIDIA NeMo": ("Suíte agent-first: Curator, Evaluator (benchmark, LLM-as-judge, custom), "
                    "Customizer para fine-tuning e Relay para observabilidade de agentes."),
}


def node(state: EstadoAnalise) -> dict:
    perfil = state.get("perfil")
    if perfil is None:
        return {"citacoes_rag": []}

    citacoes: list[CitacaoRAG] = []
    vistos: set[str] = set()
    for dor in perfil.dores_observadas:
        alvo = BASE_PROVISORIA.get(dor.dor)
        if not alvo or alvo[0] in vistos:
            continue
        tecnologia, url = alvo
        vistos.add(tecnologia)
        citacoes.append(CitacaoRAG(
            tecnologia=tecnologia,
            trecho=TRECHOS.get(tecnologia, ""),
            url_fonte=url,
            # None e não 0.0: "ainda não medido" é diferente de "medido e deu zero".
            score_denso=None, score_lexical=None, score_rerank=None,
        ))
    return {"citacoes_rag": citacoes}
