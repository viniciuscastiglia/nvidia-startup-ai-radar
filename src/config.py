"""Configuração central: provedor de LLM, embedding e reranking.

DECISÃO DE ARQUITETURA (ver projeto/decisoes.md)
------------------------------------------------
O provedor fica atrás de variáveis de ambiente desde o primeiro commit. Não porque haja
dúvida sobre usar a NVIDIA — a coerência narrativa do case pede que se use — mas porque o
risco nº 1 do plano é os créditos grátis do build.nvidia.com não sustentarem 8 agentes
rodando dezenas de vezes por dia em desenvolvimento.

Se isso acontecer, trocar de provedor é editar duas linhas do `.env`, não refatorar 8 agentes.

O RISCO QUE ESTA COSTURA **NÃO** COBRE, E QUE JÁ ACONTECEU DUAS VEZES (D-013, D-046)
------------------------------------------------------------------------------------
O catálogo de preview do build.nvidia.com aposenta modelos com HTTP 410 em cadência de meses:
18/05/2026 matou os dois que o TAPI cita, 25/08/2026 matou os dois que os substituíram.

Para o LLM a costura funciona — o endpoint é OpenAI-compatible e o modelo é intercambiável.
Para o EMBEDDER ela não funciona: trocar o modelo muda o espaço vetorial e invalida o corpus
já indexado. Env var não é pin de dependência; um modelo é um serviço remoto, não um pacote
do `requirements.txt`.

E EM 27/08 A COSTURA NÃO BASTOU NEM PARA O RERANKING (D-064, D-068)
--------------------------------------------------------------------
Trocar o modelo só resolve se existir outro modelo. Na terceira morte não existia: o catálogo
não tem nenhum reranker. Por isso `ConfigRerank` ganhou `provedor` — a variável que faltava não
era o nome do modelo, era o nome de QUEM o hospeda.

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

    `dimensao` existe porque o embedder usa Matryoshka: o mesmo modelo devolve
    384/512/768/1024/2048 dimensões conforme o parâmetro. A escolha da dimensão é uma decisão
    medível — o harness de avaliação compara recall@k entre elas.

    ATENÇÃO: trocar `modelo` aqui NÃO é como trocar o LLM. O espaço vetorial é outro, então os
    381 vetores de `chunks_nvidia` viram lixo e o corpus precisa ser re-embedado
    (`scripts/reembedar.py`) e a régua re-medida. Ver D-046.
    """

    base_url: str
    api_key: str | None
    modelo: str
    dimensao: int


@dataclass(frozen=True)
class ConfigRerank:
    """Reranking (cross-encoder) — passo 7. O PROVEDOR é escolhido aqui (D-068).

    `provedor` existe porque o passo 7 já perdeu o fornecedor três vezes (D-013, D-046, D-064)
    e na terceira não sobrou substituto na NVIDIA: 9 sondagens de path x modelo, todas 404/410,
    e zero modelos com `rank` no nome entre os 83 do catálogo.

        cohere  -> produção. É o que o TAPI recomenda nominalmente (secão 5.3)
        nvidia  -> o que rodava até 27/08. Preservado como registro, NÃO funciona hoje
        nenhum  -> degradação graciosa: sem chave, o passo 7 sai do caminho e a resposta
                   vira a ordem da busca híbrida, que sozinha faz 95% r@1 e 100% r@3 (D-046)

    POR QUE `nenhum` NÃO É UMA LINHA A MAIS NO HARNESS DE ABLAÇÃO
    A tabela de `avaliar_rag.py` JÁ tem a linha sem rerank: são os motores `denso` e `hibrido`.
    O provedor `nenhum` não existe para medir nada — existe para que quem clonar o repositório
    sem chave nenhuma consiga rodar, que é a metade executável do eliminatório nº 3.

    O endpoint de ranking da NVIDIA NÃO é o mesmo path do chat/embedding — por isso `url`
    completa em vez de base_url + sufixo fixo. O Cohere tem path próprio e não usa `url`.
    """

    provedor: str
    url: str
    api_key: str | None
    modelo: str
    cohere_api_key: str | None
    cohere_modelo: str
    cohere_req_por_min: int


# Chave única: aceita NVIDIA_API_KEY (nome específico) ou LLM_API_KEY (nome neutro),
# para que trocar de provedor não exija renomear variável.
_API_KEY = _env("LLM_API_KEY") or _env("NVIDIA_API_KEY")

LLM = ConfigLLM(
    base_url=_env("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=_API_KEY,
    # Escolhido em 28/08 por ELIMINAÇÃO MEDIDA, não por preferência (D-067): dos 10
    # candidatos do catálogo sondados com chamada real, 7 deram 404, 1 alternou
    # HTTP 400 com timeout de 300 s, 1 responde em ~35 s e quebra no structured
    # output (HTTP 500). Este responde em ~650 ms e passa nos dois métodos.
    # `scripts/sondar_catalogo.py` refaz a sondagem inteira — o catálogo LISTA
    # modelos que não respondem, então a listagem nunca é a prova (D-070).
    modelo=_env("LLM_MODEL", "nvidia/nemotron-3-nano-30b-a3b"),
    temperatura=float(_env("LLM_TEMPERATURE", "0.1")),
)

EMBEDDING = ConfigEmbedding(
    base_url=_env("EMBEDDING_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key=_API_KEY,
    modelo=_env("EMBEDDING_MODEL", "nvidia/llama-nemotron-embed-vl-1b-v2"),
    dimensao=int(_env("EMBEDDING_DIM", "1024")),
)

RERANK = ConfigRerank(
    # Default `cohere` desde 28/08 (D-068). O provedor `nvidia` morreu em 27/08 e o
    # catálogo não tem substituto; o Cohere é o que o TAPI recomenda desde sempre, e
    # D-015 o descartou por "é pago" — afirmação FALSA, corrigida em D-065.
    provedor=_env("RERANK_PROVEDOR", "cohere"),
    url=_env("RERANK_URL", "https://ai.api.nvidia.com/v1/retrieval/nvidia/reranking"),
    api_key=_API_KEY,
    modelo=_env("RERANK_MODEL", "nvidia/rerank-qa-mistral-4b"),
    cohere_api_key=_env("COHERE_API_KEY"),
    cohere_modelo=_env("COHERE_RERANK_MODEL", "rerank-v3.5"),
    # Teto de requisições por minuto. Default 10 = o da TRIAL, medido em 28/08 e pior do
    # que a documentação sugere: o 429 chega na 4ª chamada sequencial, `retry-after` vem
    # AUSENTE, e a janela de recuperação medida foi de ~26 s. Quem tiver chave paga
    # (1.000 req/min) põe o número real aqui e o limitador some do caminho. 0 desliga.
    cohere_req_por_min=int(_env("COHERE_REQ_POR_MIN", "10")),
)

DATABASE_URL = _env("DATABASE_URL", "postgresql://localhost:5432/case_nvidia")

# Teto de startups analisadas por consulta. Existe por causa do fan-out: a topologia roda
# o pipeline de análise uma vez POR startup, então N startups = N x 5 chamadas de LLM.
# Este é o botão de controle de custo quando os créditos apertarem.
MAX_STARTUPS = int(_env("MAX_STARTUPS", "5"))


def tem_credencial() -> bool:
    return bool(_API_KEY)
