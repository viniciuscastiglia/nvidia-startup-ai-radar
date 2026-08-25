"""Passo 7 do pipeline RAG do TAPI: reranking dos trechos recuperados. Ver D-015, D-034 e D-038.

O QUE O CROSS-ENCODER FAZ QUE O BI-ENCODER NÃO FAZ
---------------------------------------------------
O embedder vetoriza consulta e passagem SEPARADAMENTE e compara os vetores: a passagem nunca
"viu" a pergunta. O cross-encoder recebe o par `(consulta, passagem)` numa entrada só e pontua a
relevância olhando os dois juntos. Custa uma chamada por par — inviável sobre 177 chunks, natural
sobre os 20 que a recuperação já filtrou. É por isso que reranking é passo 7 e não passo 6.

ELE LÊ `texto_indexado`, COM O BREADCRUMB (D-038)
--------------------------------------------------
Medido: `texto` e `texto_indexado` empatam em recall@1 (18/19), mas o breadcrumb sobe o logit do
chunk-âncora em 9 das 17 perguntas — q03 +3,70→+7,39, q13 +3,98→+9,10, q05 −4,55→−1,71.
Reranquear o texto puro descartaria no passo 7 exatamente a correção feita no passo 3: o chunk que
responde a q19 cita "TensorRT-LLM" com destaque e nunca repete "NIM", e é o breadcrumb
`NVIDIA NIM > ...` que diz ao cross-encoder de que produto aquilo fala.

DOIS FATOS MEDIDOS QUE LIMITAM O QUE SE PODE CONSTRUIR SOBRE O LOGIT (D-034, D-046)
------------------------------------------------------------------------------------
Os dois números abaixo são do `rerank-qa-mistral-4b`, medidos em 25/08 depois de o
`llama-nemotron-rerank-1b-v2` morrer com HTTP 410. Os valores de D-034 eram do 1B e não
transferem — a escala de logit de um 4B é outra.

1. **A janela é de ~6.958 tokens somando query e passagem** (contagem `tiktoken`, aproximada;
   era 8.192 no 1B). A conjunção é exata: duas queries que diferem em 72 tokens deram somas que
   diferem em ZERO. Nenhum chunk do corpus chega perto (máximo medido: 446 tokens contra ~6.958),
   então `truncate="END"` no payload é rede de segurança e não caminho normal — e é omitindo
   `truncate` que a API denuncia o limite, com HTTP 400, em vez de cortar em silêncio.
2. **Os logits são quantizados e NÃO variam entre execuções.** `11,9375` é `11 + 15/16`,
   assinatura da grade; três chamadas independentes deram o mesmo valor, espalhamento 0,000000.
   D-034 supunha variação entre execuções e a revisão da sessão 03 já a tinha refutado no 1B.
   **Nenhuma lógica pode depender de margem abaixo do passo da grade** — e isso vale
   especialmente para qualquer limiar de abstenção (ver D-035).
"""

from __future__ import annotations

import httpx

from src.config import RERANK
from src.rag.busca import Passagem, para_citacao
from src.state import CitacaoRAG

# Quantas passagens vão por chamada. A API aceita mais que isto, mas lotear tem uma vantagem que
# não é de limite: o cross-encoder pontua cada par (consulta, passagem) de forma INDEPENDENTE,
# então dividir em lotes não muda nenhum score. Se um dia mudar, o lote é o botão.
LOTE = 32

TIMEOUT = 120.0


def _chamar(consulta: str, textos: list[str]) -> list[float]:
    """Logits na MESMA ordem da entrada. A API devolve ordenado por relevância, não por índice."""
    r = httpx.post(
        RERANK.url,
        headers={"Authorization": f"Bearer {RERANK.api_key}", "Accept": "application/json"},
        json={
            "model": RERANK.modelo,
            "query": {"text": consulta},
            "passages": [{"text": t} for t in textos],
            "truncate": "END",
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    por_indice = {x["index"]: float(x["logit"]) for x in r.json()["rankings"]}
    return [por_indice[i] for i in range(len(textos))]


def logits_de(consulta: str, passagens: list[Passagem]) -> dict[int, float]:
    """`chunk_id -> logit`. Dicionário e não lista porque a fusão já mexeu na ordem."""
    saida: dict[int, float] = {}
    for i in range(0, len(passagens), LOTE):
        lote = passagens[i:i + LOTE]
        for p, logit in zip(lote, _chamar(consulta, [p.texto_indexado for p in lote])):
            saida[p.chunk_id] = logit
    return saida


def reranquear(
    consulta: str, passagens: list[Passagem], top_n: int | None = None
) -> list[tuple[Passagem, float]]:
    """Reordena as passagens por relevância julgada pelo cross-encoder."""
    if not passagens:
        return []
    logits = logits_de(consulta, passagens)
    ordenado = sorted(passagens, key=lambda p: -logits[p.chunk_id])
    if top_n is not None:
        ordenado = ordenado[:top_n]
    return [(p, logits[p.chunk_id]) for p in ordenado]


def reranquear_citacoes(
    consulta: str,
    passagens: list[Passagem],
    scores_denso: dict[int, float] | None = None,
    scores_lexical: dict[int, float] | None = None,
    top_n: int | None = None,
) -> list[CitacaoRAG]:
    """A borda: devolve `CitacaoRAG` com OS TRÊS SCORES preenchidos.

    Guardar os três separados é o que permite MOSTRAR o reranker mudando a ordem — no vídeo e no
    harness. `None` num deles continua significando "este motor não votou", que é diferente de
    "votou zero".
    """
    scores_denso = scores_denso or {}
    scores_lexical = scores_lexical or {}
    return [
        para_citacao(
            p,
            denso=scores_denso.get(p.chunk_id),
            lexical=scores_lexical.get(p.chunk_id),
            rerank=logit,
        )
        for p, logit in reranquear(consulta, passagens, top_n)
    ]
