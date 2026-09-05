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
    # ESTA LINHA É O QUE FAZ O TESTE VALER DEPOIS DE 24/08. `analisar_startup` afunila qualquer
    # falha de nó do subgrafo em `AnaliseStartup(erros=[...])` — por desenho, D-024 —, e desde
    # que `nvidia_rag` passou a chamar o pipeline real, o nó faz I/O de banco e de API. Sem
    # assertar `erros`, um RAG COMPLETAMENTE QUEBRADO produzia `len(analises) == 1` e o teste
    # passava verde. Achado do code review da revisão da sessão 03.
    for analise in resultado["analises"]:
        assert not analise.erros, f"{analise.nome}: o subgrafo registrou {analise.erros}"


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


def test_justificativa_negocio_fala_da_tecnologia_recomendada(resultado):
    """O teste acima só checa verdade booleana — um fallback CONSTANTE o satisfaz por construção.

    Este aqui é o que impede um campo obrigatório do TAPI de virar texto de enfeite: se duas
    recomendações de TECNOLOGIAS diferentes trazem a mesma justificativa de negócio, o campo não
    está falando da tecnologia, está preenchendo espaço. Ver a revisão da sessão 03, §4 — foi
    exatamente uma falha detectável que um fallback tornou indetectável.
    """
    for analise in resultado["analises"]:
        por_texto: dict[str, set[str]] = {}
        for rec in analise.recomendacoes:
            por_texto.setdefault(rec.justificativa_negocio, set()).update(rec.tecnologias)
        for texto, tecnologias in por_texto.items():
            assert len(tecnologias) == 1, (
                f"{analise.nome}: a MESMA justificativa_negocio serve a {sorted(tecnologias)} — "
                f"{texto[:80]!r}"
            )


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


# ─────────────────────────────────────────────────────────────────────────────
# D-063 — `dores_enderecadas` e o lastro. ZERO chamada de API: o estado é montado
# à mão, porque o único caminho do harness que exercita `recommendation.node` é
# `--motor ponta-a-ponta`, que custa API e hoje nem roda (reranker 404).
# Achado nº 9 do code review de 27/08: a mudança tinha entrado em produção sem rede.
# ─────────────────────────────────────────────────────────────────────────────


def _perfil_com_duas_dores():
    from src.state import DorObservada, Evidencia, PerfilStartup
    ev = lambda t, d: Evidencia(documento_id=d, tipo_documento="site",
                                url_fonte=f"https://exemplo.test/{d}", trecho=t)
    return PerfilStartup(startup_id=1, nome="Acme", dores_observadas=[
        DorObservada(dor="custo", texto="c", validada=True,
                     evidencias=[ev("o custo de nuvem dobrou no último ano", 1)]),
        DorObservada(dor="observabilidade", texto="o", validada=True,
                     evidencias=[ev("falta monitoramento do modelo em produção", 2)]),
    ])


def _diagnostico_sweet_spot():
    from src.state import Diagnostico
    return Diagnostico(classe="AI-native", maturidade_stack="baixa", quadrante="sweet-spot",
                       confianca="alta", justificativa="j")


def _recomendar(dor_origem):
    from src.agents import recommendation
    from src.state import CitacaoRAG
    citacao = CitacaoRAG(tecnologia="NVIDIA NIM", trecho="t",
                         url_fonte="https://build.nvidia.com/nim", dor_origem=dor_origem)
    return recommendation.node({"perfil": _perfil_com_duas_dores(),
                                "diagnostico": _diagnostico_sweet_spot(),
                                "citacoes_rag": [citacao]})["recomendacoes"]


def test_dores_enderecadas_e_so_a_dor_que_puxou_a_citacao():
    """O filtro antigo (`any(c.tecnologia == citacao.tecnologia for c in citacoes)`) era SEMPRE
    verdadeiro, então toda recomendação declarava todas as dores validadas."""
    rec = _recomendar("observabilidade")[0]
    assert rec.dores_enderecadas == ["observabilidade"], rec.dores_enderecadas


