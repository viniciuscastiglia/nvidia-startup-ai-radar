"""Testes do tokenizador do BM25. Sem banco e sem API — é função pura.

As três primeiras decisões de D-036 estão aqui como teste porque cada uma nasceu de um erro real
observado ao medir o gabarito, não de uma preferência de estilo.
"""

from src.rag.lexical import tokenizar


def test_dobra_acento_ou_o_vocabulario_vira_lixo():
    """Sem NFD, o `re` parte a palavra NO acento: 'genômica' -> 'gen' + 'mica'.

    Foi esse termo espúrio 'gen' que fez a q12 aparecer classificada como ATRAPALHA na primeira
    medição do sinal lexical do gabarito.
    """
    assert tokenizar("genômica") == ["genomica"]
    assert tokenizar("inferência") == ["inferencia"]
    assert tokenizar("português") == ["portugues"]


def test_ponto_sobrevive_no_identificador_e_morre_na_pontuacao():
    """`cudf.pandas` é a âncora da q14 e é identificador; `containers.` é fim de frase."""
    assert tokenizar("cudf.pandas") == ["cudf.pandas"]
    assert tokenizar("cuml.accel acelera") == ["cuml.accel", "acelera"]
    assert tokenizar("hardening de containers.") == ["hardening", "containers"]


def test_hifen_separa_para_casar_o_corpus():
    """'scikit-learn' vira dois tokens dos dois lados — consulta e corpus casam (q15)."""
    assert tokenizar("scikit-learn") == ["scikit", "learn"]


def test_stopwords_dos_dois_idiomas():
    """As consultas são em português e o corpus em inglês: os dois precisam ser filtrados."""
    assert tokenizar("o que é isso e aquilo") == ["aquilo"]
    assert tokenizar("the model and the data") == ["model", "data"]


def test_token_de_uma_letra_sai():
    assert tokenizar("a b c GPU x") == ["gpu"]
