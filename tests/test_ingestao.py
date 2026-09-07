"""Testes do cache das fontes do RAG — a propriedade que o clone limpo depende.

O QUE ESTES TESTES GUARDAM
---------------------------
`scripts/ingerir_nvidia.py` baixava ao vivo das 16 URLs, e em 03/09 o clone limpo produziu a
**mesma contagem de chunks com hash diferente** (D-089): a página do TensorRT-LLM rolou o mural
de novidades. Como o gabarito de 24 perguntas aponta URL **e frase-âncora**, quem avalia rodava
`avaliar_rag.py` contra um corpus que não era o medido.

A correção é um cache versionado, e a propriedade que ela compra é **negativa**: sem
`--refetch`, o script NÃO TOCA A REDE. Propriedade negativa não se verifica olhando a saída —
uma execução com cache quente e uma sem cache imprimem a mesma tabela. O teste força o caso
passando um cliente que EXPLODE se alguém chamar `.get`, que é a única forma de provar que a
chamada não aconteceu.

Zero rede e zero API: o único I/O é `tmp_path`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import ingerir_nvidia as ing


class ClienteQueExplode:
    """Se o cache funciona, ninguém chama isto. É o assert de verdade do primeiro teste."""

    def get(self, url):  # noqa: D102
        raise AssertionError(f"a rede foi tocada para {url} — o cache não foi usado")


class ClienteFalso:
    def __init__(self, texto: str):
        self.texto, self.chamadas = texto, 0

    def get(self, url):  # noqa: D102
        self.chamadas += 1
        return self

    def raise_for_status(self):  # noqa: D102
        return None

    @property
    def text(self) -> str:
        return self.texto


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(ing, "CACHE", tmp_path)
    monkeypatch.setattr(ing, "INDICE_CACHE", tmp_path / "indice.json")
    return tmp_path


FONTE = {"tecnologia": "NVIDIA NIM", "formato": "html",
         "url_fetch": "https://exemplo.invalid/nim"}


def test_com_cache_quente_a_rede_nao_e_tocada(cache):
    """A propriedade inteira do clone limpo, e ela é negativa: nenhuma chamada de rede."""
    ing.caminho_de_cache(FONTE).write_text("<html>conteúdo congelado</html>", encoding="utf-8")
    bruto, origem = ing.buscar(FONTE, ClienteQueExplode())
    assert origem == "cache"
    assert bruto == "<html>conteúdo congelado</html>"


def test_refetch_toca_a_rede_e_reescreve_o_cache(cache):
    """`--refetch` é a ÚNICA porta para a rede — se ela não abrir, a deriva fica invisível."""
    ing.caminho_de_cache(FONTE).write_text("<html>velho</html>", encoding="utf-8")
    cliente = ClienteFalso("<html>novo</html>")
    bruto, origem = ing.buscar(FONTE, cliente, refetch=True)
    assert (origem, cliente.chamadas, bruto) == ("rede", 1, "<html>novo</html>")
    assert ing.caminho_de_cache(FONTE).read_text(encoding="utf-8") == "<html>novo</html>"


def test_cache_frio_baixa_uma_vez_e_a_segunda_leitura_ja_e_offline(cache):
    """O caminho de quem clona sem o cache commitado: baixa, e a partir daí não depende da rede."""
    cliente = ClienteFalso("<html>baixado</html>")
    assert ing.buscar(FONTE, cliente)[1] == "rede"
    assert ing.buscar(FONTE, ClienteQueExplode())[1] == "cache"
    assert cliente.chamadas == 1


def test_o_slug_e_estavel_e_sobrevive_a_acento_e_barra(cache):
    """O slug é CHAVE DE CACHE. Um slug que muda transforma re-execução em re-download
    silencioso — e `RAPIDS / CUDA-X Data Science` tem barra, que quebraria o caminho."""
    assert ing._slug("RAPIDS / CUDA-X Data Science") == "rapids-cuda-x-data-science"
    assert ing._slug("NVIDIA Healthcare (ex-Clara)") == "nvidia-healthcare-ex-clara"
    assert ing._slug("Índice de Inferência") == "indice-de-inferencia"


def test_o_indice_do_cache_cobre_as_16_fontes_do_manifesto():
    """A rede de segurança do repositório: fonte no manifesto sem arquivo no cache é um clone
    limpo que volta a depender da rede — exatamente o defeito que o cache existe para fechar."""
    import json

    import yaml

    fontes = yaml.safe_load(ing.MANIFESTO.read_text(encoding="utf-8"))
    indice = json.loads(ing.INDICE_CACHE.read_text(encoding="utf-8"))
    assert {f["tecnologia"] for f in fontes} == set(indice)
    for f in fontes:
        arquivo = ing.caminho_de_cache(f)
        assert arquivo.exists(), f"{f['tecnologia']} está no manifesto e não está no cache"
        assert ing.sha256(arquivo.read_text(encoding="utf-8")) == indice[f["tecnologia"]]["sha256"]
