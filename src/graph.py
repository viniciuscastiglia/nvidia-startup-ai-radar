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
  error_handler   por nó do subgrafo: a etapa que falhou registra o erro e salta para o END
                  PRESERVANDO o que as etapas anteriores já produziram. Uma startup com dado
                  ruim vira análise PARCIAL — não um buraco, e não um run derrubado.

O `Send` mira um nó-WRAPPER que invoca o subgrafo compilado, em vez de mirar o subgrafo
direto: isso evita descasamento entre o schema do estado pai e o do filho.
"""

from __future__ import annotations

import sys
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import NodeError
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, RetryPolicy, Send

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


def registrar_falha(state: EstadoAnalise, error: NodeError) -> Command:
    """`error_handler` de nó do subgrafo (D-024).

    POR QUE ISSO E NAO try/except DENTRO DE CADA NÓ
    ------------------------------------------------
    O ponto não é "não estourar" — é PRESERVAR O TRABALHO PARCIAL. Se o `nvidia_rag` falhar
    depois que o Extractor e o Classifier já rodaram, envolver o subgrafo inteiro num
    try/except perde perfil e diagnóstico junto: a startup volta vazia. Com `error_handler`,
    as escritas dos super-steps anteriores já estão nos canais, o handler só acrescenta o
    erro e manda para o END — e o briefing recebe uma análise parcial com a causa registrada.

    Medido: falha no classifier devolve `{perfil: <preenchido>, erros: [...]}` em vez de `{}`.

    `goto=END` e não seguir o fluxo: sem o diagnóstico, as etapas seguintes produziriam
    recomendação sem base. Falha cedo é informação; falha propagada é ruído.
    """
    return Command(
        update={"erros": [f"{error.node}: {type(error.error).__name__}: {error.error}"]},
        goto=END,
    )


def construir_subgrafo():
    """As cinco etapas de análise de UMA startup.

    Compilado separado de propósito: dá para invocar no pytest com um `EstadoAnalise` montado
    à mão, sem subir o grafo pai nem tocar no banco.
    """
    g = StateGraph(EstadoAnalise)
    g.add_node("extractor", extractor.node, retry_policy=RETENTAR, error_handler=registrar_falha)
    g.add_node("classifier", classifier.node, retry_policy=RETENTAR, error_handler=registrar_falha)
    # lógica pura: sem retry (repetir não muda o resultado), mas ainda pode levantar
    g.add_node("evidence_validator", evidence_validator.node, error_handler=registrar_falha)
    g.add_node("nvidia_rag", nvidia_rag.node, retry_policy=RETENTAR, error_handler=registrar_falha)
    g.add_node("recommendation", recommendation.node, retry_policy=RETENTAR,
               error_handler=registrar_falha)
    g.add_node("elegibilidade", briefing.node_analise, error_handler=registrar_falha)

    g.add_edge(START, "extractor")
    g.add_edge("extractor", "classifier")
    g.add_edge("classifier", "evidence_validator")
    g.add_edge("evidence_validator", "nvidia_rag")
    g.add_edge("nvidia_rag", "recommendation")
    g.add_edge("recommendation", "elegibilidade")
    g.add_edge("elegibilidade", END)
    return g.compile()


SUBGRAFO = construir_subgrafo()


def distribuir(state: EstadoRadar) -> list[Send] | str:
    """Aresta condicional que faz o fan-out: um `Send` por startup recuperada.

    Cada `Send` carrega o estado INICIAL daquela branch — não o estado do pai inteiro. É o
    que garante que cada análise enxergue uma empresa só.

    O CASO ZERO É EXPLÍCITO DE PROPÓSITO (D-023). Devolver `[]` aqui não agenda tarefa
    nenhuma, e como o `briefing` só é alcançável pela aresta vinda de `analisar_startup`,
    ele nunca executaria — `defer=True` não agenda nada, só ATRASA o que já foi agendado.
    O resultado seria uma consulta sem resultado terminando em silêncio, sem relatório.
    Roteando direto para o briefing, "não encontrei nada e aqui está o porquê" vira uma
    saída do sistema em vez de um estado interno.
    """
    startups = state.get("startups") or []
    if not startups:
        return "briefing"
    return [
        Send("analisar_startup", {"plano": state["plano"], "startup": s})
        for s in startups
    ]


def analisar_startup(state: EstadoAnalise) -> dict:
    """Nó-wrapper: invoca o subgrafo e devolve UMA análise para o reducer do pai concatenar.

    TRÊS NÍVEIS DE TRATAMENTO DE FALHA, cada um pegando uma coisa diferente:
      1. `retry_policy` no nó  — falha TRANSITÓRIA (timeout, 5xx do provedor de LLM).
      2. `error_handler` no nó — falha PERSISTENTE da etapa: registra e salta para o END
                                 preservando o que as etapas anteriores produziram.
      3. este try/except       — falha da PRÓPRIA MÁQUINA do subgrafo (schema incompatível,
                                 estouro de recursão), que os dois de cima não alcançam.

    O nível 3 quase nunca dispara agora que o 2 existe — e é por isso que ele continua aqui:
    uma startup não pode derrubar as outras quatro por um modo de falha que não previmos.
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
    g.add_conditional_edges("retriever", distribuir, ["analisar_startup", "briefing"])
    g.add_edge("analisar_startup", "briefing")
    g.add_edge("briefing", END)
    return g.compile(checkpointer=checkpointer or MemorySaver())


GRAFO = construir_grafo()


def main() -> int:
    """CLI. `--thread <id>` retoma um run existente; sem ele, cada execução é um run novo.

    POR QUE NÃO UM `thread_id` FIXO (D-022)
    ----------------------------------------
    `thread_id` é a identidade da CONVERSA, não do processo. Invocar duas vezes no mesmo
    thread não recomeça: o checkpointer restaura os canais e o run continua de onde parou —
    então `analises`, que tem reducer `operator.add`, SOMA em cima do run anterior.
    Medido com o `thread_id: "cli"` fixo que estava aqui: a segunda execução devolvia a
    mesma startup duas vezes no briefing.

    Um comando novo é um run novo. Retomar é o caso especial, e agora é explícito.
    """
    args = sys.argv[1:]
    thread: str | None = None
    if "--thread" in args:
        i = args.index("--thread")
        thread = args[i + 1] if i + 1 < len(args) else None
        args = args[:i] + args[i + 2:]
    consulta = " ".join(args) or "startups brasileiras de saúde usando IA"

    thread_id = thread or f"cli-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}
    final = GRAFO.invoke({"consulta": consulta}, config=config)
    print(final.get("briefing") or "(sem briefing)")
    if erros := final.get("erros"):
        print("\nerros do grafo pai:", erros)
    print(f"\nthread_id: {thread_id}   (retomar: python -m src.graph --thread {thread_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
