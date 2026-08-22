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
from src.graph import GRAFO, SUBGRAFO
from src.state import Afirmacao, DocumentoRef, Evidencia, PlanoDeBusca, derivar_quadrante

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
