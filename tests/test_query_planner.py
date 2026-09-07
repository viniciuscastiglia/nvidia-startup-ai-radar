"""Testes do Query Planner — o agente que estava sem rede nenhuma até 02/09.

POR QUE ESTE ARQUIVO EXISTE, E POR QUE ELE NASCEU COM UM BUG DENTRO
--------------------------------------------------------------------
O `query_planner` era um dos dois agentes (o outro é o `extractor`) sem nenhum teste. A régua
dos agentes também não o cobre. A consequência apareceu na revisão de plano de 02/09: o filtro
`len(t) > 2` descartava **"ia" e "ai"**, e a consulta-bandeira do produto — *"startups de IA"* —
saía com `palavras_chave=[]`.

O que torna isso o pior modo de falha do sistema, e não apenas um bug: com a lista vazia, o SQL
cai em `tsq = ''`, devolve os `max_startups` primeiros em ordem alfabética, **e o briefing os
apresenta como resultado**. Não havia erro, não havia aviso, e a saída era byte a byte do mesmo
formato de um acerto. Medido: a consulta devolvia `Laura Networks`, que não casa "ia" em nenhum
dos seus três documentos.

Por isso os testes aqui se dividem em dois grupos, e o segundo é o que importa mais:
  1. o plano EXTRAI o que deveria extrair
  2. quando ele NÃO extrai nada, o sistema DIZ isso — `discrimina()` é a rede (D-081)
"""

from __future__ import annotations

import pytest

from src.agents import query_planner
from src.state import PlanoDeBusca


def planejar(consulta: str) -> PlanoDeBusca:
    return query_planner.node({"consulta": consulta})["plano"]


# ── grupo 1: o plano extrai ──────────────────────────────────────────────────

@pytest.mark.parametrize("consulta,esperado", [
    ("startups de IA", "ia"),
    ("quais empresas usam AI", "ai"),
    ("startups brasileiras de saúde usando IA", "ia"),
    ("empresas de ML no Brasil", "ml"),
])
def test_sigla_de_dois_caracteres_sobrevive(consulta, esperado):
    """A REGRESSÃO QUE MOTIVOU O ARQUIVO. Um radar de startups de IA não pode descartar "IA"."""
    assert esperado in planejar(consulta).palavras_chave, (
        f"{esperado!r} sumiu do plano de {consulta!r} — o filtro de tamanho voltou a comer sigla"
    )


@pytest.mark.parametrize("consulta,vazia", [
    ("startups de IA", "de"),
    ("startups brasileiras de saúde", "brasileiras"),
    ("quais empresas usam AI", "empresas"),
])
def test_palavra_funcional_continua_fora(consulta, vazia):
    """A correção não podia ser "aceitar tudo": quem decide o que é vazio é `VAZIAS`, e ela
    precisa continuar decidindo. Sem este teste, `len(t) > 1` viraria um tsquery poluído."""
    assert vazia not in planejar(consulta).palavras_chave


def test_setor_e_estagio_saem_da_consulta():
    p = planejar("fintechs AI-native em série A")
    assert p.setores == ["fintech"]
    assert p.estagios == ["série a"]


def test_setor_entra_tambem_como_palavra_chave():
    """O setor é sinal lexical, não só filtro — se ele só filtrasse, a busca textual perderia
    o termo mais discriminante da consulta."""
    assert "saúde" in planejar("startups de saúde").palavras_chave


# ── grupo 2: a rede contra o silêncio ────────────────────────────────────────

@pytest.mark.parametrize("consulta", [
    "startups de IA",
    "startups brasileiras de saúde usando IA",
    "fintechs AI-native em série A",
])
def test_consulta_real_discrimina(consulta):
    assert planejar(consulta).discrimina()


def test_consulta_sem_criterio_se_declara():
    """`discrimina()` é o que separa "não achei nada" de "não procurei nada" (D-081).

    Sem ele o briefing imprime uma fatia alfabética da base sob o mesmo cabeçalho de um
    resultado legítimo — e o gerente não tem como saber a diferença.
    """
    plano = PlanoDeBusca(consulta_original="me mostre")
    assert not plano.discrimina()


def test_qualquer_criterio_sozinho_ja_discrimina():
    """Um filtro só basta: a busca deixa de ser fatia arbitrária no momento em que estreita."""
    base = {"consulta_original": "x"}
    assert PlanoDeBusca(**base, setores=["saúde"]).discrimina()
    assert PlanoDeBusca(**base, estagios=["seed"]).discrimina()
    assert PlanoDeBusca(**base, palavras_chave=["ia"]).discrimina()
    assert PlanoDeBusca(**base, porte_min_time=10).discrimina()


