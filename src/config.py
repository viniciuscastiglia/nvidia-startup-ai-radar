"""Configuração central: provedor de LLM, embedding e reranking.

DECISÃO DE ARQUITETURA (ver projeto/decisoes.md)
------------------------------------------------
O provedor fica atrás de variáveis de ambiente desde o primeiro commit. Não porque haja
dúvida sobre usar a NVIDIA — a coerência narrativa do case pede que se use — mas porque o
risco nº 1 do plano é os créditos grátis do build.nvidia.com não sustentarem 8 agentes
rodando dezenas de vezes por dia em desenvolvimento.

Se isso acontecer, trocar de provedor é editar duas linhas do `.env`, não refatorar 8 agentes.

Isso só é possível porque os endpoints NIM da NVIDIA são OpenAI-compatible: mesmo payload,
mesmo formato de resposta, só muda o `base_url`. Ver contexto/03-stack-nvidia.md §1.
É também a razão de usarmos `langchain-openai` em vez de `langchain-nvidia-ai-endpoints`:
uma dependência a menos, e o mesmo código serve de fallback para qualquer outro provedor.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")


def _env(chave: str, padrao: str | None = None) -> str | None:
    valor = os.getenv(chave, padrao)
    return valor.strip() if isinstance(valor, str) else valor


@dataclass(frozen=True)
class ConfigLLM:
    """Chat completions. Endpoint OpenAI-compatible."""

    base_url: str
    api_key: str | None
    modelo: str
    temperatura: float


@dataclass(frozen=True)
class ConfigEmbedding:
    """Embeddings via NeMo Retriever.

    `dimensao` existe porque o llama-3.2-nv-embedqa-1b-v2 usa Matryoshka: o mesmo modelo
    devolve 384/512/768/1024/2048 dimensões conforme o parâmetro. A escolha da dimensão é
    uma decisão medível — o harness de avaliação da M2 compara recall@k entre elas.
    """

    base_url: str
    api_key: str | None
    modelo: str
    dimensao: int


@dataclass(frozen=True)
class ConfigRerank:
    """Reranking (cross-encoder).

    O endpoint de ranking NÃO é o mesmo path do chat/embedding — por isso `url` completa
    em vez de base_url + sufixo fixo. O smoke test confirma qual path responde.
    """

    url: str
    api_key: str | None
    modelo: str


# Chave única: aceita NVIDIA_API_KEY (nome específico) ou LLM_API_KEY (nome neutro),
# para que trocar de provedor não exija renomear variável.
_API_KEY = _env("LLM_API_KEY") or _env("NVIDIA_API_KEY")

LLM = ConfigLLM(
    base_url=_env("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=_API_KEY,
    modelo=_env("LLM_MODEL", "meta/llama-3.1-8b-instruct"),
    temperatura=float(_env("LLM_TEMPERATURE", "0.1")),
)

EMBEDDING = ConfigEmbedding(
    base_url=_env("EMBEDDING_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=_API_KEY,
    modelo=_env("EMBEDDING_MODEL", "nvidia/llama-nemotron-embed-1b-v2"),
    dimensao=int(_env("EMBEDDING_DIM", "1024")),
)

RERANK = ConfigRerank(
    url=_env("RERANK_URL", "https://ai.api.nvidia.com/v1/retrieval/nvidia/llama-nemotron-rerank-1b-v2/reranking"),
    api_key=_API_KEY,
    modelo=_env("RERANK_MODEL", "nvidia/llama-nemotron-rerank-1b-v2"),
)

DATABASE_URL = _env("DATABASE_URL", "postgresql://localhost:5432/case_nvidia")

# Teto de startups analisadas por consulta. Existe por causa do fan-out: a topologia roda
# o pipeline de análise uma vez POR startup, então N startups = N x 5 chamadas de LLM.
# Este é o botão de controle de custo quando os créditos apertarem.
MAX_STARTUPS = int(_env("MAX_STARTUPS", "5"))


def tem_credencial() -> bool:
    return bool(_API_KEY)