def test_a_evidencia_citada_sustenta_a_dor_declarada():
    """A REDE DO ACHADO Nº 1 DO REVIEW. A primeira versão de D-063 estreitou a declaração e
    deixou o lastro largo: a recomendação declarava `observabilidade` e citava trechos sobre
    custo, sob o rodapé que promete que toda conclusão aponta para o documento que a sustenta."""
    rec = _recomendar("observabilidade")[0]
    assert rec.evidencias, "recomendação sem lastro"
    assert all("monitoramento" in e.trecho for e in rec.evidencias), \
        [e.trecho for e in rec.evidencias]


def test_sem_dor_de_origem_a_recomendacao_nao_some_e_o_briefing_nao_pendura_o_rotulo():
    """`dor_origem=None` é o caminho da interface. D-063 não pode fazer a recomendação sumir
    (era a razão de a dívida não ter sido paga antes), e o briefing não pode imprimir
    `dores      : ` com nada depois — achado nº 10 do review."""
    from src.agents import briefing
    from src.state import AnaliseStartup
    recs = _recomendar(None)
    assert recs, "a recomendação sumiu quando a citação não veio de uma dor"
    assert recs[0].dores_enderecadas == []
    analise = AnaliseStartup(startup_id=1, nome="Acme", perfil=_perfil_com_duas_dores(),
                             diagnostico=_diagnostico_sweet_spot(), recomendacoes=recs)
    linha = next(l for l in briefing._secao(analise) if "dores" in l)
    assert not linha.rstrip().endswith(":"), f"rótulo pendurado: {linha!r}"


def test_o_diagnostico_carrega_o_motivo_da_confianca_em_producao():
    """Regra 5 de contexto/02 §6. Achado nº 5 do review: `motivo_confianca` só era preenchido
    no braço da flag, que é `False` por default — o campo e a linha do briefing eram código
    morto na configuração que roda, e D-059 afirmava o contrário."""
    from src.agents import evidence_validator
    assert evidence_validator.CONFIANCA_DA_EVIDENCIA_DO_DIAGNOSTICO is False, \
        "este teste mede o braço de PRODUÇÃO"
    estado = {"perfil": _perfil_com_duas_dores(), "diagnostico": _diagnostico_sweet_spot()}
    diagnostico = evidence_validator.node(estado)["diagnostico"]
    assert diagnostico.motivo_confianca, "confiança sem motivo no braço de produção"


# ─────────────────────────────────────────────────────────────────────────────
# D-099, D-100 e D-101 — os três consertos de 04/09. Todos sem API.
# ─────────────────────────────────────────────────────────────────────────────


def _alcanca(origem: str, destino: str) -> bool:
    """`destino` é alcançável a partir de `origem` no subgrafo COMPILADO?

    BUSCA EM LARGURA, E NÃO UMA CAMINHADA PELA CADEIA (D-103). A primeira versão montava
    `{e.source: e.target}` e andava com um `while` sem teto: um dict COLAPSA arestas paralelas
    (fica só a última), então a primeira aresta condicional acrescentada ao subgrafo faria o
    teste afirmar um ramo arbitrário, ou estourar `ValueError`/`KeyError` — e um ciclo faria o
    `while` pendurar a suíte em vez de falhar. O próprio comentário de `construir_subgrafo`
    prevê a condicional ("a mudança vira uma condicional"), então o teste não pode assumir linha
    reta. Lê do compilado, e não da lista de `add_edge`: é o que de fato roda.
    """
    saidas: dict[str, list[str]] = {}
    for e in SUBGRAFO.get_graph().edges:
        saidas.setdefault(e.source, []).append(e.target)
    vistos, fila = {origem}, [origem]
    while fila:
        no = fila.pop()
        for prox in saidas.get(no, []):
            if prox == destino:
                return True
            if prox not in vistos:
                vistos.add(prox)
                fila.append(prox)
    return False