# ─────────────────────────────────────────────────────────────────────────────
# O PLANNER PLANEJANDO — P-14, D-112
#
# O que estes testes guardam é a PROPRIEDADE DE REVERSIBILIDADE, e ela é o argumento inteiro
# pelo qual esta mudança pôde entrar a um dia do vídeo: `dores_prioritarias=[]` é a IDENTIDADE.
# É o único ramo que `avaliar_agentes.rodar` exercita, e é por isso que a régua dos agentes não
# se move. Se alguém trocar o `sorted` estável por um instável, ou tirar o `return` antecipado,
# a régua passa a se mover em silêncio — e a régua não é rodada em CI.
# ─────────────────────────────────────────────────────────────────────────────

def test_a_consulta_nomeia_a_dor_e_o_plano_a_carrega():
    from src.agents.query_planner import node

    plano = node({"consulta": "startups de fintech com problema de custo e latência"})["plano"]
    # a ORDEM é a da consulta, não a do dicionário: quem escreveu "custo e latência" pediu
    # custo primeiro, e é isso que desempata lá no `nvidia_rag`
    assert plano.dores_prioritarias == ["custo", "latencia"]


def test_consulta_sem_dor_nenhuma_produz_lista_vazia():
    """O caso que preserva a régua e o comportamento de todas as consultas anteriores."""
    from src.agents.query_planner import node

    assert node({"consulta": "fintechs brasileiras usando IA"})["plano"].dores_prioritarias == []


def test_a_estrategia_deixou_de_ser_constante():
    """O defeito que a P-14 escondia: a frase era a MESMA para toda consulta, e por isso um nó
    que a lesse não estaria lendo informação nenhuma."""
    from src.agents.query_planner import node

    com = node({"consulta": "fintechs com problema de custo"})["plano"].estrategia_analise
    sem = node({"consulta": "startups de agro"})["plano"].estrategia_analise
    assert com != sem
    assert "custo" in com and "custo" not in sem


def test_a_estrategia_escrita_bate_com_a_estrategia_EXECUTADA():
    """A frase vai impressa no briefing. Se ela citar uma dor que `nvidia_rag` não prioriza, o
    relatório afirma ao gerente algo que não aconteceu — a família de D-100."""
    from src.agents.query_planner import node

    plano = node({"consulta": "startups com problema de governança e observabilidade"})["plano"]
    for dor in plano.dores_prioritarias:
        assert dor.replace("_", " ") in plano.estrategia_analise


def _dor(nome: str):
    from src.state import DorObservada, Evidencia

    return DorObservada(dor=nome, texto=nome, evidencias=[Evidencia(
        documento_id=1, tipo_documento="site", url_fonte="https://exemplo.invalid/",
        trecho=f"trecho de {nome}")])


def test_lista_vazia_e_a_IDENTIDADE_e_e_isso_que_protege_a_regua():
    """A propriedade que faz `avaliar_agentes` reproduzir byte a byte. Não é conveniência: é o
    que permitiu esta mudança entrar sem re-medir a régua inteira."""
    from src.agents.nvidia_rag import ordenar_por_plano

    dores = [_dor("latencia"), _dor("custo"), _dor("escalabilidade")]
    assert ordenar_por_plano(dores, []) == dores


def test_a_ordenacao_e_ESTAVEL_nas_dores_que_o_planner_nao_pediu():
    """Um `sorted` instável reordenaria em silêncio o que o planner não pediu para reordenar —
    e o efeito apareceria como recomendação diferente, sem nada na saída que denunciasse."""
    from src.agents.nvidia_rag import ordenar_por_plano

    dores = [_dor("latencia"), _dor("custo"), _dor("escalabilidade"), _dor("governanca")]
    saida = [d.dor for d in ordenar_por_plano(dores, ["governanca"])]
    assert saida == ["governanca", "latencia", "custo", "escalabilidade"]


def test_dor_pedida_que_a_empresa_nao_tem_nao_inventa_dor():
    """O planner PRIORIZA, ele não cria. Uma consulta por `privacidade` numa empresa sem essa
    dor não pode fazer aparecer uma — seria afirmação sem `list[Evidencia]`."""
    from src.agents.nvidia_rag import ordenar_por_plano

    dores = [_dor("custo"), _dor("latencia")]
    saida = ordenar_por_plano(dores, ["privacidade"])
    assert [d.dor for d in saida] == ["custo", "latencia"]
