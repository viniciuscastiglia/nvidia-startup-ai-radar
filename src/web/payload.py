"""O contrato de dados entre o grafo e a tela.

POR QUE NÃO EXISTE UM DTO NOVO AQUI
------------------------------------
Os modelos de `src/state.py` JÁ são o contrato. `Recomendacao` existe para que "cumpre os 7
campos obrigatórios do TAPI" seja verificável lendo uma classe (D-045); um DTO paralelo
duplicaria esses 7 campos num segundo lugar, e o dia em que os dois divergissem ninguém
descobriria pela tela. `model_dump(mode="json")` já resolve `date` -> ISO, que era o único
motivo real para escrever conversão à mão.

O QUE ESTE MÓDULO DE FATO FAZ, ENTÃO, SÃO TRÊS COISAS QUE O `model_dump` NÃO FAZ
--------------------------------------------------------------------------------
1. **Tira o corpus do payload.** `StartupRef.documentos[*].conteudo_texto` é o documento
   INTEIRO — é sobre ele que o Extractor trabalha, e ele não tem o que fazer no navegador.
   Serializado cru, um run de 5 empresas leva ~15 documentos completos pelo fio.
2. **Carimba o run.** `rerank_provedor` no topo, porque D-097 mediu que julgar recomendação com
   o passo 7 desligado é julgar outro sistema — a tela precisa poder avisar. É o mesmo carimbo
   que `avaliar_agentes.py --regras-tapi` usa para RECUSAR um run feito com `nenhum`.
3. **Guarda a consulta que o grafo fez a cada dor**, para a vitrine do passo 7 poder refazer
   exatamente aquela recuperação — e não uma parecida. Ver `consultas_do_perfil`.

O QUE ELE NÃO PÕE NO PAYLOAD, DE PROPÓSITO: `plano.estrategia_analise` e `plano.exige_sinais_ia`.
São dois dos quatro campos da P-14 — calculados corretamente e sem nenhum leitor. Mostrá-los na
tela não fecha a P-14: faria a interface EXIBIR uma "estratégia de análise" que nó nenhum do
subgrafo lê, o que é pior que a lacuna atual, porque passa a afirmar ao gerente que aquilo
governou a análise. A P-14 se fecha no subgrafo ou no diagrama, não aqui.
"""

from __future__ import annotations

from datetime import datetime

from src.agents.briefing import ordenar_analises, rotulo_do_quadrante
from src.agents.nvidia_rag import consulta_da_dor
from src.config import RERANK
from src.state import AnaliseStartup, EstadoRadar, PerfilStartup, StartupRef

# `__all__` é a chave do pydantic para "todo item da lista". Sem esta exclusão o payload leva o
# corpus junto — ver o item 1 do docstring. Título, tipo e `url_fonte` FICAM: são a lista de
# fontes que a tela mostra, e o `url_fonte` é o link que torna a evidência conferível.
SEM_TEXTO_BRUTO = {"documentos": {"__all__": {"conteudo_texto"}}}


def _startup(s: StartupRef) -> dict:
    return s.model_dump(mode="json", exclude=SEM_TEXTO_BRUTO)


def consultas_do_perfil(perfil: PerfilStartup | None) -> list[dict]:
    """A string que `nvidia_rag` mandou ao RAG por dor — a mesma função, não uma reescrita.

    A vitrine do passo 7 precisa refazer a recuperação para mostrar as duas ordens. Se ela
    montasse a consulta por conta própria, mostraria o reranker trabalhando sobre uma consulta
    que o grafo nunca fez — um painel bonito sobre outra pergunta. Reusar `consulta_da_dor`
    (`src/agents/nvidia_rag.py:90`) é o que faz a vitrine ser uma janela para o run, e não uma
    demonstração paralela.

    A guarda de consulta vazia é a mesma de `nvidia_rag.node`: dor sem rótulo e sem evidência
    não vai ao embedder, que responde HTTP 400.
    """
    if perfil is None:
        return []
    stack = [a.texto for a in perfil.stack_declarada]
    saida = []
    for dor in perfil.dores_observadas:
        consulta = consulta_da_dor(dor, stack)
        if consulta:
            saida.append({"dor": dor.dor, "consulta": consulta})
    return saida


def _analise(a: AnaliseStartup) -> dict:
    d = a.model_dump(mode="json")
    # Os dois campos calculados PELA CAMADA WEB ficam com nome próprio, para que quem ler o JSON
    # saiba que não saíram do grafo. O rótulo vem de `briefing.rotulo_do_quadrante` — a tela e o
    # `.txt` exportado do mesmo run não podem discordar sobre o que a empresa é.
    d["rotulo_quadrante"] = rotulo_do_quadrante(a.diagnostico) if a.diagnostico else None
    d["consultas_rag"] = consultas_do_perfil(a.perfil)
    return d


def montar_run(estado: EstadoRadar, thread_id: str) -> dict:
    """O estado final do grafo -> o JSON que a tela e o arquivo salvo compartilham.

    UM formato só para os dois: o run que a tela desenha ao vivo é byte a byte o run que
    `persistencia.salvar` grava e que "abrir run salvo" carrega. Dois formatos dariam duas
    telas para manter, e a segunda só seria exercitada no dia da gravação.
    """
    plano = estado.get("plano")
    analises = ordenar_analises(estado.get("analises") or [])
    return {
        "thread_id": thread_id,
        "consulta": estado.get("consulta") or "",
        "gerado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
        # D-097: sem este campo a tela não tem como saber que está mostrando um run barato.
        "rerank_provedor": RERANK.provedor,
        "plano": (
            {
                "setores": plano.setores,
                "estagios": plano.estagios,
                "localizacoes": plano.localizacoes,
                "palavras_chave": plano.palavras_chave,
                "max_startups": plano.max_startups,
            }
            if plano
            else None
        ),
        # D-081: `None` quando não houve plano (o run nem chegou lá) é diferente de `False`
        # ("a consulta não discriminou nada"). Só o `False` aciona o aviso na tela — um `None`
        # tratado como `False` faria a interface gritar sobre uma consulta que nunca rodou.
        "discrimina": plano.discrimina() if plano else None,
        "erros": estado.get("erros") or [],
        "startups": [_startup(s) for s in (estado.get("startups") or [])],
        "analises": [_analise(a) for a in analises],
        "briefing": estado.get("briefing") or "",
    }