def test_elegibilidade_roda_antes_do_recommendation():
    """D-099. O motor de recomendação não pode decidir sem saber se a empresa foi recusada.

    Este é o teste ESTRUTURAL, e ele existe separado do comportamental abaixo porque a ordem é
    o que torna a informação disponível: com `elegibilidade` no fim, `recommendation` lê `None`
    e o rótulo some em silêncio — nenhum teste de comportamento pegaria isso, porque o estado
    montado à mão no pytest não tem a ordem do grafo.
    """
    assert _alcanca("elegibilidade", "recommendation"), "elegibilidade não precede recommendation"
    assert not _alcanca("recommendation", "elegibilidade"), "a ordem antiga voltou"


def _elegibilidade(elegivel: bool):
    from src.state import Elegibilidade
    return Elegibilidade(
        elegivel=elegivel,
        motivos_exclusao=[] if elegivel else ["exclusão por 'cripto': o termo 'stablecoin' "
                                              "aparece nos documentos falando da própria empresa"],
        requisitos_nao_verificados=[],
    )


def test_recusada_pelo_inception_mantem_recomendacao_rotulada_e_rebaixada():
    """D-099. Suprimir seria o Recommendation DELETANDO, contra D-010.

    O caso real que decidiu isto: a JetBov é a única `AI-native` e o único `sweet-spot` da base
    de 30, e é recusada por idade. Suprimir apagaria da tela o melhor prospect do sistema.
    """
    from src.agents import recommendation
    from src.state import CitacaoRAG
    citacao = CitacaoRAG(tecnologia="NVIDIA NIM", trecho="t",
                         url_fonte="https://build.nvidia.com/nim", dor_origem="custo")
    estado = {"perfil": _perfil_com_duas_dores(), "diagnostico": _diagnostico_sweet_spot(),
              "citacoes_rag": [citacao], "elegibilidade": _elegibilidade(False)}
    from src.agents import briefing
    from src.state import AnaliseStartup
    recs = recommendation.node(estado)["recomendacoes"]
    assert recs, "a recomendação sumiu quando a empresa foi recusada"

    # O RÓTULO É DO BRIEFING, LENDO `a.elegibilidade` (D-103) — não um campo em `Recomendacao`.
    # E a `prioridade` NÃO cai por causa da recusa: medido em 04/09, esse rebaixamento achatava
    # 15 das 30 e empatava a JetBov (único `sweet-spot`) com a SunnyHUB (energia solar).
    assert recs[0].prioridade == "alta", recs[0].prioridade
    analise = AnaliseStartup(startup_id=1, nome="Acme", perfil=_perfil_com_duas_dores(),
                             diagnostico=_diagnostico_sweet_spot(), recomendacoes=recs,
                             elegibilidade=_elegibilidade(False))
    banner = [l for l in briefing._secao(analise) if "FORA DO INCEPTION" in l]
    assert banner, "recusada sem o banner comercial"
    # O motivo aparece UMA vez, no bloco de elegibilidade, com a evidência — não duas.
    motivos = [l for l in briefing._secao(analise) if "cripto" in l]
    assert len(motivos) == 1, motivos

    # E o contrário, para a asserção não passar por construção:
    analise.elegibilidade = _elegibilidade(True)
    assert not [l for l in briefing._secao(analise) if "FORA DO INCEPTION" in l]


def test_non_ai_sem_sinal_verificado_nao_e_cortado_do_funil():
    """D-101. `pontos == 0` é ausência de sinal, e ausência de sinal não é sinal negativo.

    O par com `test_non_ai_nao_recebe_recomendacao` é o ponto: o `non-AI` CONSTATADO continua
    fora do funil — a rubrica autoriza esse corte. O que mudou é só o não constatado.
    """
    assert derivar_quadrante("non-AI", "baixa", sinal_verificado=False) == "prospect-de-evolucao"
    assert derivar_quadrante("non-AI", "alta", sinal_verificado=False) == "prospect-de-evolucao"
    assert derivar_quadrante("non-AI", "baixa", sinal_verificado=True) == "fora-do-funil"


