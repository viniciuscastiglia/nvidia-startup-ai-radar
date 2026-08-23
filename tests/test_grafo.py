"""Testes da sessão 01.

O teste que mais importa é `test_toda_recomendacao_tem_evidencia`: ele codifica o requisito
que o TAPI grifa duas vezes — "toda conclusão do sistema sobre uma startup precisa apontar
para o documento que a sustenta". Enquanto ele passar, a rastreabilidade não regrediu.

`test_subgrafo_roda_isolado` existe para provar a afirmação de D-007: a topologia de subgrafo
foi escolhida em parte porque a análise de uma startup é testável sem subir o grafo pai.
Um teste que não conseguisse fazer isso invalidaria a justificativa da decisão.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.agents.evidence_validator import avaliar
from src.graph import GRAFO, SUBGRAFO, construir_grafo
from src.state import (
    Afirmacao,
    DocumentoRef,
    Evidencia,
    PlanoDeBusca,
    StartupRef,
    derivar_quadrante,
)

CONSULTA = "startups brasileiras de saúde usando IA"


@pytest.fixture(scope="module")
def resultado():
    return GRAFO.invoke({"consulta": CONSULTA},
                        config={"configurable": {"thread_id": "pytest"}})


def test_grafo_roda_ponta_a_ponta(resultado):
    assert resultado.get("briefing"), "o Briefing Agent não produziu saída"
    assert resultado["analises"], "nenhuma análise chegou ao fan-in"


def test_fan_in_preserva_todas_as_branches(resultado):
    """O reducer operator.add em EstadoRadar.analises é o que faz o fan-in.
    Se ele fosse substituído por atribuição simples, sobraria uma análise só."""
    assert len(resultado["analises"]) == len(resultado["startups"])


def test_toda_recomendacao_tem_evidencia(resultado):
    """A invariante de rastreabilidade. Se este teste cair, o projeto perde o critério 3."""
    for analise in resultado["analises"]:
        for rec in analise.recomendacoes:
            assert rec.evidencias, f"{analise.nome}: recomendação {rec.tecnologias} sem evidência"
            for ev in rec.evidencias:
                assert ev.url_fonte.startswith("http"), "evidência sem url_fonte resolvível"
                assert ev.trecho.strip(), "evidência sem trecho literal"
                assert ev.documento_id > 0, "evidência sem documento_id da base"


def test_recomendacao_tem_os_sete_campos_do_tapi(resultado):
    obrigatorios = ["tecnologias", "justificativa_tecnica", "justificativa_negocio",
                    "prioridade", "complexidade", "proxima_acao", "evidencias"]
    for analise in resultado["analises"]:
        for rec in analise.recomendacoes:
            for campo in obrigatorios:
                assert getattr(rec, campo), f"{analise.nome}: campo obrigatório {campo!r} vazio"


def test_subgrafo_roda_isolado():
    """Prova a justificativa de D-007: a análise de uma startup não depende do grafo pai."""
    from src.state import StartupRef
    doc = DocumentoRef(
        documento_id=999, tipo="vaga", titulo="ML Engineer",
        url_fonte="https://exemplo.test/vaga", data_publicacao=date.today(),
        conteudo_texto=("Buscamos engenheiro para otimizar inferência de LLM com quantização e "
                        "self-hosted em GPU, reduzindo latência e custo por token em produção."),
    )
    startup = StartupRef(startup_id=999, nome="Teste", setor="saúde", documentos=[doc])
    final = SUBGRAFO.invoke({"plano": PlanoDeBusca(consulta_original="x"), "startup": startup})
    assert final.get("perfil") is not None
    assert final.get("diagnostico") is not None


def test_non_ai_nao_recebe_recomendacao():
    """Regra 1 de contexto/03 §4: non-AI está fora do funil."""
    assert derivar_quadrante("non-AI", "baixa") == "fora-do-funil"
    assert derivar_quadrante("non-AI", "alta") == "fora-do-funil"


def test_dois_eixos_separam_sweet_spot_de_ja_otimizada():
    """O que justifica o modelo de dois eixos: mesma CLASSE, prioridade oposta."""
    assert derivar_quadrante("AI-native", "baixa") == "sweet-spot"
    assert derivar_quadrante("AI-native", "alta") == "ja-otimizada"


def _ev(doc_id, tipo, quando):
    return Evidencia(documento_id=doc_id, tipo_documento=tipo,
                     url_fonte=f"https://exemplo.test/{doc_id}", trecho="trecho",
                     data_publicacao=quando)


def test_validator_regra_1_sem_evidencia_nao_valida():
    conf, ok, _ = avaliar(Afirmacao(texto="x", evidencias=[]))
    assert (conf, ok) == ("baixa", False)


def test_validator_regra_2_corroboracao_entre_tipos_vale_mais():
    hoje = date.today()
    dois_tipos = Afirmacao(texto="x", evidencias=[_ev(1, "vaga", hoje), _ev(2, "blog", hoje)])
    um_tipo = Afirmacao(texto="x", evidencias=[_ev(1, "vaga", hoje), _ev(2, "vaga", hoje)])
    assert avaliar(dois_tipos)[0] == "alta"
    assert avaliar(um_tipo)[0] == "media"


def test_validator_regra_3_documento_antigo_rebaixa():
    antigo = date(date.today().year - 5, 1, 1)
    a = Afirmacao(texto="x", evidencias=[_ev(1, "vaga", antigo), _ev(2, "blog", antigo)])
    conf, ok, motivo = avaliar(a)
    assert conf == "media" and ok is True, "regra 3 deve rebaixar, não invalidar"
    assert "24 meses" in motivo


def test_validator_regra_4_nunca_deleta():
    """Ausência de sinal != sinal negativo (D-010). O validator anota; quem barra é o
    Recommendation."""
    a = Afirmacao(texto="x", evidencias=[])
    conf, validada, _ = avaliar(a)
    assert a.texto == "x", "a afirmação não pode ser destruída pelo validator"
    assert conf == "baixa"


# ─────────────────────────────────────────────────────────────────────────────
# Regressões da revisão de 23/08 — três defeitos achados executando o grafo, não lendo.
# Cada um vira teste porque os três só aparecem em caminhos que o "caminho feliz" não toca:
# consulta sem resultado, execução repetida, e etapa que levanta exceção.
# ─────────────────────────────────────────────────────────────────────────────


def _startup_de_teste(nome="Acme", startup_id=1):
    doc = DocumentoRef(documento_id=1, tipo="site", titulo="t", url_fonte="http://exemplo.test",
                       conteudo_texto="Plataforma de IA para saúde. Reduzimos custo de inferência.")
    return StartupRef(startup_id=startup_id, nome=nome, site="http://exemplo.test",
                      setor="saude", documentos=[doc])


def test_consulta_sem_resultado_ainda_produz_briefing(monkeypatch):
    """D-023. Fan-out vazio não agenda tarefa nenhuma, e o briefing só era alcançável pela
    aresta vinda de `analisar_startup` — então o run terminava SEM relatório. `defer=True`
    não salva: ele atrasa o que foi agendado, não agenda o que não foi."""
    import src.agents.retriever as r
    monkeypatch.setattr(r, "buscar_startups", lambda plano: [])
    final = construir_grafo().invoke({"consulta": "consulta que não casa nada"},
                                     config={"configurable": {"thread_id": "vazio"}})
    assert final.get("briefing"), "consulta sem resultado terminou sem briefing"
    assert "NENHUMA STARTUP CASOU" in final["briefing"]
    assert final["erros"], "o motivo de não ter casado nada precisa chegar ao relatório"


def test_runs_distintos_nao_acumulam_analises(monkeypatch):
    """D-022. `thread_id` fixo + reducer operator.add = a segunda execução SOMA na primeira.
    Cada run é um thread novo; retomar é opt-in via --thread."""
    import src.agents.retriever as r
    monkeypatch.setattr(r, "buscar_startups", lambda plano: [_startup_de_teste()])
    g = construir_grafo()
    r1 = g.invoke({"consulta": "saúde"}, config={"configurable": {"thread_id": "run-a"}})
    r2 = g.invoke({"consulta": "saúde"}, config={"configurable": {"thread_id": "run-b"}})
    assert len(r1["analises"]) == 1
    assert len(r2["analises"]) == 1, "run novo herdou as análises do run anterior"


def test_retomar_o_mesmo_thread_continua_de_onde_parou(monkeypatch):
    """A contraprova do teste acima: a acumulação não é bug do reducer, é a semântica de
    thread. Com o MESMO thread_id, continuar é o comportamento CORRETO — e por isso o
    default do CLI precisa ser um thread novo."""
    import src.agents.retriever as r
    monkeypatch.setattr(r, "buscar_startups", lambda plano: [_startup_de_teste()])
    g = construir_grafo()
    cfg = {"configurable": {"thread_id": "mesmo-thread"}}
    g.invoke({"consulta": "saúde"}, config=cfg)
    segundo = g.invoke({"consulta": "saúde"}, config=cfg)
    assert len(segundo["analises"]) == 2


def test_falha_no_meio_da_analise_preserva_o_trabalho_parcial(monkeypatch):
    """D-024. É o teste que separa `error_handler` de um try/except em volta do subgrafo:
    o Extractor já rodou, então o perfil TEM que sobreviver à falha do Classifier.
    Com try/except envolvendo o subgrafo inteiro, esta asserção falha — volta tudo vazio."""
    import src.agents.classifier as c

    def explode(state):
        raise ValueError("dado ruim nesta startup")

    monkeypatch.setattr(c, "node", explode)
    from src.graph import construir_subgrafo
    final = construir_subgrafo().invoke(
        {"plano": PlanoDeBusca(consulta_original="x"), "startup": _startup_de_teste()}
    )
    assert final.get("erros"), "a falha não foi registrada"
    assert "classifier" in final["erros"][0] and "dado ruim" in final["erros"][0]
    assert final.get("perfil") is not None, \
        "o perfil extraído ANTES da falha foi descartado — é isso que o error_handler evita"
    assert final.get("diagnostico") is None, "não pode haver diagnóstico se o classifier caiu"
