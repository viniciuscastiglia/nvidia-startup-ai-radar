"""Interface web — a superfície pela qual o gerente de Startups & VCs usa o Radar.

O QUE ESTA CAMADA É, E O QUE ELA DELIBERADAMENTE NÃO É
-------------------------------------------------------
Ela é **consumidora** do grafo. Nenhuma regra de negócio mora aqui: a ordem das empresas vem de
`briefing.ordenar_analises`, o rótulo do quadrante de `briefing.rotulo_do_quadrante`, a consulta
por dor de `nvidia_rag.consulta_da_dor`, o texto exportado de `state["briefing"]`. Toda vez que a
tela precisou de uma regra, ela foi buscar a existente em vez de reescrever — porque uma segunda
definição da mesma regra é uma divergência esperando a data.

POR QUE FastAPI E NÃO STREAMLIT (P-06)
---------------------------------------
O que decidiu foi a LATÊNCIA, não a preferência: um run com o passo 7 ligado custa ~3m30
(D-068). Streamlit re-executa o script a cada interação, o que briga de frente com um processo
longo; e são ~15 dependências transitivas para uma tela que precisa de controle fino de estado.
Aqui o run é um stream SSE — o navegador recebe cada nó do grafo conforme ele termina.
Descartado também `http.server` da stdlib: economizaria 5 dependências e custaria roteamento e
SSE escritos à mão, mais código para manter e defender sem nada em troca.

POR QUE SSE E NÃO WEBSOCKET: o tráfego é de mão única (servidor -> navegador), SSE é HTTP puro
e reconecta sozinho. WebSocket traria um protocolo bidirecional para um problema que não é.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from src.config import LLM, MAX_STARTUPS, RERANK, tem_credencial
from src.graph import GRAFO
from src.rag.pipeline import recuperar_com_rastro, responder
from src.web import persistencia
from src.web.payload import montar_run

ESTATICO = Path(__file__).resolve().parent / "estatico"

app = FastAPI(title="NVIDIA Startup AI Radar", docs_url="/api/docs")
app.mount("/estatico", StaticFiles(directory=ESTATICO), name="estatico")

# UM RUN POR VEZ, E A RAZÃO É O FORNECEDOR, NÃO O SERVIDOR.
# Dois runs simultâneos dobram a fila do throttle do Cohere — cujo 429 chega na 4ª chamada
# sequencial, sem `retry-after`, com ~26 s de recuperação (D-068) — e ainda disputam a cota
# mensal de 1.000 chamadas que já acabou uma vez (D-093). A segunda consulta recebe um 409 que
# DIZ isso, em vez de um timeout mudo que o usuário interpretaria como sistema quebrado.
_EM_EXECUCAO = threading.Lock()

# Os nós, na ordem em que o grafo os executa. A tela desenha a arquitetura do TAPI e vai
# marcando — é o mesmo desenho de `src/graph.py`, e existe para que a espera de 3m30 mostre o
# sistema trabalhando em vez de um spinner.
NOS_PAI = ["query_planner", "retriever", "analisar_startup", "briefing"]
NOS_ANALISE = ["extractor", "classifier", "evidence_validator", "elegibilidade",
               "nvidia_rag", "recommendation"]


def _sse(evento: dict) -> str:
    """Uma mensagem SSE. `ensure_ascii=False` mantém o português legível no fio; o `\\n` do
    briefing já vem escapado pelo próprio JSON, então nenhuma quebra de linha vaza para o
    protocolo — que é onde ela quebraria o enquadramento das mensagens."""
    return f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"


def _nome_da_branch(no: str, atualizacao: dict) -> str | None:
    """De qual empresa é esta branch do fan-out?

    O namespace do `Send` carrega só um id de tarefa, então o nome vem do PAYLOAD: `extractor`
    é o primeiro nó do subgrafo e devolve um `PerfilStartup`, que tem `nome`. A partir daí a
    branch fica batizada para os cinco nós seguintes.
    """
    perfil = atualizacao.get("perfil") if isinstance(atualizacao, dict) else None
    return getattr(perfil, "nome", None) if no == "extractor" else None


def _rodar(consulta: str, max_startups: int, thread_id: str) -> Iterator[str]:
    """Roda o grafo e emite um evento por nó concluído. Ver o docstring do módulo.

    `stream_mode="updates"` + `subgraphs=True`: sem o segundo, o fan-out inteiro apareceria como
    um único nó `analisar_startup` piscando por minutos. Com ele, cada branch se identifica.

    O evento leva SÓ o nome do nó e o da empresa — as atualizações carregam modelos Pydantic, e
    serializá-las a cada superstep mandaria o run inteiro pelo fio uma vez por nó.
    """
    if not _EM_EXECUCAO.acquire(blocking=False):
        yield _sse({"tipo": "erro", "mensagem":
                    "já existe um run em andamento. Dois runs simultâneos disputam a cota do "
                    "Cohere e cada um fica mais lento que os dois em sequência."})
        return
    try:
        config = {"configurable": {"thread_id": thread_id}}
        entrada = {"consulta": consulta, "max_startups": max_startups}
        yield _sse({"tipo": "inicio", "thread_id": thread_id, "consulta": consulta,
                    "rerank_provedor": RERANK.provedor})

        branches: dict[tuple, str] = {}
        for ns, atualizacao in GRAFO.stream(entrada, config,
                                            stream_mode="updates", subgraphs=True):
            for no, carga in (atualizacao or {}).items():
                if nome := _nome_da_branch(no, carga):
                    branches[tuple(ns)] = nome
                # O `retriever` é o único nó cuja saída a tela precisa ANTES do fim: é ele que
                # diz quantas empresas entraram no fan-out, e sem isso a grade de progresso não
                # tem quantas linhas desenhar.
                if no == "retriever":
                    nomes = [s.nome for s in (carga.get("startups") or [])]
                    yield _sse({"tipo": "startups", "nomes": nomes})
                yield _sse({"tipo": "no", "no": no,
                            "escopo": "analise" if ns else "pai",
                            "empresa": branches.get(tuple(ns))})

        final = GRAFO.get_state(config).values
        run = montar_run(final, thread_id)
        persistencia.salvar(run)
        yield _sse({"tipo": "fim", "run": run})
    except Exception as exc:  # noqa: BLE001
        # O erro vai para a TELA, com o tipo da exceção. Um stream que morre em silêncio deixa
        # a interface girando para sempre, e quem está gravando não sabe se travou ou demora.
        yield _sse({"tipo": "erro", "mensagem": f"{type(exc).__name__}: {exc}"})
    finally:
        _EM_EXECUCAO.release()


@app.get("/")
def raiz() -> FileResponse:
    return FileResponse(ESTATICO / "index.html")


@app.get("/api/estado")
def estado() -> dict:
    """O que a tela precisa saber antes da primeira consulta — inclusive o que está DEGRADADO."""
    return {
        "rerank_provedor": RERANK.provedor,
        "max_startups_padrao": MAX_STARTUPS,
        "tem_credencial": tem_credencial(),
        "runs_salvos": len(persistencia.listar()),
    }


@app.get("/api/consulta")
def consulta(
    q: str = Query(..., min_length=1),
    max_startups: int = Query(MAX_STARTUPS, ge=1, le=30),
) -> StreamingResponse:
    thread_id = f"web-{uuid4()}"
    return StreamingResponse(
        _rodar(q, max_startups, thread_id),
        media_type="text/event-stream",
        # Sem isto, um proxy ou o próprio navegador podem BUFFERIZAR o stream e entregar tudo
        # de uma vez no fim — o que apagaria exatamente o que o SSE existe para mostrar.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/runs")
def runs() -> list[dict]:
    return persistencia.listar()


def _carregar(thread_id: str) -> dict:
    try:
        run = persistencia.carregar(thread_id)
    except persistencia.ThreadInvalido as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if run is None:
        raise HTTPException(status_code=404, detail=f"run {thread_id!r} não está salvo")
    return run


@app.get("/api/runs/{thread_id}")
def run(thread_id: str) -> dict:
    return _carregar(thread_id)


@app.get("/api/runs/{thread_id}/briefing.txt")
def briefing_txt(thread_id: str) -> PlainTextResponse:
    """O briefing BYTE A BYTE como o CLI o imprime — sem redação nova nesta camada.

    A tentação era "melhorar" o texto para a web. Seria uma segunda redação do entregável, e o
    que o gerente exportasse deixaria de ser o que o sistema produziu.
    """
    run = _carregar(thread_id)
    return PlainTextResponse(
        run.get("briefing") or "",
        headers={"Content-Disposition": f'attachment; filename="briefing-{thread_id}.txt"'},
    )


@app.get("/api/runs/{thread_id}/run.json")
def run_json(thread_id: str) -> PlainTextResponse:
    run = _carregar(thread_id)
    return PlainTextResponse(
        json.dumps(run, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="run-{thread_id}.json"'},
    )


class PerguntaVitrine(BaseModel):
    consulta: str


@app.post("/api/vitrine")
def vitrine(pergunta: PerguntaVitrine) -> dict:
    """As duas ordens da MESMA recuperação — o passo 7 mostrando o que ele fez.

    Este endpoint responde à única pergunta que o briefing não respondia: *por que esta
    tecnologia para esta empresa?* A resposta é o julgamento do cross-encoder, e ele até aqui
    acontecia e era descartado.

    A `consulta` vem da tela, mas não foi inventada por ela: é a string que
    `nvidia_rag.consulta_da_dor` montou durante o run, guardada no payload por
    `payload.consultas_do_perfil`. Uma consulta reescrita aqui mostraria o reranker
    trabalhando sobre uma pergunta que o grafo nunca fez.
    """
    if not pergunta.consulta.strip():
        raise HTTPException(status_code=400, detail="consulta vazia")
    if not _EM_EXECUCAO.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="há um run em andamento; a vitrine dividiria a cota de rerank com ele.")
    try:
        rastro = recuperar_com_rastro(pergunta.consulta)
    finally:
        _EM_EXECUCAO.release()

    if not rastro.rerank:
        return {
            "consulta": pergunta.consulta,
            # D-097 na tela: o modo barato não tem segunda coluna, e dizer isso é melhor que
            # desenhar duas colunas idênticas e deixar o leitor concluir que o passo 7 não faz nada.
            "aviso": (
                f"RERANK_PROVEDOR={RERANK.provedor}: o passo 7 está fora do caminho neste "
                "processo, então não existe uma segunda ordem para comparar. A busca híbrida "
                "sozinha já faz 95% de recall@1 (D-064) — mas quem julga qual tecnologia a "
                "empresa recebe é o reranker. Suba o servidor com RERANK_PROVEDOR=cohere."
            ) if RERANK.provedor == "nenhum" else
            "a recuperação não devolveu nenhuma passagem para esta consulta.",
        }

    # A POSIÇÃO DE ORIGEM É CALCULADA SOBRE A UNIÃO INTEIRA, não sobre o topo que a tela mostra.
    # É o que faz aparecer o caso interessante — a passagem que estava em 15º e subiu para 1ª.
    # Calculado aqui e não no navegador porque o cliente só recebe o topo.
    posicao = {p.chunk_id: i + 1 for i, p in enumerate(rastro.fusao)}
    topo = len(rastro.rerank)

    def _passagem(p, i: int, com_delta: bool, score=None) -> dict:
        antes = posicao[p.chunk_id]
        return {
            "posicao": i + 1,
            "posicao_fusao": antes,
            "delta": (antes - (i + 1)) if com_delta else 0,
            "chunk_id": p.chunk_id,
            "tecnologia": p.tecnologia,
            "caminho_secao": p.caminho_secao,
            # O TRECHO É O QUE DISTINGUE UM CHUNK DO VIZINHO, e o breadcrumb não serve para isso:
            # medido em 06/09 nesta mesma tela, os chunks 361 e 366 têm `caminho_secao` idêntico
            # (`NVIDIA AI Enterprise > NVIDIA AI Enterprise`) e a vitrine mostrava duas linhas
            # iguais, uma subindo 26 posições e a outra descendo 3 — ilegível. E o trecho é o que
            # o leitor de fato quer: a pergunta da vitrine é QUAL PASSAGEM o reranker escolheu.
            "trecho": " ".join(p.texto.split())[:180],
            "url_fonte": p.documento_url,
            "score_denso": rastro.scores_denso.get(p.chunk_id),
            "score_lexical": rastro.scores_lexical.get(p.chunk_id),
            "score_rerank": score,
        }

    return {
        "consulta": pergunta.consulta,
        "uniao": len(rastro.fusao),
        "fusao": [_passagem(p, i, False) for i, p in enumerate(rastro.fusao[:topo])],
        "rerank": [_passagem(p, i, True, s) for i, (p, s) in enumerate(rastro.rerank)],
        "nota": (
            f"A união dos dois braços trouxe {len(rastro.fusao)} passagens; as {topo} acima são "
            f"o topo de cada ordem. O reranker leu o par (consulta, passagem) junto — o "
            f"embedder vetoriza os dois separadamente e nunca vê a pergunta."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# O PASSO 8 GANHA PORTA — P-26
#
# `src/rag/geracao.py` faz geração com citação e ABSTENÇÃO, medida em 23/24 = 96% (D-040), e
# `pipeline.responder()` é a porta dela. Até 06/09 **nenhum caminho de execução chegava lá**:
# zero ocorrências de `responder` em `src/web/`, e nenhuma das 8 rotas a expunha. O passo 8 de 9
# que o TAPI especifica nominalmente não era acessível a usuário nenhum.
#
# O nó `nvidia_rag` não gera DE PROPÓSITO, e a razão está certa (`nvidia_rag.py:46`): o
# Recommendation Agent precisa dos trechos COM SCORE para cruzar com o perfil, e redigir ali
# perderia a evidência no meio do caminho. O que falhou foi a outra metade da frase — *"ela
# entra pela interface, não por este nó"* —, que nunca foi cumprida. Esta rota a cumpre.
#
# POR QUE UMA ROTA NOVA E NÃO UM MODO DE `/api/vitrine`
# ------------------------------------------------------
# A vitrine mostra as DUAS ORDENS de uma recuperação que o grafo JÁ FEZ — ela é uma janela para
# o run. Esta responde a uma pergunta que o HUMANO faz e que o grafo nunca fará. Fundi-las poria
# uma chamada de LLM dentro do endpoint que hoje é puro passo 6+7.
#
# E ISSO IMPORTA MAIS DO QUE PARECE: **o grafo continua com zero chamada de LLM em produção** —
# três flags `False` por medição —, e foi essa propriedade que o fez sobreviver ao 4º EOL do
# catálogo (D-087). A porta do passo 8 é uma superfície SEPARADA, fora do caminho do grafo, e é
# exatamente isso que preserva a propriedade. Se o modelo morrer na hora de gravar, o run
# continua rodando e só esta rota cai.
# ─────────────────────────────────────────────────────────────────────────────

class PerguntaRAG(BaseModel):
    consulta: str


@app.post("/api/perguntar")
def perguntar(pergunta: PerguntaRAG) -> dict:
    """Passos 6 + 7 + 8: o RAG responde com citação, ou RECUSA responder o que não sabe.

    A ABSTENÇÃO É O PRODUTO, NÃO A EXCEÇÃO. Um gerador de RAG comum é instruído a responder
    bem; este é instruído antes de tudo a reconhecer quando não deve. As passagens que chegam
    ao passo 8 já passaram por busca híbrida e cross-encoder — elas são, por construção,
    altamente relevantes —, e o erro que ele existe para evitar é responder com trecho
    perfeitamente relevante que não contém o fato, citando fonte real e inventando só o número.
    Duas medições fecharam a porta de qualquer atalho: nem a cosseno densa (margem −0,2810,
    D-033) nem o logit do cross-encoder (−17,6328, D-035) separam "não sei".
    """
    consulta = pergunta.consulta.strip()
    if not consulta:
        raise HTTPException(status_code=400, detail="consulta vazia")
    # Mesma disciplina de `/api/vitrine`, e aqui ela é mais dura: além da cota de rerank, esta
    # rota gasta uma chamada de LLM. 409 e não erro dentro de um stream porque quem chama é
    # `fetch`, que não reconecta sozinho — a tela mostra a frase no diálogo.
    if not _EM_EXECUCAO.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="há um run em andamento; a pergunta dividiria a cota de rerank com ele.")
    try:
        resposta = responder(consulta)
    finally:
        _EM_EXECUCAO.release()

    # QUEM RESPONDEU VAI NO PAYLOAD, pela mesma disciplina que pôs `rerank_provedor` no run
    # (D-097): a tela precisa poder dizer de quem é a resposta. Um provedor trocado pelo `.env`
    # é invisível para quem lê a tela, e a abstenção medida em 96% é do modelo de produção.
    citadas = set(resposta.indices_citados)
    return {
        "consulta": consulta,
        "abstencao": resposta.abstencao,
        "texto": resposta.texto,
        "motivo_abstencao": resposta.motivo_abstencao,
        "modelo": LLM.modelo,
        "rerank_provedor": RERANK.provedor,
        "citacoes": [
            {
                "i": i,
                # `citada` VEM DE `indices_citados`, e a distinção não é enfeite: citar menos do
                # que leu é comportamento correto e esperado (`RespostaRAG`). A tela mostra o que
                # sustentou a resposta E o que foi lido e descartado — e num caso de abstenção,
                # tudo o que ele leu e recusou, que é a demonstração inteira.
                "citada": i in citadas,
                "tecnologia": c.tecnologia,
                "trecho": " ".join(c.trecho.split())[:600],
                "url_fonte": c.url_fonte,
                "score_denso": c.score_denso,
                "score_lexical": c.score_lexical,
                "score_rerank": c.score_rerank,
            }
            for i, c in enumerate(resposta.citacoes)
        ],
    }