def test_classifier_marca_sinal_nao_verificado_quando_nenhum_detector_dispara():
    """D-101, do lado do produtor: quem emite o rótulo é quem sabe se ele foi constatado."""
    from src.agents import classifier
    from src.state import PerfilStartup
    perfil = PerfilStartup(startup_id=1, nome="Muda")   # zero detector, zero dor
    diag = classifier.node({"perfil": perfil, "startup": _startup_de_teste()})["diagnostico"]
    assert diag.classe == "non-AI"
    assert diag.sinal_verificado is False
    assert diag.quadrante != "fora-do-funil", diag.quadrante


def test_briefing_nao_inventa_causa_para_zero_recomendacoes():
    """D-100. A frase fixa "sem evidência validada" era impressa para TODA lista vazia.

    Medido em 04/09: Conta Simples, Core AI e Iniciador têm 3, 5 e 7 dores VALIDADAS e recebiam
    essa frase. A causa real era o corte de funil. Um relatório que afirma a causa errada é pior
    que um que não afirma nenhuma, porque o gerente age sobre ela.
    """
    from src.agents import briefing
    from src.state import AnaliseStartup, Diagnostico
    fora = Diagnostico(classe="non-AI", maturidade_stack="baixa", quadrante="fora-do-funil",
                       confianca="baixa", justificativa="j")
    analise = AnaliseStartup(startup_id=1, nome="Acme", perfil=_perfil_com_duas_dores(),
                             diagnostico=fora, recomendacoes=[],
                             motivo_sem_recomendacao="fora do funil por `contexto/02` §4")
    linha = next(l for l in briefing._secao(analise) if l.strip().startswith("nenhuma —"))
    assert "fora do funil" in linha, linha
    assert "sem evidência validada" not in linha, linha


def test_resumir_nunca_corta_no_meio_da_palavra_nem_deixa_quebra_de_linha():
    """D-100. `[:150]` cru produzia "...NVIDIA NIM™ microse" em dois dos SETE campos do TAPI."""
    from src.agents.briefing import _resumir
    assert _resumir("NVIDIA NIM microservices em produção", 18) == "NVIDIA NIM…"
    assert _resumir("curto", 50) == "curto"
    assert "\n" not in _resumir("uma linha\noutra linha", 100)
    # Palavra única maior que o limite: corta, mas ANUNCIA o corte.
    longo = _resumir("a" * 80, 20)
    assert len(longo) <= 20 and longo.endswith("…")
    # A borda (D-103): `limite - 1` virava fatia NEGATIVA e devolvia quase o texto inteiro.
    assert _resumir("texto longo", 0) == "…"
    assert _resumir("", 0) == ""


# ─────────────────────────────────────────────────────────────────────────────
# D-104 — `justificativa_negocio` por (tecnologia, dor). P-22.
# ─────────────────────────────────────────────────────────────────────────────


