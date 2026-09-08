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
    timeout: float


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
    sem chave nenhuma consiga rodar, em vez de receber um stack trace na primeira consulta.

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


# Chave COMPARTILHADA da conta NVIDIA: serve embedding e rerank, que são da NVIDIA
# independentemente de quem serve o chat. Aceita LLM_API_KEY por compatibilidade com
# quem já tinha o .env antigo, mas o nome correto para ela é NVIDIA_API_KEY.
_API_KEY = _env("NVIDIA_API_KEY") or _env("LLM_API_KEY")

LLM = ConfigLLM(
    base_url=_env("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    # SÓ DO LLM, e é por isso que não é `_API_KEY` direto (06/09). O comentário antigo dizia
    # que `LLM_API_KEY` existia "para que trocar de provedor não exija renomear variável" —
    # mas ela alimentava os TRÊS clientes, então apontar o chat para outro provedor levava
    # embedding e rerank junto, e a busca densa morria com 401 do lado da NVIDIA. Provado por
    # execução: com `LLM_API_KEY=x`, `EMBEDDING.api_key` também virava `x`. O fallback para
    # `_API_KEY` mantém o caso de um provedor único funcionando sem tocar no .env.
    api_key=_env("LLM_API_KEY") or _API_KEY,
    # Escolhido em 01/09 por ELIMINAÇÃO MEDIDA, não por preferência (D-079): 1 vivo de 10
    # sondados, e passa na pergunta-armadilha de D-047 nos dois métodos.
    # `scripts/sondar_catalogo.py` refaz a sondagem inteira — o catálogo LISTA
    # modelos que não respondem, então a listagem nunca é a prova (D-070).
    #
    # LATÊNCIA, MEDIDA EM 02/09 (D-080): mediana 51 s, faixa 17-88 s, em 8 chamadas reais pelo
    # caminho de produção. A versão anterior deste comentário dizia "responde em ~650 ms" — era
    # verdade em 01/09 e ficou falsa em 24 h. É a razão de `LLM_TIMEOUT` ter subido para 120, e
    # a razão de o smoke ter passado a distinguir LENTO de MORTO: com 30 s, 5 de 8 chamadas
    # estouravam a primeira tentativa e o instrumento chamava isso de falha.
    modelo=_env("LLM_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b"),
    temperatura=float(_env("LLM_TEMPERATURE", "0.1")),
    # Teto POR TENTATIVA, não por chamada: o `ChatOpenAI` traz `max_retries=2` do LangChain,
    # que fica como está. Está aqui e não no `src/llm.py` porque tudo que o cliente lê vem daqui.
    #
    # 30 -> 120 EM 02/09 (D-080), E O MOTIVO É MEDIÇÃO, NÃO PRECAUÇÃO. Com 30 s, 5 de 8 chamadas
    # reais estouram a PRIMEIRA tentativa e só completam pelo retry: a mediana medida foi 51 s,
    # faixa 17-88 s, e uma chamada de 88 s é 30 (falha) + 30 (falha) + ~28 (sucesso). O timeout
    # curto não protegia de nada — ele TRIPLICAVA o relógio de cada chamada lenta e escondia a
    # latência real atrás de retries silenciosos. Com 120 s cada chamada é uma tentativa só.
    #
    # 120 -> 300 EM 08/09 (D-116), PELO MESMO ARGUMENTO E COM O MODELO 4x MAIS LENTO.
    # Medido hoje, n=3 pelo caminho de produção: **mediana 216,9 s · faixa 186,5-240,8 s**.
    # A faixa inteira está ACIMA do teto de 120, então TODA tentativa estourava e a chamada só
    # terminava quando os 3 retries se esgotavam — exatamente o defeito que D-080 consertou,
    # voltando por deriva do fornecedor em vez de por escolha.
    #
    # E ele não era teórico: `POST /api/perguntar` devolvia **HTTP 500 depois de 363 s**
    # (= 3 x 120), com `OpenAITimeoutError` no log, num modelo que estava VIVO. O passo 8 do
    # TAPI — a porta da abstenção — estava inacessível por um número de configuração.
    #
    # 300 e não 250: o máximo medido foi 240,8 s, e um teto colado no máximo observado volta a
    # falhar no primeiro dia pior. 300 dá ~25% de folga sobre o pior caso de hoje.
    #
    # O CUSTO, DECLARADO: com `max_retries=2`, uma chamada de fato pendurada agora leva 900 s
    # para desistir, contra 360. É o preço de não abortar chamada viva, e a assimetria é a mesma
    # de D-080 — desistir de resposta que ia chegar é erro silencioso; demorar é erro visível.
    # Mexer no número de retries é OUTRA decisão e não entra junto.
    timeout=float(_env("LLM_TIMEOUT", "300")),
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
