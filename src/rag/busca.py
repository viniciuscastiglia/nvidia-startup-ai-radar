"""Recuperação na base de conhecimento NVIDIA — o braço denso do passo 6.

O passo 6 do pipeline do TAPI é "busca híbrida: vetorial + lexical". O braço lexical mora em
`src/rag/lexical.py` e a fusão em `src/rag/fusao.py`; aqui fica o denso e a montagem do
resultado híbrido.

O denso puro continua exportado como `buscar_denso` porque ele é a LINHA DE BASE de D-032: sem
um número de partida, "a busca híbrida melhorou" e "o reranking melhorou" viram afirmação em
vez de medida.

DOIS TIPOS, E A FRONTEIRA ENTRE ELES É DE PROPÓSITO (D-041)
------------------------------------------------------------
`Passagem` é o tipo INTERNO do pipeline de recuperação: carrega `chunk_id` (a chave que a fusão
usa para casar o mesmo chunk entre dois rankings) e `texto_indexado` (o que o reranker lê,
D-038). `CitacaoRAG` é o CONTRATO com os agentes — mora em `src/state.py` e vai para
`Recomendacao.citacoes_rag`.

Manter os dois separados significa que trocar a fusão ou o reranker não propaga para o estado
do grafo. A conversão acontece só na borda, em `para_citacao`.

`score_lexical` e `score_rerank` em `None` significam "ainda não medido", que é diferente de
`0.0` — este diria "medido e deu zero".

A ASSIMETRIA, DO OUTRO LADO
---------------------------
A ingestão embeda com `input_type="passage"`; aqui é `"query"`. O NeMo Retriever treina os
dois lados de forma diferente e usar o tipo errado degrada a recuperação SEM DAR ERRO
(`contexto/03` §3). É o mesmo cuidado do `ingerir_nvidia.py`, na ponta oposta.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from src.config import EMBEDDING
from src.db import conectar
from src.state import CitacaoRAG

ESTRATEGIA_PADRAO = "estrutural-v1"


@dataclass(frozen=True)
class Passagem:
    """Um chunk recuperado, antes de virar citação. Ver o docstring do módulo (D-041).

    `chunk_id` existe para a fusão: RRF e soma ponderada precisam reconhecer que o item no
    ranking denso e o item no ranking lexical são o MESMO chunk. Comparar por texto seria
    frágil e caro; o id vem do banco de graça.
    """

    chunk_id: int
    tecnologia: str
    texto: str              # limpo — é o que vira CitacaoRAG.trecho
    texto_indexado: str     # com breadcrumb — é o que o reranker lê (D-038)
    caminho_secao: str
    documento_url: str


def para_citacao(
    p: Passagem,
    denso: float | None = None,
    lexical: float | None = None,
    rerank: float | None = None,
) -> CitacaoRAG:
    """A borda entre o pipeline de recuperação e o contrato com os agentes."""
    return CitacaoRAG(
        tecnologia=p.tecnologia,
        trecho=p.texto,
        url_fonte=p.documento_url,
        score_denso=denso,
        score_lexical=lexical,
        score_rerank=rerank,
    )


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
SELECT id, tecnologia, texto, texto_indexado, caminho_secao, documento_url,
       1 - (embedding <=> %(vetor)s::vector) AS score
FROM chunks_nvidia
WHERE estrategia = %(estrategia)s
ORDER BY embedding <=> %(vetor)s::vector
LIMIT %(k)s
"""


def buscar_denso_bruto(
    consulta: str, k: int = 10, estrategia: str = ESTRATEGIA_PADRAO
) -> list[tuple[Passagem, float]]:
    """Os k chunks mais próximos por cosseno, como `Passagem` + score.

    É a forma que a fusão e o reranker consomem. `buscar_denso` embrulha esta.
    """
    vetor = como_vetor(embedar_consulta(consulta))
    with conectar() as conexao, conexao.cursor() as cur:
        cur.execute(SQL_DENSO, {"vetor": vetor, "estrategia": estrategia, "k": k})
        linhas = cur.fetchall()

    return [
        (
            Passagem(
                chunk_id=linha["id"],
                tecnologia=linha["tecnologia"],
                texto=linha["texto"],
                texto_indexado=linha["texto_indexado"],
                caminho_secao=linha["caminho_secao"],
                documento_url=linha["documento_url"],
            ),
            float(linha["score"]),
        )
        for linha in linhas
    ]


def buscar_denso(
    consulta: str, k: int = 10, estrategia: str = ESTRATEGIA_PADRAO
) -> list[CitacaoRAG]:
    """Os k chunks mais próximos da consulta por similaridade de cosseno.

    `estrategia` é parâmetro e não constante por causa de D-027: é o que deixa o harness
    comparar 'estrutural-v1' com 'fixo-800' sem tocar em mais nada.

    Continua existindo depois da sessão 03 porque é a LINHA DE BASE de D-032 — o número contra
    o qual híbrida e rerank são medidos.
    """
    return [para_citacao(p, denso=s) for p, s in buscar_denso_bruto(consulta, k, estrategia)]