def test_justificativa_negocio_fala_da_dor_declarada():
    """IRMÃO de `test_justificativa_negocio_fala_da_tecnologia_recomendada`, pelo mesmo motivo
    e no campo ao lado (D-063 → D-104).

    Aquele impede o campo de virar texto que não fala da TECNOLOGIA; este impede que ele fale
    de uma DOR diferente da que a linha `dores:` declara duas linhas acima. Medido na tela em
    05/09, com o rerank ligado: `NVIDIA NIM · dores: latencia · "Reduz o custo por token…"` e
    `NVIDIA NeMo · dores: custo · "Sem processo de avaliação…"` — 13 das 15 recomendações do
    briefing traziam texto de outra dor ou o fallback formulaico.

    A rede é o CONTRAPOSITIVO, e não a coincidência: nenhum texto curado para um par pode sair
    sob uma dor que não é a dele. Verificar "o texto casa com a dor" exigiria julgar prosa;
    verificar "o texto de OUTRA dor não aparece aqui" é mecânico e pega a regressão de índice,
    que é o defeito real — `NEGOCIO` indexado só por tecnologia.
    """
    from src.agents.recommendation import NEGOCIO, justificativa_negocio
    from src.state import CitacaoRAG, Dor
    from typing import get_args

    tecnologias = {t for t, _ in NEGOCIO}
    for tecnologia in sorted(tecnologias):
        proprias = {d for t, d in NEGOCIO if t == tecnologia}
        for dor in get_args(Dor):
            citacao = CitacaoRAG(tecnologia=tecnologia, trecho="t",
                                 url_fonte="https://exemplo.test/x", dor_origem=dor)
            texto = justificativa_negocio(citacao, "Acme")
            if dor in proprias:
                assert texto == NEGOCIO[(tecnologia, dor)], f"{tecnologia}/{dor}"
            else:
                assert texto not in NEGOCIO.values(), (
                    f"{tecnologia} sob a dor `{dor}` recebeu texto curado para outra dor: "
                    f"{texto[:70]!r}")


def test_justificativa_negocio_cabe_no_briefing():
    """O tamanho é restrição MEDIDA, não estilo — e a primeira redação de D-104 a violou.

    `briefing` corta em 150 com `…` (D-100). Sete das oito frases por dor estouravam quando
    formatadas com `RAPIDS / CUDA-X Data Science`, o nome mais longo da base: teriam chegado ao
    gerente cortadas no meio, que é exatamente o defeito que D-100 tinha acabado de tirar da
    tela. O teto entra aqui para que a próxima frase curada nasça sabendo dele.
    """
    from src.agents.recommendation import NEGOCIO, NEGOCIO_POR_DOR
    import yaml
    from pathlib import Path

    fontes = yaml.safe_load(Path("data/nvidia/fontes.yaml").read_text(encoding="utf-8"))
    nomes = [f["tecnologia"] for f in (fontes["fontes"] if isinstance(fontes, dict) else fontes)]
    mais_longo = max(nomes, key=len)
    for dor, modelo in NEGOCIO_POR_DOR.items():
        texto = modelo.format(tecnologia=mais_longo)
        assert len(texto) <= 150, f"`{dor}` estoura o briefing com {len(texto)}: {texto!r}"
    for chave, texto in NEGOCIO.items():
        assert len(texto) <= 150, f"{chave} estoura o briefing com {len(texto)}"


def test_toda_dor_tem_texto_de_negocio():
    """As oito dores de `state.Dor` são o domínio do campo; uma sem frase cai no fallback
    formulaico, que é a dívida que D-104 existe para pagar."""
    from src.agents.recommendation import NEGOCIO_POR_DOR
    from src.state import Dor
    from typing import get_args

    assert set(NEGOCIO_POR_DOR) == set(get_args(Dor)), \
        f"faltam: {set(get_args(Dor)) - set(NEGOCIO_POR_DOR)}"


# ─────────────────────────────────────────────────────────────────────────────
# D-106 — `PROFUNDOS` alternativo, sob protocolo anti-contaminação.
# ─────────────────────────────────────────────────────────────────────────────


def test_profundos_candidato_bate_com_o_yaml():
    """O CARIMBO DE DATA SÓ VALE SE OS DOIS LADOS NÃO PUDEREM DIVERGIR.

    `data/avaliacao/profundos-candidato.yaml` guarda a ORIGEM de cada termo — documento e
    trecho literal —, e foi commitado antes de qualquer medição. A constante em `classifier.py`
    é o que roda. Se as duas divergirem, o YAML vira decoração e a lista volta a poder ser
    ajustada olhando o resultado, que é exatamente o erro que D-091 custou uma sessão.
    """
    import yaml
    from pathlib import Path
    from src.agents.classifier import PROFUNDOS_CANDIDATO

    dados = yaml.safe_load(
        Path("data/avaliacao/profundos-candidato.yaml").read_text(encoding="utf-8"))
    do_yaml = [t["termo"] for t in dados["candidato"]]
    assert set(do_yaml) == set(PROFUNDOS_CANDIDATO), (
        f"só no yaml: {sorted(set(do_yaml) - set(PROFUNDOS_CANDIDATO))} · "
        f"só no código: {sorted(set(PROFUNDOS_CANDIDATO) - set(do_yaml))}")
    sem_origem = [t["termo"] for t in dados["candidato"] if not t.get("origem")]
    assert not sem_origem, f"termo sem origem — foi inventado olhando o resultado? {sem_origem}"


