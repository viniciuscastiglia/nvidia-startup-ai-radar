"""Runs salvos em disco — a rede de segurança da gravação, e a única cópia que um avaliador
sem chave de API consegue abrir.

POR QUE ISTO EXISTE, E NÃO É CACHE
-----------------------------------
Duas razões, e nenhuma é desempenho:

1. **O fornecedor não avisa (D-079).** Não há header `Sunset`, não há campo na listagem: a
   chamada real informa, e informa depois. Um run salvo é a diferença entre gravar o vídeo e
   descobrir o EOL na frente da câmera. O mesmo vale para a cota do Cohere, que já acabou uma
   vez no meio de um dia de trabalho (D-093).
2. **Quem clonar o repositório sem chave nenhuma consegue ver o sistema.** Não é o mesmo que
   rodá-lo — e a tela diz qual dos dois o leitor está vendo.

O ARQUIVO É O MESMO JSON QUE A TELA DESENHA AO VIVO (`payload.montar_run`). Um segundo formato
"para salvar" criaria uma segunda tela para manter, e ela só seria exercitada no dia em que a
primeira falhasse — que é exatamente o dia em que ela precisa funcionar.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
DIR_RUNS = RAIZ / "data" / "runs"

# O `thread_id` vem da URL, então ele é entrada de fora e não um identificador interno.
# `../../.env` é um `thread_id` sintaticamente válido para uma rota `/api/run/{id}`; sem esta
# guarda, `DIR_RUNS / thread_id` sai de `data/runs/` e lê qualquer arquivo da máquina.
# O gerador de `src/graph.py:257` produz `cli-<uuid4>`, que passa nesta regra por construção.
SEGURO = re.compile(r"^[A-Za-z0-9_-]{1,120}$")


class ThreadInvalido(ValueError):
    pass


def _caminho(thread_id: str) -> Path:
    if not SEGURO.match(thread_id or ""):
        raise ThreadInvalido(f"thread_id fora do formato esperado: {thread_id!r}")
    return DIR_RUNS / f"{thread_id}.json"


def salvar(run: dict) -> Path:
    DIR_RUNS.mkdir(parents=True, exist_ok=True)
    destino = _caminho(run["thread_id"])
    destino.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino


def carregar(thread_id: str) -> dict | None:
    caminho = _caminho(thread_id)
    if not caminho.is_file():
        return None
    return json.loads(caminho.read_text(encoding="utf-8"))


def listar() -> list[dict]:
    """Só o cabeçalho de cada run — a lista não carrega 36 KB por linha para desenhar um menu.

    Ordenada do mais recente para o mais antigo: quem abre a lista está quase sempre atrás do
    último run, não do primeiro.
    """
    if not DIR_RUNS.is_dir():
        return []
    cabecalhos = []
    for caminho in DIR_RUNS.glob("*.json"):
        try:
            run = json.loads(caminho.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # Um arquivo corrompido não pode derrubar a lista inteira: o menu é a porta de
            # entrada da rede de segurança, e ele falhar junto anula o propósito dela.
            continue
        cabecalhos.append({
            "thread_id": run.get("thread_id", caminho.stem),
            "consulta": run.get("consulta", ""),
            "gerado_em": run.get("gerado_em", ""),
            "rerank_provedor": run.get("rerank_provedor"),
            "empresas": len(run.get("analises") or []),
        })
    return sorted(cabecalhos, key=lambda c: c["gerado_em"], reverse=True)
