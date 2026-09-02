"""O seletor do trecho técnico — P-10 (D-086).

A RÉGUA MORA EM `data/avaliacao/justificativas.yaml` e é rodada por
`avaliar_agentes.py --justificativas`, que compara o seletor com a linha trivial sobre 30 chunks
do corpus. **Estes testes não a duplicam**: aqui ficam as invariantes que a régua não vê — a forma
do span, o fallback, e o nível de PASSAGEM, que a régua (que mede dentro de um chunk) não alcança.
"""

from __future__ import annotations

from src.agents.justificativa import ORCAMENTO, melhor_trecho, pontuar
from src.agents.nvidia_rag import node
from src.state import CitacaoRAG

TECNICO = ("Holoscan is a real-time runtime for building GPU-accelerated systems that ingest "
           "high-bandwidth, multimodal, multi-rate sensor data and perform AI inference.")
CONVITE = ("Join our ecosystem of startups, partners, and developers building healthcare and "
           "life sciences platforms and applications. Learn more and get started today.")
CASE = ("Writer / Startup Pens Generative AI Success Story With NVIDIA NeMo\n"
        "Using NVIDIA NeMo, Writer is building LLMs that are helping hundreds of companies.")


def test_tecnico_pontua_acima_de_convite():
    """O par mínimo do critério. Sem ele, "o seletor funciona" é afirmação sem lado oposto."""
    assert pontuar(TECNICO) > pontuar(CONVITE)


def test_case_de_terceiro_pontua_abaixo_de_tecnico():
    """O defeito que abriu P-10: a justificativa saía como case da Writer (D-082)."""
    assert pontuar(TECNICO) > pontuar(CASE)


def test_menu_de_navegacao_perde_para_o_paragrafo_do_mesmo_chunk():
    """O chunk 127 real: menu colado na frente de conteúdo técnico bom. O que o gerente lia era
    o menu, porque o campo era o chunk inteiro e o briefing imprime os 150 primeiros."""
    chunk = ("Learn More\n- Documentation\n- Getting Started Guide\n- Examples\n- FAQs\n"
             "- Security Guidelines\nTelemetry and Privacy\n"
             "The NVIDIA NeMo Guardrails library collects anonymous telemetry to help NVIDIA "
             "understand which deployment patterns and safety features are most used. The library "
             "emits one usage event when you instantiate LLMRails, IORails, or Guardrails.")
    escolhido = melhor_trecho(chunk)
    assert "collects anonymous telemetry" in escolhido
    assert "- Getting Started Guide" not in escolhido


def test_span_respeita_o_orcamento():
    """`justificativa_tecnica` é um campo de briefing, não um despejo de documento: o chunk
    mediano tem 803 caracteres e o campo carregava todos eles."""
    chunk = "\n".join(f"Linha {i} sobre inference, latency e throughput em GPU." for i in range(40))
    assert len(melhor_trecho(chunk)) <= ORCAMENTO


def test_texto_curto_demais_volta_inteiro_e_nunca_vazio():
    """`justificativa_tecnica` é um dos 7 campos obrigatórios do TAPI. Campo vazio não é
    "quase lá" — é uma recomendação que o gerente não consegue levar para a conversa."""
    assert melhor_trecho("Curto.") == "Curto."
    assert melhor_trecho("   ") == ""


def _citacao(trecho: str, url: str, rerank: float) -> CitacaoRAG:
    return CitacaoRAG(tecnologia="NVIDIA NeMo", trecho=trecho, url_fonte=url, score_rerank=rerank)


def test_entre_passagens_da_MESMA_pagina_vence_a_mais_tecnica(monkeypatch):
    """O NÍVEL DE PASSAGEM, que a régua não alcança.

    Todo chunk de uma tecnologia compartilha a URL da página, então a deduplicação por URL decidia
    qual TEXTO representa aquela tecnologia — e decidia por posição do reranker, que ordena por
    relevância à consulta e não por servir de justificativa. Medido em 02/09: vencia o chunk de
    cases da Writer, enquanto outro chunk da mesma página dizia o que o NeMo faz.
    """
    from src.agents import nvidia_rag
    from src.state import Afirmacao, DorObservada, Evidencia, PerfilStartup

    url = "https://www.nvidia.com/en-us/ai-data-science/products/nemo/"
    monkeypatch.setattr(nvidia_rag, "buscar_com_rerank",
                        lambda c, k: [_citacao(CASE, url, 9.0), _citacao(TECNICO, url, 1.0)])
    perfil = PerfilStartup(
        startup_id=1, nome="Acme",
        dores_observadas=[DorObservada(
            dor="custo", texto="t", validada=True,
            evidencias=[Evidencia(documento_id=1, tipo_documento="site",
                                  url_fonte="https://exemplo.test/", trecho="custo alto")])],
        afirmacoes_livres=[Afirmacao(texto="x", evidencias=[])],
    )
    citacoes = node({"perfil": perfil})["citacoes_rag"]
    assert len(citacoes) == 1, "duas passagens da mesma página viraram duas citações"
    assert citacoes[0].trecho == TECNICO, "venceu o case por estar melhor colocado no reranker"
    # O score acompanha o TEXTO escolhido: um score que descreve um chunk que ninguém vê não
    # descreve nada, e `CitacaoRAG` existe para mostrar o reranker mudando a ordem.
    assert citacoes[0].score_rerank == 1.0