def test_a_flag_do_candidato_alcanca_os_dois_eixos():
    """A GUARDA DE D-060, E ELA É A RAZÃO DE `marcadores_de_profundidade()` EXISTIR.

    D-060 deixou a lista compartilhada de propósito: mexer nela para consertar `classe` move a
    `maturidade_stack` no mesmo movimento, o que torna a calibração visível. Um candidato que
    alcançasse só o eixo 1 faria o critério de D-106 — *"sem derrubar maturidade_stack abaixo
    de 6/7"* — passar POR CONSTRUÇÃO, que é a armadilha do instrumento que parece medido.

    A PRIMEIRA VERSÃO DESTE TESTE NÃO CHAMAVA `profundidade_tecnica`, e por isso ficou verde
    sobre um `TypeError` — o acessor colidia com a variável local `marcadores`. Era o mesmo
    defeito que ele existe para impedir: uma checagem que parece verificação e não executa o
    caminho. Ele agora EXERCITA os dois eixos com um documento que só o candidato casa.
    """
    from src.agents import classifier
    from src.state import Afirmacao, DocumentoRef, Evidencia, PerfilStartup, StartupRef

    # `guardrails` e `avaliação` estão SÓ no candidato; nenhum termo de produção aparece aqui.
    frase = ("A equipe mantém guardrails proprietários e um processo de avaliação contínua "
             "com fine-tuning sobre dado de domínio, sem depender de terceiro.")
    doc = DocumentoRef(documento_id=1, tipo="site", titulo="t",
                       url_fonte="https://exemplo.test/x", conteudo_texto=frase)
    perfil = PerfilStartup(
        startup_id=1, nome="Acme",
        sinais_otimizacao_tecnica=[Afirmacao(texto=frase,
                                             evidencias=[Evidencia.de_documento(doc, frase)])])
    estado = {"perfil": perfil, "startup": StartupRef(startup_id=1, nome="Acme",
                                                      documentos=[doc])}

    original_lista = classifier.USAR_PROFUNDOS_CANDIDATO
    original_rubrica = classifier.RUBRICA_EM_DEGRAUS
    try:
        assert classifier.marcadores_de_profundidade() is classifier.PROFUNDOS
        classifier.RUBRICA_EM_DEGRAUS = True

        # EIXO 1 (`profundidade_tecnica`, documentos inteiros) e EIXO 2 (`maturidade_stack`,
        # trechos de evidência) — os dois têm de se mexer, e nenhum se mexe hoje.
        assert classifier.profundidade_tecnica([doc])[0] == 0
        assert classifier.node(estado)["diagnostico"].maturidade_stack == "baixa"

        classifier.USAR_PROFUNDOS_CANDIDATO = True
        assert classifier.marcadores_de_profundidade() is classifier.PROFUNDOS_CANDIDATO
        assert classifier.profundidade_tecnica([doc])[0] >= 3, "o eixo 1 não leu o candidato"
        assert classifier.node(estado)["diagnostico"].maturidade_stack == "alta", \
            "o eixo 2 não leu o candidato — a calibração ficou silenciosa"
    finally:
        classifier.USAR_PROFUNDOS_CANDIDATO = original_lista
        classifier.RUBRICA_EM_DEGRAUS = original_rubrica
