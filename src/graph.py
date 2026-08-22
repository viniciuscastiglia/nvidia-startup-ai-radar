"""Montagem do grafo — topologia de subgrafo + fan-out por `Send` (D-007).

    GRAFO PAI (4 nós)
      START -> query_planner -> retriever
                                   |  Send(...) x N startups
                                   v
                            analisar_startup          <- nó-wrapper
                                   |  fan-in via reducer operator.add
                                   v
                            briefing (defer=True) -> END

    SUBGRAFO DE ANÁLISE (5 nós, roda 1x por startup, testável isolado)
      extractor -> classifier -> evidence_validator -> nvidia_rag -> recommendation
                                                                          |
                                                                    elegibilidade

POR QUE ASSIM E NÃO UM GRAFO LINEAR DE 8 NÓS
---------------------------------------------
O TAPI justifica LangGraph por "estado, transições condicionais, checkpoints, retry e
intervenção humana". Um grafo linear usaria zero disso — seria uma chain de prompts com
sintaxe de grafo, o que é nível 2 no critério 1. Esta topologia usa quatro recursos que uma
chain não tem, e cada um resolve um problema concreto:

  Send            uma startup por chamada de LLM. Com lote, o prompt cresce com N e a
                  extração degrada; e o retry só existiria no nível do nó.
  defer=True      o Briefing só executa quando o run está terminando, ou seja, depois de
                  todas as branches. Sem isso seria preciso contar branches à mão.
  retry_policy    falha transitória de LLM não derruba a análise.
  error_handler   uma startup com dado ruim vira análise incompleta com `erros` preenchido,
                  não um run inteiro derrubado. O briefing reporta a falha em vez de sumir.

O `Send` mira um nó-WRAPPER que invoca o subgrafo compilado, em vez de mirar o subgrafo
direto: isso evita descasamento entre o schema do estado pai e o do filho.
"""

from __future__ import annotations

import sys

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy, Send

from src.agents import (
    briefing,
    classifier,
    evidence_validator,
    extractor,
    nvidia_rag,
    query_planner,
    recommendation,
    retriever,
)
from src.state import AnaliseStartup, EstadoAnalise, EstadoRadar

# Retry só onde a falha é plausível e transitória. O Retriever fala com o Postgres local:
# se ele falhar, repetir três vezes não resolve e só esconde o problema.
RETENTAR = RetryPolicy(max_attempts=3, initial_interval=1.0, backoff_factor=2.0)


def construir_subgrafo():
    """As cinco etapas de análise de UMA startup.

    Compilado separado de propósito: dá para invocar no pytest com um `EstadoAnalise` montado
    à mão, sem subir o grafo pai nem tocar no banco.
    """
    g = StateGraph(EstadoAnalise)
    g.add_node("extractor", extractor.node, retry_policy=RETENTAR)
    g.add_node("classifier", classifier.node, retry_policy=RETENTAR)
    g.add_node("evidence_validator", evidence_validator.node)   # lógica pura: não falha por rede
    g.add_node("nvidia_rag", nvidia_rag.node, retry_policy=RETENTAR)
    g.add_node("recommendation", recommendation.node, retry_policy=RETENTAR)
    g.add_node("elegibilidade", briefing.node_analise)

    g.add_edge(START, "extractor")
    g.add_edge("extractor", "classifier")
    g.add_edge("classifier", "evidence_validator")
    g.add_edge("evidence_validator", "nvidia_rag")
    g.add_edge("nvidia_rag", "recommendation")
    g.add_edge("recommendation", "elegibilidade")
    g.add_edge("elegibilidade", END)
    return g.compile()


SUBGRAFO = construir_subgrafo()


def distribuir(state: EstadoRadar) -> list[Send]:
    """Aresta condicional que faz o fan-out: um `Send` por startup recuperada.

    Cada `Send` carrega o estado INICIAL daquela branch — não o estado do pai inteiro. É o
    que garante que cada análise enxergue uma empresa só.
    """
    return [
        Send("analisar_startup", {"plano": state["plano"], "startup": s})
        for s in (state.get("startups") or [])
    ]


def analisar_startup(state: EstadoAnalise) -> dict:
    """Nó-wrapper: invoca o subgrafo e devolve UMA análise para o reducer do pai concatenar.

    O try/except aqui é a rede de segurança de último nível: se o subgrafo inteiro estourar,
    a startup vira uma `AnaliseStartup` com `erros` preenchido em vez de derrubar o run.
    O briefing reporta a falha — que é informação útil — em vez de a empresa sumir em silêncio.
    """
    startup = state["startup"]
    try:
        final = SUBGRAFO.invoke(state)
        analise = AnaliseStartup(
            startup_id=startup.startup_id,
            nome=startup.nome,
            perfil=final.get("perfil"),
            diagnostico=final.get("diagnostico"),
            elegibilidade=final.get("elegibilidade"),
            recomendacoes=final.get("recomendacoes") or [],
            erros=final.get("erros") or [],
        )
    except Exception as exc:  # noqa: BLE001
        analise = AnaliseStartup(
            startup_id=startup.startup_id,
            nome=startup.nome,
            erros=[f"{type(exc).__name__}: {exc}"],
        )
    return {"analises": [analise]}


def construir_grafo(checkpointer=None):
    """Grafo pai. `checkpointer` é parâmetro, não constante: hoje `MemorySaver`, alvo
    `PostgresSaver` reusando o Postgres que já é dependência dura (ver D-006)."""
    g = StateGraph(EstadoRadar)
    g.add_node("query_planner", query_planner.node)
    g.add_node("retriever", retriever.node)
    g.add_node("analisar_startup", analisar_startup)
    # defer=True: só roda quando o run está terminando, ou seja, depois de todos os Send.
    g.add_node("briefing", briefing.node, defer=True)

    g.add_edge(START, "query_planner")
    g.add_edge("query_planner", "retriever")
    g.add_conditional_edges("retriever", distribuir, ["analisar_startup"])
    g.add_edge("analisar_startup", "briefing")
    g.add_edge("briefing", END)
    return g.compile(checkpointer=checkpointer or MemorySaver())


GRAFO = construir_grafo()


def main() -> int:
    consulta = " ".join(sys.argv[1:]) or "startups brasileiras de saúde usando IA"
    # thread_id é o que o checkpointer usa para agrupar o run. Com PostgresSaver, é por ele
    # que se retoma uma execução interrompida sem re-rodar o que já passou.
    config = {"configurable": {"thread_id": "cli"}}
    final = GRAFO.invoke({"consulta": consulta}, config=config)
    print(final.get("briefing") or "(sem briefing)")
    if erros := final.get("erros"):
        print("\nerros do grafo pai:", erros)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
