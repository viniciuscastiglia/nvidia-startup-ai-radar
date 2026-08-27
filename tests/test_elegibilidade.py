"""Filtro de elegibilidade do NVIDIA Inception — os testes que faltavam.

POR QUE ESTE ARQUIVO EXISTE
----------------------------
`elegibilidade()` é o candidato a Diferencial declarado do projeto: um sistema que RECUSA
recomendar o Inception para uma consultoria de IA, e explica por quê, demonstra regra de
negócio. Até 25/08 ele não tinha um único teste — e o code review daquele dia achou dois
defeitos que produziam saída errada em produção, os dois neste arquivo.

O PAR DE TESTES DO `"token"` É PROPOSITALMENTE UM PAR
------------------------------------------------------
`test_custo_por_token_nao_e_exclusao_por_cripto` sozinho é satisfeito apagando a regra de
cripto inteira. `test_tokenizacao_em_blockchain_continua_excluindo` é o que impede isso:
a correção precisa distinguir os dois casos, não eliminar um lado.
"""

from __future__ import annotations

import pytest

from src.agents.briefing import elegibilidade
from src.state import Afirmacao, Evidencia, PerfilStartup, StartupRef


def _perfil(*trechos: str) -> PerfilStartup:
    """Perfil mínimo cujas evidências carregam os trechos dados. `elegibilidade()` lê
    exatamente isto: `perfil.afirmacoes[*].evidencias[*].trecho`."""
    return PerfilStartup(
        startup_id=1,
        nome="Acme",
        sinais_otimizacao_tecnica=[
            Afirmacao(
                texto="Indício de profundidade técnica própria na stack de IA",
                evidencias=[
                    Evidencia(
                        documento_id=1,
                        tipo_documento="vaga",
                        url_fonte="https://exemplo.test/vaga",
                        trecho=t,
                    )
                    for t in trechos
                ],
            )
        ],
    )


def _startup(ano_fundacao: int | None = 2022) -> StartupRef:
    return StartupRef(
        startup_id=1, nome="Acme", site="https://exemplo.test", ano_fundacao=ano_fundacao
    )


def test_custo_por_token_nao_e_exclusao_por_cripto():
    """REGRESSÃO do code review de 25/08 — `briefing.py:25`.

    `"token"` estava na lista de exclusão de cripto e era casado como SUBSTRING. Como
    `SINAIS_TECNICOS` do Extractor inclui `"tokens por segundo"`, uma frase sobre custo de
    inferência virava evidência técnica e disparava "exclusão por 'cripto'".

    O trecho abaixo é o de `tests/test_grafo.py:102` — o gatilho já estava DENTRO do
    repositório, e nenhuma asserção olhava para `elegibilidade`.
    """
    perfil = _perfil(
        "Buscamos engenheiro para otimizar inferência de LLM com quantização e self-hosted "
        "em GPU, reduzindo latência e custo por token em produção."
    )
    resultado = elegibilidade(_startup(), perfil)
    assert resultado.elegivel, (
        f"startup de infraestrutura de IA reprovada ao Inception: {resultado.motivos_exclusao}"
    )


def test_tokenizacao_em_blockchain_continua_excluindo():
    """A contraprova do teste acima: a regra de cripto não pode ser apagada, só afiada.

    `contexto/03` §2 lista "empresas ligadas a criptomoeda" como exclusão explícita do
    programa. Se este teste cair, a correção resolveu o falso positivo criando um falso
    negativo — que é pior, porque é silencioso.
    """
    perfil = _perfil("Nossa plataforma faz tokenização de ativos reais em blockchain.")
    resultado = elegibilidade(_startup(), perfil)
    assert not resultado.elegivel, "empresa de cripto passou pelo filtro do Inception"
    assert any("cripto" in m for m in resultado.motivos_exclusao), (
        f"excluiu, mas pelo rótulo errado: {resultado.motivos_exclusao}"
    )


def test_consultoria_continua_excluindo():
    """O caso que `contexto/03` §2 pede por escrito, e o Diferencial declarado do projeto."""
    perfil = _perfil("Somos uma consultoria de dados e IA para grandes empresas.")
    resultado = elegibilidade(_startup(), perfil)
    assert not resultado.elegivel
    assert any("consultoria" in m for m in resultado.motivos_exclusao)


