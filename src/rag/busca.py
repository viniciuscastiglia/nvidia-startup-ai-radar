"""Recuperação na base de conhecimento NVIDIA.

ESTA SESSÃO ENTREGA SÓ A METADE DENSA — de propósito.

O passo 6 do pipeline do TAPI é "busca híbrida: vetorial + lexical", e a lexical (BM25 em
processo, D-016) é a sessão 03. O denso puro está aqui porque ele é a LINHA DE BASE: sem um
número de partida, "a busca híbrida melhorou" e "o reranking melhorou" viram afirmação em vez
de medida. É a razão de D-031 ter movido a busca densa e o recall@k para esta sessão.

`buscar_hibrido(query, k)` da sessão 03 vai ter esta mesma assinatura e preencher os outros
dois scores de `CitacaoRAG`. Enquanto isso, `score_lexical` e `score_rerank` ficam em `None` —
e `None` é diferente de `0.0`: um diz "ainda não medido", o outro diria "medido e deu zero".

A ASSIMETRIA, DO OUTRO LADO
---------------------------
A ingestão embeda com `input_type="passage"`; aqui é `"query"`. O NeMo Retriever treina os
dois lados de forma diferente e usar o tipo errado degrada a recuperação SEM DAR ERRO
(`contexto/03` §3). É o mesmo cuidado do `ingerir_nvidia.py`, na ponta oposta.
"""

from __future__ import annotations

import httpx

from src.config import EMBEDDING
from src.db import conectar
from src.state import CitacaoRAG

ESTRATEGIA_PADRAO = "estrutural-v1"


def embedar_consulta(texto: str, dimensao: int | None = None) -> list[float]:
    """Embeda UMA consulta. `input_type="query"` — ver o docstring do módulo."""
    dim = dimensao or EMBEDDING.dimensao
    r = httpx.post(
        f"{EMBEDDING.base_url}/embeddings",
        headers={"Authorization": f"Bearer {EMBEDDING.api_key}", "Accept": "application/json"},
        json={
            "input": [texto],
            "model": EMBEDDING.modelo,
            "input_type": "query",
            "encoding_format": "float",
            "truncate": "END",
            "dimensions": dim,
        },
        timeout=60.0,
    )
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]


def como_vetor(v: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in v) + "]"


# `<=>` é distância de cosseno no pgvector: 0 = idêntico, 2 = oposto. O score devolvido é
# 1 - distância, para que MAIOR seja MELHOR — que é a convenção dos outros dois scores de
# CitacaoRAG e evita uma inversão de sinal na hora de fundir na sessão 03.
SQL_DENSO = """
SELECT tecnologia, texto, caminho_secao, documento_url,
       1 - (embedding <=> %(vetor)s::vector) AS score
FROM chunks_nvidia
WHERE estrategia = %(estrategia)s
ORDER BY embedding <=> %(vetor)s::vector
LIMIT %(k)s
"""


def buscar_denso(
    consulta: str, k: int = 10, estrategia: str = ESTRATEGIA_PADRAO
) -> list[CitacaoRAG]:
    """Os k chunks mais próximos da consulta por similaridade de cosseno.

    `estrategia` é parâmetro e não constante por causa de D-027: é o que deixa o harness
    comparar 'estrutural-v1' com 'fixo-800' sem tocar em mais nada.
    """
    vetor = como_vetor(embedar_consulta(consulta))
    with conectar() as conexao, conexao.cursor() as cur:
        cur.execute(SQL_DENSO, {"vetor": vetor, "estrategia": estrategia, "k": k})
        linhas = cur.fetchall()

    return [
        CitacaoRAG(
            tecnologia=linha["tecnologia"],
            trecho=linha["texto"],
            url_fonte=linha["documento_url"],
            score_denso=float(linha["score"]),
            score_lexical=None,     # sessão 03
            score_rerank=None,      # sessão 03
        )
        for linha in linhas
    ]
