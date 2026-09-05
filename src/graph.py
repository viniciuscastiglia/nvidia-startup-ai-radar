"""Montagem do grafo — topologia de subgrafo + fan-out por `Send` (D-007).

    GRAFO PAI (4 nós)
      START -> query_planner -> retriever
                                   |  Send(...) x N startups
                                   v
                            analisar_startup          <- nó-wrapper
                                   |  fan-in via reducer operator.add
                                   v
                            briefing (defer=True) -> END

    SUBGRAFO DE ANÁLISE (6 nós, roda 1x por startup, testável isolado)
      extractor -> classifier -> evidence_validator -> elegibilidade -> nvidia_rag
                                                                            |
                                                                      recommendation
                            ^ elegibilidade ANTES de recommendation desde 04/09 (D-099):
                              recomendar para quem o próprio sistema recusou era defeito de
                              ORDEM, não de motor. Ver o comentário em `construir_subgrafo`.

POR QUE ASSIM E NÃO UM GRAFO LINEAR DE 8 NÓS
---------------------------------------------
O TAPI justifica LangGraph por "estado, transições condicionais, checkpoints, retry e
intervenção humana". Um grafo linear usaria zero disso — seria uma chain de prompts vestida de
grafo, pagando a complexidade do LangGraph sem receber nada em troca. Esta topologia usa quatro
recursos que uma chain não tem, e cada um resolve um problema concreto:

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


def seguir_sem_elegibilidade(state: EstadoAnalise, error: NodeError) -> Command:
    """Anota a falha e SEGUE — o oposto de `registrar_falha`, e por um motivo (D-103).

    O filtro do Inception não alimenta nada a jusante: `recommendation.node` não lê
    `elegibilidade`, e `briefing._secao` já trata `elegibilidade=None` como ausência. Uma falha
    aqui custa um veredito; com `goto=END` ela passaria a custar TAMBÉM as citações do RAG e as
    recomendações, que são o resto da análise. É a mesma lógica de `registrar_falha` — preservar
    o trabalho parcial —, e é justamente por isso que ela pede outro `goto` neste nó.
    """
    return Command(
        update={"erros": [f"{error.node}: {type(error.error).__name__}: {error.error}"]},
        goto="nvidia_rag",
    )


def construir_subgrafo():
    """As SEIS etapas de análise de UMA startup.

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
    # ERROR HANDLER PRÓPRIO — D-103, e é consequência direta de D-099 ter movido este nó.
    # `registrar_falha` faz `goto=END`, o que era correto quando `elegibilidade` era o ÚLTIMO
    # nó: a falha custava só o veredito de elegibilidade. Movido para cima, o MESMO handler
    # passou a destruir as citações do RAG e as recomendações da empresa — medido por injeção
    # de falha: `citacoes_rag=None`, `recomendacoes=None`. Isso contraria o objetivo declarado
    # de `registrar_falha`, que é PRESERVAR O TRABALHO PARCIAL.
    #
    # Nada a jusante depende da elegibilidade — `recommendation.node` não a lê, e o briefing
    # trata `elegibilidade=None` como ausência —, então a falha aqui deve ANOTAR e SEGUIR.
    # `goto` é o próximo nó, não `END`.
    g.add_node("elegibilidade", briefing.node_analise, error_handler=seguir_sem_elegibilidade)

    # A ORDEM DO FILTRO DO INCEPTION — CORRIGIDA EM 04/09 (D-099)
    # ------------------------------------------------------------
    # Até aqui `elegibilidade` era o ÚLTIMO nó, depois de `recommendation`. O motor de
    # recomendação rodava antes do filtro e não tinha como saber que a empresa fora recusada.
    # Na tela, num run real: a Liqi sai `x exclusão por 'cripto'` e sete linhas abaixo recebe
    # "Agendar conversa técnica ... com o time de engenharia da Liqi".
    #
    # NÃO HAVIA DEPENDÊNCIA NENHUMA SUSTENTANDO ESSA POSIÇÃO: `briefing.node_analise` lê só
    # `state["startup"]` e `state["perfil"]`, ambos prontos depois do `extractor`. O nó estava
    # no fim por acidente de construção — foi o último a ser escrito.
    #
    # POR QUE ANTES DE `nvidia_rag` E NÃO SÓ ANTES DE `recommendation`: é onde a informação
    # fica disponível o mais cedo possível sem custar nada. Não pulamos o RAG das recusadas
    # (D-099 decidiu MANTER a recomendação, rotulada), mas quem quiser pular no futuro tem o
    # dado em mãos no ponto certo, e a mudança vira uma condicional em vez de uma topologia.
    g.add_edge(START, "extractor")
    g.add_edge("extractor", "classifier")
    g.add_edge("classifier", "evidence_validator")
    g.add_edge("evidence_validator", "elegibilidade")
    g.add_edge("elegibilidade", "nvidia_rag")
    g.add_edge("nvidia_rag", "recommendation")
    g.add_edge("recommendation", END)
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
            motivo_sem_recomendacao=final.get("motivo_sem_recomendacao"),
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