def test_motivo_de_exclusao_aponta_para_a_evidencia_que_o_sustenta():
    """ACHADO Nº 2 do code review de 25/08 — `briefing.py:36`.

    `Elegibilidade.evidencias` nascia `[]` e nunca era preenchida, enquanto os motivos
    afirmam "o termo X aparece nos documentos" e o briefing imprime tudo sob o rodapé
    "Toda conclusão acima aponta para o documento que a sustenta". Era a ÚNICA conclusão do
    sistema sem `list[Evidencia]` — contra a invariante do repositório.
    """
    trecho = "Nossa plataforma faz tokenização de ativos reais em blockchain."
    resultado = elegibilidade(_startup(), _perfil(trecho))
    assert resultado.motivos_exclusao
    assert resultado.evidencias, "motivo de exclusão afirmado sem a evidência que o sustenta"
    assert any(e.trecho == trecho for e in resultado.evidencias), (
        "a evidência anexada não é o trecho onde o termo excludente aparece"
    )
    for e in resultado.evidencias:
        assert e.url_fonte.startswith("http")
        assert e.documento_id > 0


def test_exclusao_por_idade_usa_o_campo_estruturado():
    """Sem fixture: `ano_fundacao` é campo estruturado e determinístico. O plano da sessão 06
    registra por que coletar 3 páginas reais para exercitar um `if` aritmético não compra
    medição nenhuma."""
    velha = elegibilidade(_startup(ano_fundacao=2010), _perfil("texto sem termo excludente"))
    assert not velha.elegivel
    assert any("idade" in m for m in velha.motivos_exclusao)

    nova = elegibilidade(_startup(ano_fundacao=2022), _perfil("texto sem termo excludente"))
    assert nova.elegivel


def test_ausencia_de_ano_de_fundacao_nao_exclui_vira_pendencia():
    """A disciplina que o docstring do módulo chama de "a que vale notar": "a base não prova"
    é diferente de "a base prova que não". Só o segundo exclui."""
    resultado = elegibilidade(_startup(ano_fundacao=None), _perfil("texto sem termo excludente"))
    assert resultado.elegivel
    assert any("ano de fundação" in p for p in resultado.requisitos_nao_verificados)


def test_plural_continua_excluindo():
    """REGRESSÃO do code review de 25/08, achado nº 1.

    A primeira versão de D-048 ancorou a fronteira nos DOIS lados (`\\btermo\\b`), o que
    silenciosamente desligou o plural: `\\bconsultoria\\b` não casa "consultorias". Plural é a
    forma comum em texto institucional, então uma empresa que se descreve como "consultorias de
    IA" passava pelo filtro do Inception — o falso positivo de D-048 tinha sido trocado por um
    falso negativo, que é pior porque não aparece em lugar nenhum.
    """
    for frase in ("Prestamos consultorias de dados e IA para grandes empresas.",
                  "Somos revendas autorizadas de hardware para datacenter.",
                  "Operamos com criptomoedas desde 2021."):
        resultado = elegibilidade(_startup(), _perfil(frase))
        assert not resultado.elegivel, f"passou pelo filtro no plural: {frase!r}"


def test_fronteira_no_inicio_ainda_impede_o_falso_positivo_de_substring():
    """A contraparte: soltar a âncora final não pode ressuscitar o defeito que D-048 pagou.

    `'ipo concluído'` (exclusão por capital aberto) não pode casar dentro de "equipo".
    """
    resultado = elegibilidade(_startup(), _perfil("O equipo concluído entrega o resultado."))
    assert resultado.elegivel, resultado.motivos_exclusao


def test_briefing_imprime_a_evidencia_da_exclusao():
    """Achado nº 5 do code review: D-049 passou a GUARDAR a evidência, e o briefing não a
    imprimia — então o rodapé "toda conclusão aponta para o documento que a sustenta"
    continuava falso exatamente na conclusão que a decisão foi escrita para consertar."""
    from src.agents.briefing import _secao
    from src.state import AnaliseStartup

    trecho = "Nossa plataforma faz tokenização de ativos reais em blockchain."
    analise = AnaliseStartup(
        startup_id=1, nome="Acme",
        elegibilidade=elegibilidade(_startup(), _perfil(trecho)),
    )
    texto = "\n".join(_secao(analise))
    assert "NÃO ELEGÍVEL" in texto
    assert "https://exemplo.test/vaga" in texto, "motivo de exclusão impresso sem a fonte"
    assert trecho[:60] in texto, "motivo de exclusão impresso sem o trecho literal"
