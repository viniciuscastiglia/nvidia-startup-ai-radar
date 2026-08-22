"""Acesso ao Postgres. O Retriever é o único nó que NÃO precisa de LLM — ele faz SQL.

POR QUE A BUSCA DOS DOCUMENTOS DE STARTUP É SQL E NÃO O MESMO MOTOR DO RAG NVIDIA (ver D-016)
----------------------------------------------------------------------------------------------
São dois problemas de recuperação com formatos diferentes:

- Aqui a busca lexical anda SEMPRE junto de filtro estruturado — setor, estágio, porte do time —
  e o corpus cresce a cada startup adicionada. Um `WHERE` combinando `tsvector @@ tsquery` com
  colunas indexadas é exatamente o que um banco relacional faz melhor que qualquer coisa.
- No RAG da NVIDIA o corpus é pequeno, estático, sem metadado para filtrar, e o que se quer é
  Okapi BM25 de verdade com k1/b ajustáveis para o harness de avaliação medir.

Ferramentas diferentes para problemas diferentes é decisão, não inconsistência.
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

from src.config import DATABASE_URL
from src.state import DocumentoRef, PlanoDeBusca, StartupRef


@contextmanager
def conectar() -> Iterator[psycopg.Connection]:
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conexao:
        yield conexao


def _para_tsquery(palavras: list[str]) -> str:
    """Monta um tsquery OR a partir das palavras-chave do plano.

    Sanitiza porque `to_tsquery` tem sintaxe própria (`&`, `|`, `!`, `:*`) e uma palavra-chave
    vinda de LLM pode conter qualquer coisa. `plainto_tsquery` seria mais seguro mas junta tudo
    com AND, o que é restritivo demais para uma consulta exploratória.
    """
    limpos = []
    for p in palavras:
        for termo in re.split(r"\W+", p, flags=re.UNICODE):
            if len(termo) > 2:
                limpos.append(termo.lower())
    return " | ".join(dict.fromkeys(limpos))   # dedup preservando ordem


SQL_BUSCAR = """
WITH consulta AS (
    SELECT to_tsquery('portuguese', imutavel_unaccent(%(tsq)s)) AS q
),
pontuadas AS (
    SELECT d.startup_id,
           MAX(ts_rank_cd(d.busca, c.q)) AS score,
           COUNT(*)                      AS docs_casados
    FROM documentos d, consulta c
    WHERE %(tsq)s = '' OR d.busca @@ c.q
    GROUP BY d.startup_id
)
SELECT s.*, COALESCE(p.score, 0) AS score, COALESCE(p.docs_casados, 0) AS docs_casados
FROM startups s
LEFT JOIN pontuadas p ON p.startup_id = s.id
WHERE (%(tsq)s = '' OR p.startup_id IS NOT NULL)
  AND (%(setores)s::text[]  IS NULL OR s.setor        ILIKE ANY(%(setores)s))
  AND (%(estagios)s::text[] IS NULL OR s.estagio      ILIKE ANY(%(estagios)s))
  AND (%(locais)s::text[]   IS NULL OR s.localizacao  ILIKE ANY(%(locais)s))
  AND (%(time_min)s::int    IS NULL OR s.tamanho_time >= %(time_min)s)
  AND (%(time_max)s::int    IS NULL OR s.tamanho_time <= %(time_max)s)
ORDER BY score DESC, s.nome
LIMIT %(limite)s
"""

SQL_DOCUMENTOS = """
SELECT id, startup_id, tipo, titulo, conteudo_texto, url_fonte, data_publicacao
FROM documentos
WHERE startup_id = ANY(%(ids)s)
ORDER BY startup_id, data_publicacao DESC NULLS LAST, id
"""


def _curinga(valores: list[str] | None) -> list[str] | None:
    """ILIKE ANY com curinga nas pontas: 'saúde' casa 'saúde corporativa'."""
    return [f"%{v}%" for v in valores] if valores else None


def buscar_startups(plano: PlanoDeBusca) -> list[StartupRef]:
    tsq = _para_tsquery(plano.palavras_chave)
    parametros = {
        "tsq": tsq,
        "setores": _curinga(plano.setores),
        "estagios": _curinga(plano.estagios),
        "locais": _curinga(plano.localizacoes),
        "time_min": plano.porte_min_time,
        "time_max": plano.porte_max_time,
        "limite": plano.max_startups,
    }
    with conectar() as conexao, conexao.cursor() as cur:
        cur.execute(SQL_BUSCAR, parametros)
        linhas = cur.fetchall()
        if not linhas:
            return []
        ids = [linha["id"] for linha in linhas]
        cur.execute(SQL_DOCUMENTOS, {"ids": ids})
        docs_por_startup: dict[int, list[DocumentoRef]] = {}
        for d in cur.fetchall():
            docs_por_startup.setdefault(d["startup_id"], []).append(
                DocumentoRef(
                    documento_id=d["id"],
                    tipo=d["tipo"],
                    titulo=d["titulo"],
                    url_fonte=d["url_fonte"],
                    data_publicacao=d["data_publicacao"],
                    conteudo_texto=d["conteudo_texto"],
                )
            )

    return [
        StartupRef(
            startup_id=linha["id"],
            nome=linha["nome"],
            site=linha["site"],
            setor=linha["setor"],
            estagio=linha["estagio"],
            localizacao=linha["localizacao"],
            ano_fundacao=linha["ano_fundacao"],
            tamanho_time=linha["tamanho_time"],
            descricao_curta=linha["descricao_curta"],
            documentos=docs_por_startup.get(linha["id"], []),
            score_recuperacao=float(linha["score"]),
        )
        for linha in linhas
    ]
