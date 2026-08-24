"""Testes da fusão. São funções puras — sem banco, sem API.

Cada teste aqui ENCODA UMA DECISÃO de D-037, e não só um comportamento. Se um deles quebrar, o
que quebrou foi um argumento que está escrito em `decisoes.md` e vai para o vídeo.
"""

from src.rag.busca import Passagem
from src.rag.fusao import fundir_rrf, fundir_soma


def p(cid: int) -> Passagem:
    return Passagem(cid, "T", f"texto {cid}", f"T > s\n\ntexto {cid}", "T > s", f"http://d/{cid}")


def test_rrf_em_ranks_espelhados_so_obedece_a_ordem_dos_PESOS():
    """A propriedade estrutural que explica por que a fusão NÃO consertou a q19.

    Chunk A é 1º no denso e 2º no lexical; chunk B é 2º no denso e 1º no lexical — exatamente o
    que acontece na q19 entre o chunk do TensorRT-LLM (errado) e o do NIM (certo).

    Como o RRF só soma posições, e as posições são simétricas, o resultado não depende de NENHUMA
    evidência: depende só de qual peso é maior. Não existe ajuste intermediário que decida o caso
    pelo mérito — e o lado que consertaria a q19 (`lexical > denso`) é precisamente o que quebra
    a garantia crosslingual do teste seguinte.
    """
    a, b = p(1), p(2)
    listas = {"denso": [(a, 0.9), (b, 0.8)], "lexical": [(b, 5.0), (a, 4.0)]}

    def vencedor(peso_lexical: float) -> int:
        return fundir_rrf(listas, {"denso": 1.0, "lexical": peso_lexical}, k=10)[0][0].chunk_id

    def empatam(peso_lexical: float) -> bool:
        s = dict((pa.chunk_id, sc) for pa, sc in
                 fundir_rrf(listas, {"denso": 1.0, "lexical": peso_lexical}, k=10))
        return s[1] == s[2]

    assert vencedor(0.3) == 1 and vencedor(0.7) == 1     # denso manda
    assert empatam(1.0)                                   # pesos iguais: empate exato
    assert vencedor(2.0) == 2                             # lexico manda


def test_rrf_nao_deixa_o_lexico_deslocar_o_primeiro_do_denso():
    """A garantia que protege o caso crosslingual (q05).

    Um item 1º no denso e ausente do lexical soma w_denso/(k+1); um 1º no lexical e ausente do
    denso soma w_lexical/(k+1). Com w_denso > w_lexical, o denso vence sempre — e a q05 é uma
    pergunta em português sobre a palavra "Portuguese", onde o braço lexical é mudo.
    """
    so_denso, so_lexical = p(1), p(2)
    ordem = fundir_rrf(
        {"denso": [(so_denso, 0.5)], "lexical": [(so_lexical, 9.9)]},
        {"denso": 1.0, "lexical": 0.3}, k=10,
    )
    assert ordem[0][0].chunk_id == 1


def test_minmax_crava_o_topo_em_um_independente_da_qualidade():
    """O defeito que desqualificou a soma ponderada como motor de produção.

    Duas consultas com qualidade MUITO diferente produzem a mesma pontuação normalizada para o
    1º colocado. É o que faz a q20 — que não tem resposta na base — parecer tão confiante
    quanto um acerto perfeito.
    """
    otimo = {"denso": [(p(1), 0.95), (p(2), 0.10)]}
    pessimo = {"denso": [(p(1), 0.28), (p(2), 0.10)]}
    pesos = {"denso": 1.0}
    assert fundir_soma(otimo, pesos, "minmax")[0][1] == fundir_soma(pessimo, pesos, "minmax")[0][1] == 1.0


def test_minmax_com_faixa_nula_nao_finge_ordem():
    """Todos os scores iguais = nenhuma informação de ordem. 1.0 diria 'todos perfeitos'."""
    iguais = {"denso": [(p(1), 0.4), (p(2), 0.4), (p(3), 0.4)]}
    assert all(s == 0.5 for _, s in fundir_soma(iguais, {"denso": 1.0}, "minmax"))


def test_ausencia_de_um_braco_nao_quebra_a_fusao():
    """A q18 devolve lista lexical VAZIA: nenhum termo da consulta existe no corpus em inglês."""
    listas = {"denso": [(p(1), 0.5), (p(2), 0.4)], "lexical": []}
    ordem = fundir_rrf(listas, {"denso": 1.0, "lexical": 0.3}, k=10)
    assert [pa.chunk_id for pa, _ in ordem] == [1, 2]
