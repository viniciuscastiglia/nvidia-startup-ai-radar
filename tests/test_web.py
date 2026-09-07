"""Testes da interface web.

O QUE ESTES TESTES GUARDAM, E POR QUE CADA UM EXISTE
-----------------------------------------------------
A camada web não tem regra de negócio — ela reusa `briefing.ordenar_analises`,
`briefing.rotulo_do_quadrante` e `nvidia_rag.consulta_da_dor`. Então o que dá para quebrar
aqui é o CONTRATO, e é isso que estes testes cobrem:

  - o corpus vazando no payload (o defeito silencioso: nada falha, o navegador só fica lento);
  - o briefing exportado deixar de ser byte a byte o que o sistema produziu;
  - o guarda de caminho do `thread_id`, que é entrada de fora;
  - a vitrine mentir quando o passo 7 está desligado (D-097 aplicado à tela).

TODOS RODAM SEM POSTGRES E SEM API: o estado é montado à mão, do mesmo jeito que
`test_grafo.py::test_subgrafo_roda_isolado` monta o `EstadoAnalise`. As rotas que INVOCAM o
grafo não são exercitadas aqui de propósito — quem cobre o grafo é `test_grafo.py`, e duplicar
isso faria a suíte pagar um run de API para testar uma função de serialização.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from src.state import (
    AnaliseStartup,
    CitacaoRAG,
    Diagnostico,
    DocumentoRef,
    DorObservada,
    Elegibilidade,
    Evidencia,
    PerfilStartup,
    PlanoDeBusca,
    Recomendacao,
    RespostaRAG,
    StartupRef,
)
from src.web import persistencia
from src.web.app import app
from src.web.payload import montar_run

TEXTO_DO_DOCUMENTO = "TEXTO INTEGRAL DO DOCUMENTO QUE NAO PODE CHEGAR AO NAVEGADOR"


def _evidencia() -> Evidencia:
    return Evidencia(documento_id=1, tipo_documento="site",
                     url_fonte="https://exemplo.com.br/", trecho="custo por inferência alto")


def _estado() -> dict:
    startup = StartupRef(
        startup_id=1, nome="Exemplar", site="https://exemplo.com.br/", setor="fintech",
        documentos=[DocumentoRef(documento_id=1, tipo="site", titulo="Home",
                                 url_fonte="https://exemplo.com.br/",
                                 conteudo_texto=TEXTO_DO_DOCUMENTO)],
    )
    perfil = PerfilStartup(
        startup_id=1, nome="Exemplar",
        dores_observadas=[DorObservada(dor="custo", texto="custo",
                                       evidencias=[_evidencia()])],
    )
    analise = AnaliseStartup(
        startup_id=1, nome="Exemplar", perfil=perfil,
        diagnostico=Diagnostico(classe="AI-enabled", maturidade_stack="baixa",
                                quadrante="prospect-de-evolucao", confianca="baixa",
                                justificativa="teste", sinal_verificado=True),
        elegibilidade=Elegibilidade(elegivel=True),
        recomendacoes=[Recomendacao(
            tecnologias=["NVIDIA NIM"], justificativa_tecnica="t", justificativa_negocio="n",
            prioridade="alta", complexidade="media", proxima_acao="conversar",
            evidencias=[_evidencia()], dores_enderecadas=["custo"])],
    )
    return {
        "consulta": "fintechs", "startups": [startup], "analises": [analise],
        "plano": PlanoDeBusca(consulta_original="fintechs", setores=["fintech"],
                              palavras_chave=["fintech"]),
        "briefing": "BRIEFING\n  linha com espaços à direita   \n",
    }


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    """Os runs vão para um diretório temporário — um teste não escreve em `data/runs/`."""
    monkeypatch.setattr(persistencia, "DIR_RUNS", tmp_path)
    return TestClient(app)


@pytest.fixture
def run_salvo(cliente):
    run = montar_run(_estado(), "web-teste")
    persistencia.salvar(run)
    return run


def test_conteudo_texto_nao_vai_para_o_navegador(run_salvo):
    """A regressão silenciosa: nada falha, o payload só passa a carregar o corpus inteiro."""
    bruto = json.dumps(run_salvo, ensure_ascii=False)
    assert TEXTO_DO_DOCUMENTO not in bruto
    # e o resto do documento CONTINUA: é a lista de fontes que a tela mostra
    assert run_salvo["startups"][0]["documentos"][0]["url_fonte"] == "https://exemplo.com.br/"
    assert run_salvo["startups"][0]["documentos"][0]["titulo"] == "Home"


def test_payload_carrega_o_carimbo_do_provedor_de_rerank(run_salvo):
    """D-097: sem este campo a tela não tem como avisar que o run não serve para julgar."""
    assert run_salvo["rerank_provedor"] in {"cohere", "nvidia", "nenhum"}


def test_payload_traz_a_consulta_que_o_grafo_fez_por_dor(run_salvo):
    """A vitrine precisa refazer a recuperação com a consulta REAL — ver `consultas_do_perfil`."""
    consultas = run_salvo["analises"][0]["consultas_rag"]
    assert [c["dor"] for c in consultas] == ["custo"]
    # o rótulo da dor mais o trecho literal da startup, que é o contrato de D-043
    assert consultas[0]["consulta"].startswith("custo")
    assert "custo por inferência alto" in consultas[0]["consulta"]


def test_rotulo_do_quadrante_vem_do_briefing_e_nao_da_tela(run_salvo):
    from src.agents.briefing import ROTULO_QUADRANTE
    assert run_salvo["analises"][0]["rotulo_quadrante"] == ROTULO_QUADRANTE["prospect-de-evolucao"]


def test_briefing_exportado_e_byte_a_byte_o_do_sistema(cliente, run_salvo):
    r = cliente.get("/api/runs/web-teste/briefing.txt")
    assert r.status_code == 200
    assert r.text == run_salvo["briefing"]      # inclusive os espaços à direita
    assert "attachment" in r.headers["content-disposition"]


def test_thread_id_fora_do_formato_nao_le_arquivo_nenhum(cliente):
    """`thread_id` vem da URL. Sem o guarda, `data/runs/../../.env` é um caminho válido."""
    assert cliente.get("/api/runs/.env").status_code == 400
    assert cliente.get("/api/runs/a.b").status_code == 400
    assert cliente.get("/api/runs/web-nao-existe").status_code == 404


def test_lista_de_runs_sobrevive_a_arquivo_corrompido(cliente, run_salvo, tmp_path):
    """A lista é a porta da rede de segurança: ela cair junto anula o propósito dela."""
    (tmp_path / "web-quebrado.json").write_text("{isto não é json", encoding="utf-8")
    r = cliente.get("/api/runs")
    assert r.status_code == 200
    assert [c["thread_id"] for c in r.json()] == ["web-teste"]


def test_vitrine_recusa_consulta_vazia(cliente):
    assert cliente.post("/api/vitrine", json={"consulta": "   "}).status_code == 400


def test_vitrine_avisa_em_vez_de_desenhar_duas_colunas_iguais(cliente, monkeypatch):
    """D-097 na tela. Com o passo 7 fora do caminho não existe segunda ordem — e repetir a
    primeira afirmaria que o reranker produziu aquela ordem, quando ele não rodou."""
    from dataclasses import replace

    from src.rag.pipeline import RastroRecuperacao
    import src.web.app as app_web

    # `ConfigRerank` é `frozen=True`, então o campo não se atribui — troca-se o OBJETO. E a
    # troca é explícita e não herdada do ambiente: sem ela, este teste passaria por acidente
    # quando `RERANK_PROVEDOR=nenhum` estivesse no `.env` e não testaria nada com `cohere`.
    monkeypatch.setattr(app_web, "RERANK", replace(app_web.RERANK, provedor="nenhum"))
    monkeypatch.setattr(app_web, "recuperar_com_rastro",
                        lambda *a, **k: RastroRecuperacao([], [], {}, {}))
    corpo = cliente.post("/api/vitrine", json={"consulta": "custo de inferência"}).json()
    assert "rerank" not in corpo
    assert "RERANK_PROVEDOR=nenhum" in corpo["aviso"]


def test_segundo_run_simultaneo_recebe_aviso_em_vez_de_ficar_esperando(cliente):
    """Dois runs ao mesmo tempo dobram a fila do throttle do Cohere (D-068) e disputam a cota
    mensal (D-093). O segundo tem de receber uma FRASE que explica, não um timeout mudo.

    O teste segura o cadeado à mão em vez de disparar dois runs de verdade: o que se quer
    verificar é a guarda, e um segundo run real custaria Postgres, API e minutos.
    """
    import src.web.app as app_web

    assert app_web._EM_EXECUCAO.acquire(blocking=False), "o cadeado já estava preso"
    try:
        r = cliente.get("/api/consulta", params={"q": "fintechs"})
        # SSE: a resposta é 200 e o erro viaja DENTRO do stream — um 409 aqui deixaria o
        # `EventSource` do navegador tentando reconectar, que é o oposto do que se quer.
        assert r.status_code == 200
        assert '"tipo": "erro"' in r.text
        assert "já existe um run em andamento" in r.text
        assert '"tipo": "inicio"' not in r.text, "o grafo não pode ter começado"
    finally:
        app_web._EM_EXECUCAO.release()


def test_vitrine_nao_disputa_o_rerank_com_um_run_em_andamento(cliente):
    """Aqui o 409 é o certo: `fetch` não reconecta sozinho, e a tela mostra a frase no diálogo."""
    import src.web.app as app_web

    assert app_web._EM_EXECUCAO.acquire(blocking=False)
    try:
        r = cliente.post("/api/vitrine", json={"consulta": "custo de inferência"})
        assert r.status_code == 409
        assert "run em andamento" in r.json()["detail"]
    finally:
        app_web._EM_EXECUCAO.release()


def test_o_cadeado_solta_depois_de_um_run_recusado(cliente):
    """A regressão que travaria a interface para sempre: recusar sem soltar. Um `return` dentro
    do `try` em vez de antes do `acquire` produziria exatamente isso, e nada falharia até o
    segundo uso."""
    import src.web.app as app_web

    app_web._EM_EXECUCAO.acquire(blocking=False)
    cliente.get("/api/consulta", params={"q": "fintechs"})   # recusado
    app_web._EM_EXECUCAO.release()
    assert app_web._EM_EXECUCAO.acquire(blocking=False), "o cadeado ficou preso após a recusa"
    app_web._EM_EXECUCAO.release()


# ─────────────────────────────────────────────────────────────────────────────
# A PORTA DO PASSO 8 — P-26
#
# O que estes testes guardam é o CONTRATO da abstenção, não a qualidade dela: quem mede a
# qualidade é `avaliar_rag.py --geracao`, sobre as 24 perguntas do gabarito, e isso custa API.
# O que dá para quebrar aqui sem nada falhar é a tela transformar um "não sei" em resposta —
# e é exatamente esse o defeito que apagaria a capacidade mais forte do sistema.
#
# `responder` é monkeypatchado, como `recuperar_com_rastro` já é no teste da vitrine: o
# objetivo é a serialização e a guarda, e um `responder` real custaria embedding, rerank e
# uma chamada de LLM por teste.
# ─────────────────────────────────────────────────────────────────────────────

def _citacao(tecnologia: str, trecho: str) -> CitacaoRAG:
    return CitacaoRAG(tecnologia=tecnologia, trecho=trecho,
                      url_fonte=f"https://exemplo.invalid/{tecnologia}")


def test_pergunta_vazia_nao_gasta_chamada_de_llm(cliente):
    assert cliente.post("/api/perguntar", json={"consulta": "   "}).status_code == 400


def test_pergunta_nao_disputa_a_cota_com_um_run_em_andamento(cliente):
    """Mesma guarda da vitrine, e aqui é mais cara: além do rerank, esta rota gasta um LLM."""
    import src.web.app as app_web

    assert app_web._EM_EXECUCAO.acquire(blocking=False)
    try:
        r = cliente.post("/api/perguntar", json={"consulta": "o que é o NIM?"})
        assert r.status_code == 409
        assert "run em andamento" in r.json()["detail"]
    finally:
        app_web._EM_EXECUCAO.release()


def test_o_cadeado_solta_quando_a_geracao_explode(cliente, monkeypatch):
    """A regressão que travaria a interface para sempre. `responder` fala com dois provedores
    externos — se ele levantar e o cadeado não soltar, nenhum run nem pergunta roda de novo até
    reiniciar o servidor, e ninguém descobre até o segundo uso."""
    import src.web.app as app_web

    def explode(*a, **k):
        raise RuntimeError("o provedor caiu")

    monkeypatch.setattr(app_web, "responder", explode)
    with pytest.raises(RuntimeError):
        cliente.post("/api/perguntar", json={"consulta": "o que é o NIM?"})
    assert app_web._EM_EXECUCAO.acquire(blocking=False), "o cadeado ficou preso após a falha"
    app_web._EM_EXECUCAO.release()


def test_a_abstencao_chega_a_tela_como_abstencao(cliente, monkeypatch):
    """O defeito que apagaria a capacidade: um `abstencao=True` que a tela lê como resposta.

    `texto` vem VAZIO e `motivo_abstencao` preenchido — se o payload perdesse o motivo, a tela
    mostraria um "não sei" sem dizer o que faltou, que é metade da demonstração.
    """
    import src.web.app as app_web

    monkeypatch.setattr(app_web, "responder", lambda *a, **k: RespostaRAG(
        texto="",
        citacoes=[_citacao("NVIDIA AI Enterprise", "licenciamento por GPU, por assinatura")],
        abstencao=True,
        motivo_abstencao="os trechos descrevem o modelo de licenciamento, não o preço",
    ))
    corpo = cliente.post("/api/perguntar", json={"consulta": "qual o preço?"}).json()
    assert corpo["abstencao"] is True
    assert corpo["texto"] == ""
    assert "não o preço" in corpo["motivo_abstencao"]
    # e as passagens que ele LEU E RECUSOU continuam no payload: são a demonstração
    assert [c["tecnologia"] for c in corpo["citacoes"]] == ["NVIDIA AI Enterprise"]
    assert corpo["citacoes"][0]["citada"] is False


def test_so_as_passagens_apontadas_saem_marcadas_como_citadas(cliente, monkeypatch):
    """`indices_citados` é o que torna a citação VERIFICÁVEL por código (D-040) — citar menos do
    que leu é comportamento correto. Marcar tudo como citada apagaria a distinção em silêncio,
    e a tela afirmaria que três passagens sustentam o que uma sustenta."""
    import src.web.app as app_web

    monkeypatch.setattr(app_web, "responder", lambda *a, **k: RespostaRAG(
        texto="O Triton Inference Server faz dynamic batching.",
        citacoes=[_citacao("NVIDIA NIM", "a"), _citacao("Triton Inference Server", "b"),
                  _citacao("TensorRT-LLM", "c")],
        indices_citados=[1],
    ))
    corpo = cliente.post("/api/perguntar", json={"consulta": "quem faz dynamic batching?"}).json()
    assert [c["citada"] for c in corpo["citacoes"]] == [False, True, False]
    assert corpo["abstencao"] is False
    assert corpo["motivo_abstencao"] is None


def test_o_payload_diz_QUEM_respondeu(cliente, monkeypatch):
    """Mesma disciplina que pôs `rerank_provedor` no run (D-097): um provedor trocado pelo
    `.env` é invisível para quem lê a tela, e o 23/24 de abstenção é do modelo de produção."""
    import src.web.app as app_web

    monkeypatch.setattr(app_web, "responder",
                        lambda *a, **k: RespostaRAG(texto="x", citacoes=[]))
    corpo = cliente.post("/api/perguntar", json={"consulta": "o que é o NIM?"}).json()
    assert corpo["modelo"] == app_web.LLM.modelo
    assert corpo["rerank_provedor"] in {"cohere", "nvidia", "nenhum"}
