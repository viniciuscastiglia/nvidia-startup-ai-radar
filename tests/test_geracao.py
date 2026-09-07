"""Testes do passo 8 — `src/rag/geracao.py`, onde mora a abstenção.

POR QUE ESTE ARQUIVO SÓ EXISTE AGORA, E POR QUE ISSO É UM ACHADO
-----------------------------------------------------------------
Até 06/09 **nenhum arquivo de teste citava `rag/geracao.py`**. A suíte estava verde com 102
testes, e o módulo que carrega a capacidade mais forte do RAG — recusar responder o que não
sabe — não tinha um. A cobertura era APARENTE: o passo 8 nunca era exercitado porque nenhum
caminho de execução chegava nele (P-26). Um módulo inalcançável não quebra teste nenhum.

Agora ele é caminho de usuário, e o que estes testes guardam é o que **não custa API**:

  - o curto-circuito de zero passagens, que existe para NÃO gastar chamada onde o modelo
    inventaria (é o caso em que não há o que ler);
  - a validação de `indices_citados`, que é o que torna a citação verificável por CÓDIGO em
    vez de plausível (D-040);
  - o prefixo de tecnologia em `formatar`, que é a âncora de atribuição do modelo.

O QUE ELES DELIBERADAMENTE NÃO MEDEM: se o modelo abstém quando deve. Isso é
`avaliar_rag.py --geracao` sobre as 24 perguntas do gabarito — 23/24 = 96% (D-040) —, custa
API, e um teste unitário que fingisse medi-lo seria pior que nenhum.
"""

from __future__ import annotations

from src.rag import geracao
from src.state import CitacaoRAG


def _citacao(tecnologia: str = "NVIDIA NIM", trecho: str = "texto") -> CitacaoRAG:
    return CitacaoRAG(tecnologia=tecnologia, trecho=trecho,
                      url_fonte=f"https://exemplo.invalid/{tecnologia}")


class _LLMQueExplode:
    """Se o curto-circuito funciona, ninguém chama isto."""

    def invoke(self, _):  # noqa: D102
        raise AssertionError("o LLM foi chamado com zero passagens")


def test_sem_passagens_absteve_sem_chamar_o_llm(monkeypatch):
    """Zero passagens não é caso de LLM: não há o que ler. Gastar uma chamada aqui seria pedir
    ao modelo que decidisse sobre o vazio — que é exatamente onde ele inventaria."""
    monkeypatch.setattr(geracao, "estruturado", lambda *a, **k: _LLMQueExplode())
    r = geracao.gerar("qualquer pergunta", [])
    assert r.abstencao is True
    assert r.texto == ""
    assert r.citacoes == []
    assert "não devolveu nenhum trecho" in r.motivo_abstencao


def _finge_modelo(monkeypatch, **campos):
    """Substitui o cliente por um que devolve exatamente o `SaidaGerador` pedido."""
    saida = geracao.SaidaGerador(**campos)
    monkeypatch.setattr(geracao, "estruturado",
                        lambda *a, **k: type("_", (), {"invoke": lambda self, _: saida})())


def test_indice_fora_da_faixa_e_descartado_mas_as_passagens_ficam(monkeypatch):
    """O ponto inteiro de citar por ÍNDICE: um índice fora da faixa é erro detectável por
    código, e uma URL escrita no meio de um parágrafo não é.

    As passagens NÃO são descartadas junto — elas continuam anexadas para auditoria, ainda que
    o modelo tenha apontado errado. Perder as duas coisas ao mesmo tempo apagaria a evidência
    justamente no caso em que se quer conferir o que o modelo leu.
    """
    citacoes = [_citacao("NVIDIA NIM"), _citacao("Triton Inference Server")]
    _finge_modelo(monkeypatch, texto="resposta", indices_citados=[1, 7, -1])
    r = geracao.gerar("pergunta", citacoes)
    assert r.indices_citados == [1]
    assert len(r.citacoes) == 2


def test_motivo_de_abstencao_nao_sobrevive_a_uma_resposta(monkeypatch):
    """Um `motivo_abstencao` preenchido junto de `abstencao=False` é um campo que contradiz o
    booleano ao lado — e quem lê a tela não sabe qual dos dois vale."""
    _finge_modelo(monkeypatch, texto="o Triton faz dynamic batching",
                  abstencao=False, motivo_abstencao="sobra de um prompt anterior")
    r = geracao.gerar("pergunta", [_citacao()])
    assert r.abstencao is False
    assert r.motivo_abstencao is None


def test_a_abstencao_do_modelo_atravessa_com_o_motivo(monkeypatch):
    _finge_modelo(monkeypatch, texto="", abstencao=True,
                  motivo_abstencao="os trechos descrevem o licenciamento, não o preço")
    r = geracao.gerar("qual o preço?", [_citacao("NVIDIA AI Enterprise")])
    assert r.abstencao is True
    assert "não o preço" in r.motivo_abstencao
    assert len(r.citacoes) == 1, "a passagem lida e recusada tem de continuar no resultado"


def test_formatar_prefixa_a_tecnologia_em_cada_trecho():
    """A âncora de atribuição do modelo, e ela vem da CURADORIA (`fontes.yaml`), não de um
    heading do documento. Sem ela, o trecho da q19 pareceria ser sobre TensorRT-LLM."""
    texto = geracao.formatar([_citacao("NVIDIA NIM", "empacota o modelo"),
                              _citacao("TensorRT-LLM", "quantização")])
    assert texto.startswith("[0] (NVIDIA NIM) empacota o modelo")
    assert "[1] (TensorRT-LLM) quantização" in texto
