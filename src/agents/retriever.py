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
    if not startups:
        return {
            "startups": [],
            "erros": [f"Nenhuma startup casou os critérios de {plano.consulta_original!r}"],
        }
    return {"startups": startups}
