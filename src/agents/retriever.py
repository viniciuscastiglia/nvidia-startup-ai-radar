"""Retriever — seleciona empresas e documentos na base pré-populada.

NÃO É STUB. É o único nó que não precisa de LLM: a recuperação é SQL sobre `tsvector` em
português mais filtros estruturados. Ver a justificativa em `src/db.py`.
"""

from __future__ import annotations

from src.db import buscar_startups
from src.state import EstadoRadar


def node(state: EstadoRadar) -> dict:
    plano = state["plano"]
    if plano is None:
        return {"startups": [], "erros": ["Retriever chamado sem plano de busca"]}
    startups = buscar_startups(plano)
    # D-081: sem nenhum critério, a busca devolve uma fatia alfabética da base. Isso não é um
    # erro do SQL — é uma consulta que não discriminou, e o usuário precisa saber, porque a
    # saída é idêntica à de um acerto. O briefing repete o aviso no cabeçalho: aqui ele fica
    # para o log e para o `--thread`, lá para quem lê o relatório.
    if startups and not plano.discrimina():
        return {
            "startups": startups,
            "erros": [
                f"consulta {plano.consulta_original!r} não produziu nenhum critério de busca: "
                f"as {len(startups)} empresas abaixo são uma fatia arbitrária da base, "
                f"não um resultado de recuperação"
            ],
        }
    if not startups:
        return {
            "startups": [],
            "erros": [f"Nenhuma startup casou os critérios de {plano.consulta_original!r}"],
        }
    return {"startups": startups}
