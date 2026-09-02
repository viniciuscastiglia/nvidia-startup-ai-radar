"""A RÉGUA DOS AGENTES — o que o `avaliar_rag.py` é para o RAG, este arquivo é para o pipeline de
análise e para o motor de recomendação.

POR QUE ELE EXISTE, E POR QUE VEM ANTES DO EXTRACTOR COM LLM
--------------------------------------------------------------
Até 25/08 a base tinha 3 startups e as 3 eram `perfil_alvo: AI-native`. Um classificador que
devolvesse `"AI-native"` incondicionalmente passava em 3 de 3 — não havia número capaz de
distinguir um Extractor com LLM do casador de substring que está lá desde a sessão 01. O RAG
melhorou de verdade porque teve régua desde o primeiro dia; os agentes não tinham nenhuma, e
escrever o agente antes da régua é o erro que a revisão da sessão 03 achou em dois lugares.

O GABARITO MORA NA FIXTURE (D-051)
------------------------------------
Bloco `gabarito:` em `data/seed/*.yaml`, ao lado do `perfil_alvo` que já existia. `scripts/seed.py`
já garante que esse material NÃO vai para o banco — se fosse, o Classifier enxergaria a resposta.
Na prática o seed é, de graça, um conjunto rotulado de avaliação.

CADA CAMPO DO GABARITO ACEITA TRÊS FORMAS, E A TERCEIRA É A QUE FALTAVA
------------------------------------------------------------------------
    classe: AI-native              valor   -> DECIDE. entra em acertos/decididos
    classe: [AI-native, AI-enabled] lista  -> AMBÍGUO. bater um deles não é acerto limpo
    maturidade_stack: null         null    -> NÃO MEDIDO. sai do denominador

"Medido, não decide" é resultado válido e tem coluna própria. É a mesma disciplina que
`sem_resposta` tem no gabarito do RAG: um sistema que só é avaliado onde a resposta é óbvia
aprende a parecer certo, não a estar certo.

AS MÉTRICAS, E POR QUE A MANCHETE É PRECISÃO DE DOR
-----------------------------------------------------
O modo de falha do stub NÃO é deixar de achar dor — é achar demais. A HIPÓTESE que motivou
`discriminacao` era mais forte: a dívida nº 6 da sessão 04 afirmava que ele emite o MESMO conjunto
para toda startup, e daí que consulta genérica recupera chunk genérico.

**Essa metade da hipótese foi REFUTADA por esta régua no primeiro dia** (D-052): sobre 8 fixtures
diversas o casador produz 8 conjuntos distintos — `discriminacao` 8/8. A afirmação era verdadeira
sobre a base que existia (3 startups, todas de saúde) e generalizava um artefato da amostra. A
métrica fica porque é ela que torna isso verificável, e porque a linha trivial pontua 1/8 nela.

O que sobreviveu da dívida nº 6 é o outro lado, e é o que a manchete mede: precisão de 49%. São as
dores ERRADAS que poluem a consulta, não a falta de variação. Recall sozinho premiaria emitir
tudo; precisão pune.
Por isso a manchete é precisão, e por isso existe `discriminacao`: quantos conjuntos DISTINTOS
de dores o extrator produz para as 8 fixtures. Um extrator que devolve sempre a mesma coisa
pontua 1/8 por construção, e nenhuma métrica de acerto médio revela isso.

`dores_ambiguas` sai do cálculo dos dois lados: emitir uma delas não conta a favor nem contra.
`dores_proibidas` vira FALHA NOMEADA, com a startup e o termo — porque "errou 0,3" não é
acionável e "emitiu `dependencia_fornecedor` para a Maritaca por causa do ChatGPT no título da
matéria" é.

`--motor` É ABLAÇÃO, NÃO OPÇÃO (mesma leitura de D-044)
---------------------------------------------------------
`extrator -> classificador -> validador -> ponta-a-ponta` é a ordem em que o subgrafo executa.
O default PARA ANTES do `nvidia_rag`, e isso é decisão de custo, não descuido: medir o Extractor
não exige pagar um embedding e um rerank por dor observada. O braço que gasta API se pede pelo
nome, do mesmo jeito que `--truncar-pool` no harness do RAG.

USO
---
    python scripts/avaliar_agentes.py --validar    # coerência + evidência literal + teto do casador. ZERO API
    python scripts/avaliar_agentes.py --baseline   # a linha trivial: sempre AI-native, todas as dores
    python scripts/avaliar_agentes.py              # extrator + classificador + validador
    python scripts/avaliar_agentes.py --motor ponta-a-ponta   # inclui nvidia_rag: CUSTA API
    python scripts/avaliar_agentes.py --falhas     # detalha cada divergência
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents import briefing, classifier, evidence_validator, extractor  # noqa: E402
from src.state import (  # noqa: E402
    Afirmacao,
    DocumentoRef,
    Dor,
    PlanoDeBusca,
    StartupRef,
    derivar_quadrante,
)

DIR_SEED = Path(__file__).resolve().parent.parent / "data" / "seed"

DORES_VALIDAS = set(Dor.__args__)
CLASSES = {"AI-native", "AI-enabled", "non-AI"}
MATURIDADES = {"baixa", "media", "alta"}
CONFIANCAS = {"baixa", "media", "alta"}
ROTULOS_EXCLUSAO = set(briefing.EXCLUSOES) | {"idade"}

CAMPOS = {                       # campo do gabarito -> (onde ler, domínio válido)
    "classe": ("diagnostico.classe", CLASSES),
    "maturidade_stack": ("diagnostico.maturidade_stack", MATURIDADES),
    "confianca": ("diagnostico.confianca", CONFIANCAS),
    "elegivel": ("elegibilidade.elegivel", {True, False}),
    "motivo_exclusao": ("elegibilidade.motivo", ROTULOS_EXCLUSAO),
}


# ─────────────────────────────────────────────────────────────────────────────
# Carga — o banco NÃO é tocado: as fixtures são a fonte, e assim o harness roda
# sem Postgres e é reprodutível por quem for avaliar.
# ─────────────────────────────────────────────────────────────────────────────


def carregar() -> list[dict]:
    fixtures = []
    for caminho in sorted(DIR_SEED.glob("*.yaml")):
        dados = yaml.safe_load(caminho.read_text(encoding="utf-8"))
        dados["_arquivo"] = caminho.name
        fixtures.append(dados)
    return fixtures


def como_startup(f: dict, indice: int = 0) -> StartupRef:
    """`documento_id` é o índice + 1: estável dentro de um run e suficiente para a
    verificação de evidência literal, que é o que este harness precisa rastrear.

    `startup_id` vem da POSIÇÃO na lista ordenada, não de `hash(nome)`: o hash de `str` em
    Python varia entre processos (`PYTHONHASHSEED`), e um harness cujo identificador muda a
    cada execução não é reprodutível — que é o requisito nº 1 de uma régua.
    """
    docs = [
        DocumentoRef(
            documento_id=i,
            tipo=d["tipo"],
            titulo=d["titulo"],
            url_fonte=d["url_fonte"],
            data_publicacao=d.get("data_publicacao"),
            conteudo_texto=d["conteudo_texto"],
        )
        for i, d in enumerate(f.get("documentos") or [], 1)
    ]
    return StartupRef(
        startup_id=indice + 1,
        nome=f["nome"],
        site=f.get("site"),
        setor=f.get("setor"),
        estagio=f.get("estagio"),
        localizacao=f.get("localizacao"),
        ano_fundacao=f.get("ano_fundacao"),
        tamanho_time=f.get("tamanho_time"),
        descricao_curta=f.get("descricao_curta"),
        documentos=docs,
    )


# ─────────────────────────────────────────────────────────────────────────────
# --validar: coerência do gabarito, evidência literal e teto de recall do casador.
# Nada aqui mede desempenho e tudo aqui deveria rodar primeiro. Zero chamada de API.
# ─────────────────────────────────────────────────────────────────────────────


def _aceitaveis(valor):
    """None -> não medido (None). valor -> {valor}. lista -> conjunto (ambíguo)."""
    if valor is None:
        return None
    return set(valor) if isinstance(valor, list) else {valor}


def validar(fixtures: list[dict]) -> list[str]:
    problemas: list[str] = []
    for f in fixtures:
        arq, g = f["_arquivo"], f.get("gabarito")
        if not g:
            problemas.append(f"{arq}: sem bloco `gabarito:` — a fixture não é mensurável")
            continue

        for campo, (_, dominio) in CAMPOS.items():
            aceitos = _aceitaveis(g.get(campo))
            if aceitos and (fora := aceitos - dominio):
                problemas.append(f"{arq}: `{campo}` fora do domínio: {fora}")

        conjuntos = {c: set(g.get(c) or []) for c in
                     ("dores_esperadas", "dores_proibidas", "dores_ambiguas")}
        for nome, conj in conjuntos.items():
            if fora := conj - DORES_VALIDAS:
                problemas.append(f"{arq}: `{nome}` tem dor inexistente: {fora}")
        # As três listas particionam as oito dores. Sobreposição torna o resultado
        # indefinido — a mesma dor não pode contar a favor e contra.
        for a, b in [("dores_esperadas", "dores_proibidas"),
                     ("dores_esperadas", "dores_ambiguas"),
                     ("dores_proibidas", "dores_ambiguas")]:
            if inter := conjuntos[a] & conjuntos[b]:
                problemas.append(f"{arq}: {inter} aparece em `{a}` E `{b}`")
        if faltam := DORES_VALIDAS - set().union(*conjuntos.values()):
            problemas.append(
                f"{arq}: {sorted(faltam)} não está em nenhuma das três listas de dor — "
                f"toda dor precisa de veredito explícito, inclusive 'ambígua'"
            )

        if g.get("elegivel") is False and not g.get("motivo_exclusao"):
            problemas.append(f"{arq}: `elegivel: false` sem `motivo_exclusao` — "
                             f"recusar sem dizer por qual regra não é mensurável")
        if g.get("elegivel") is True and g.get("motivo_exclusao"):
            problemas.append(f"{arq}: `elegivel: true` com `motivo_exclusao` preenchido")
    return problemas


def evidencia_literal(fixtures: list[dict]) -> list[str]:
    """TODA `Evidencia` produzida cita um trecho que ocorre VERBATIM no documento citado.

    É a rede mais importante da transição stub -> LLM: o casador de substring não tem como
    inventar citação porque recorta com `str`; um LLM tem. Custa zero chamada de API e pega
    paráfrase silenciosa, que é o modo de falha que destruiria a rastreabilidade sem quebrar
    nenhum teste existente.
    """
    falhas: list[str] = []
    for i, f in enumerate(fixtures):
        startup = como_startup(f, i)
        por_id = {d.documento_id: d.conteudo_texto for d in startup.documentos}
        perfil = extractor.node({"startup": startup})["perfil"]
        for afirmacao in perfil.afirmacoes:
            for ev in afirmacao.evidencias:
                fonte = por_id.get(ev.documento_id)
                if fonte is None:
                    falhas.append(f"{f['nome']}: evidência aponta documento_id inexistente "
                                  f"{ev.documento_id}")
                elif ev.trecho not in fonte:
                    falhas.append(f"{f['nome']}: trecho NÃO ocorre no documento "
                                  f"{ev.documento_id}: {ev.trecho[:70]!r}")
    return falhas


def teto_do_casador(fixtures: list[dict]) -> tuple[int, int, list[str]]:
    """O TETO DE RECALL DAS HEURÍSTICAS, medido sem gastar uma chamada (D-053).

    O desenho recomendado do Extractor mantém `GATILHOS_DOR` como GERADOR DE CANDIDATOS e põe o
    LLM como juiz. O custo honesto dessa escolha é que dor expressa com palavra fora da lista
    nunca vira candidata, e o LLM nunca a vê. Este número é esse custo: quantas
    `dores_esperadas` do gabarito têm ao menos um candidato hoje. Nenhum julgamento por LLM pode
    superá-lo, então ele é o teto — e se estiver baixo, o trabalho é ampliar os gatilhos, não
    trocar de modelo.
    """
    alcancadas = total = 0
    perdidas: list[str] = []
    for i, f in enumerate(fixtures):
        esperadas = set((f.get("gabarito") or {}).get("dores_esperadas") or [])
        if not esperadas:
            continue
        startup = como_startup(f, i)
        candidatas = {d.dor for d in extractor.node({"startup": startup})["perfil"].dores_observadas}
        total += len(esperadas)
        alcancadas += len(esperadas & candidatas)
        for dor in sorted(esperadas - candidatas):
            perdidas.append(f"{f['nome']}: `{dor}` esperada e SEM candidato do casador")
    return alcancadas, total, perdidas


ARQ_EXCLUSOES = Path(__file__).resolve().parent.parent / "data" / "avaliacao" / "exclusoes.yaml"


def _perfil_de_um_trecho(frase: str):
    """O perfil mínimo que `elegibilidade()` sabe ler: ela varre
    `perfil.afirmacoes[*].evidencias[*].trecho` e nada mais."""
    from src.state import Afirmacao, Evidencia, PerfilStartup
    return PerfilStartup(
        startup_id=1, nome="Acme",
        sinais_otimizacao_tecnica=[Afirmacao(
            texto="trecho sob teste",
            evidencias=[Evidencia(documento_id=1, tipo_documento="site",
                                  url_fonte="https://exemplo.test/", trecho=frase)])],
    )


def medir_exclusoes() -> dict:
    """O FILTRO DO INCEPTION, MEDIDO NOS DOIS LADOS (D-061). Zero chamada de API.

    Os dois números NÃO são somados, e isso é a decisão que o arquivo inteiro carrega. Um filtro
    que exclui tudo tem zero falso negativo; um que não exclui nada tem zero falso positivo. Uma
    "acurácia" única premiaria os dois e esconderia exatamente a assimetria que fez D-052 adiar a
    correção: o falso positivo aparece no briefing, o falso NEGATIVO não aparece em lugar nenhum.

    Para `exclui: true` não basta recusar — tem que recusar pelo RÓTULO CERTO. É a regra que a
    fixture da Deal já declarava: *"recusar pelo motivo errado conta como erro nomeado, e não como
    acerto"*, e foi o defeito que D-048 pagou quando uma startup de infraestrutura era recusada por
    "cripto" ao falar em custo por token.
    """
    from src.state import StartupRef
    casos = yaml.safe_load(ARQ_EXCLUSOES.read_text(encoding="utf-8"))["casos"]
    startup = StartupRef(startup_id=1, nome="Acme", site="https://exemplo.test",
                         ano_fundacao=2022)

    acertos = {True: 0, False: 0}
    totais = {True: 0, False: 0}
    falhas: list[str] = []
    for caso in casos:
        esperado, rotulo = caso["exclui"], caso["rotulo"]
        resultado = briefing.elegibilidade(startup, _perfil_de_um_trecho(caso["frase"]))
        rotulos = {m.split("'")[1] for m in resultado.motivos_exclusao
                   if m.startswith("exclusão por '")}
        totais[esperado] += 1
        if esperado:
            # RÓTULO CERTO **E NENHUM OUTRO**. A primeira versão checava só `rotulo in rotulos`,
            # o que deixava passar exatamente o defeito que D-048 pagou — recusar pelo motivo
            # errado — na metade da régua criada para pegá-lo. Achado nº 6 do review de 27/08.
            ok = rotulos == {rotulo}
            if not ok:
                falhas.append(
                    f"FALSO NEGATIVO · {rotulo:15} passou: {caso['frase'][:78]!r}"
                    if rotulo not in rotulos else
                    f"rótulo EXTRA  · esperado só {rotulo!r}, veio {sorted(rotulos)}: "
                    f"{caso['frase'][:56]!r}")
        else:
            ok = not rotulos
            if not ok:
                falhas.append(f"falso positivo · {rotulo:15} excluiu por {sorted(rotulos)}: "
                              f"{caso['frase'][:60]!r}")
        acertos[esperado] += ok
    proc = {"de fixture": 0, "derivado de teste": 0, "sintético": 0}
    for c in casos:
        o = c["origem"]
        proc["sintético" if o == "sintético"
             else "de fixture" if o.startswith("data/seed") else "derivado de teste"] += 1
    return {"acertos": acertos, "totais": totais, "falhas": falhas,
            "proc": proc, "n": len(casos)}


ARQ_JUSTIFICATIVAS = (Path(__file__).resolve().parent.parent / "data" / "avaliacao"
                     / "justificativas.yaml")


def medir_justificativas() -> dict:
    """A RÉGUA DA `justificativa_tecnica` — P-10 (D-086). Zero chamada de API.

    A LINHA TRIVIAL É OBRIGATÓRIA AQUI COMO EM TODA TABELA DESTE ARQUIVO (D-051), e neste critério
    ela é forte: *"os 150 primeiros caracteres do chunk"* é o que produção entregava, e metade dos
    chunks do corpus começa por uma frase boa. Sem ela, qualquer número do seletor pareceria
    vitória. Ela é recalculada do texto — não do rótulo `nota_prefixo` do YAML —, para que o
    placar não dependa de quem rotulou.

    Os chunks com `ancoras: null` (nada neles serve) saem do DENOMINADOR: punir o seletor por não
    achar o que não existe mede a amostra, não o seletor. Eles continuam impressos, porque quantos
    são é informação sobre o corpus.
    """
    import psycopg
    from psycopg.rows import dict_row
    from src.agents.justificativa import melhor_trecho
    from src.config import DATABASE_URL

    d = yaml.safe_load(ARQ_JUSTIFICATIVAS.read_text(encoding="utf-8"))
    casos = d["casos"]
    ids = [c["chunk"] for c in casos]
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as cx, cx.cursor() as cur:
        cur.execute("SELECT id, texto FROM chunks_nvidia WHERE id = ANY(%(ids)s)", {"ids": ids})
        texto_de = {r["id"]: r["texto"] for r in cur.fetchall()}

    faltando = [i for i in ids if i not in texto_de]
    acertos = {"trivial": 0, "seletor": 0}
    com_alvo = 0
    falhas: list[str] = []
    for caso in casos:
        texto = texto_de.get(caso["chunk"])
        if texto is None or not caso["ancoras"]:
            continue
        com_alvo += 1
        trivial = texto[:150]
        escolhido = melhor_trecho(texto)
        ok_t = any(a in trivial for a in caso["ancoras"])
        ok_s = any(a in escolhido for a in caso["ancoras"])
        acertos["trivial"] += ok_t
        acertos["seletor"] += ok_s
        if not ok_s:
            falhas.append(f"#{caso['chunk']:<4} {caso['tecnologia'][:22]:22} "
                          f"escolheu {escolhido[:64]!r}")
    return {"acertos": acertos, "com_alvo": com_alvo, "n": len(casos),
            "sem_alvo": sum(1 for c in casos if not c["ancoras"]),
            "faltando": faltando, "falhas": falhas, "seed": d["amostra"]["seed"]}


def validar_exclusoes() -> list[str]:
    """O gabarito de exclusão também precisa de gabarito (achado nº 7 do review de 27/08).

    Sem isto, `rotulo: consultria` com um typo vira um FALSO NEGATIVO fantasma que nunca some, e
    o operador vai procurar o defeito em `briefing.EXCLUSOES`, onde ele não está.
    """
    problemas: list[str] = []
    casos = yaml.safe_load(ARQ_EXCLUSOES.read_text(encoding="utf-8"))["casos"]
    vistos: dict[str, set[bool]] = {}
    for i, c in enumerate(casos):
        onde = f"exclusoes.yaml[{i}]"
        for campo in ("rotulo", "exclui", "frase", "origem"):
            if campo not in c:
                problemas.append(f"{onde}: falta `{campo}`")
        if (r := c.get("rotulo")) and r not in briefing.EXCLUSOES:
            problemas.append(f"{onde}: rótulo {r!r} não existe em briefing.EXCLUSOES")
        elif r is not None:
            vistos.setdefault(r, set()).add(bool(c.get("exclui")))
    # Par mínimo: um rótulo com um lado só mede metade, e é a metade que a assimetria de D-052
    # diz que não pode ser medida sozinha.
    for r, lados in sorted(vistos.items()):
        if len(lados) < 2:
            problemas.append(f"rótulo {r!r} só tem o lado `exclui: {lados.pop()}` — "
                             f"par mínimo exige os dois")
    return problemas


def teto_do_degrau_2a(fixtures: list[dict]) -> tuple[int, int, list[str]]:
    """O TETO DA RUBRICA EM DEGRAUS, medido sem gastar uma chamada — e a lição de D-060.

    Irmão de `teto_do_casador`, e ele existe pelo mesmo motivo: um alvo fixado sem saber o que é
    ALCANÇÁVEL não é disciplina, é chute com cara de disciplina. D-058 pôs a barra de `classe` em
    5/7 sem este número; se ele existisse, teria mostrado que o degrau `2a` — profundidade técnica
    própria — só pode mover as fixtures que TÊM vocabulário de infraestrutura nos documentos, e que
    são **uma**. As outras `AI-native` do gabarito dependem do degrau `2b`, que é idêntico à
    aritmética antiga e portanto não move nada.

    Devolve: quantas fixtures cujo gabarito decide `AI-native` têm profundidade suficiente para o
    degrau `2a` disparar. Nenhuma rubrica que dependa de `2a` pode superar isso.
    """
    alcancaveis = total = 0
    fora: list[str] = []
    for i, f in enumerate(fixtures):
        aceitos = _aceitaveis((f.get("gabarito") or {}).get("classe"))
        if aceitos != {"AI-native"}:      # só as que o gabarito DECIDE como AI-native
            continue
        total += 1
        n, _ = classifier.profundidade_tecnica(como_startup(f, i).documentos)
        if n >= classifier.MARCADORES_PARA_PROFUNDIDADE:
            alcancaveis += 1
        else:
            fora.append(f"{f['nome']}: {n} marcador(es) de profundidade — fora do alcance do "
                        f"degrau 2a, depende do 2b")
    return alcancaveis, total, fora


# ─────────────────────────────────────────────────────────────────────────────
# Execução dos agentes
# ─────────────────────────────────────────────────────────────────────────────


def rodar(f: dict, motor: str, indice: int = 0) -> dict:
    """Roda a cadeia até o motor pedido e devolve o que a régua lê."""
    startup = como_startup(f, indice)
    estado = {"plano": PlanoDeBusca(consulta_original="régua dos agentes"), "startup": startup}
    estado.update(extractor.node(estado))
    if motor == "extrator":
        return estado
    estado.update(classifier.node(estado))
    if motor == "classificador":
        return estado
    estado.update(evidence_validator.node(estado))
    if motor == "validador":
        estado.update(briefing.node_analise(estado))
        return estado
    estado.update(briefing.node_analise(estado))
    # ponta-a-ponta: daqui para baixo CUSTA API (embedding + rerank por dor observada).
    from src.agents import nvidia_rag, recommendation
    estado.update(nvidia_rag.node(estado))
    estado.update(recommendation.node(estado))
    return estado


def baseline(f: dict, indice: int = 0) -> dict:
    """A LINHA DE BASE TRIVIAL, e ela é obrigatória na tabela.

    Sempre `AI-native`, stack `baixa`, todas as oito dores, sempre elegível. É o equivalente do
    `denso puro` na tabela do RAG: nenhum número de agente vai para o `CLAUDE.md` sem esta linha
    ao lado, porque com 3 startups todas AI-native ela acertava 3 de 3 e ninguém sabia.
    """
    from src.state import Diagnostico, DorObservada, Elegibilidade, PerfilStartup

    startup = como_startup(f, indice)
    doc = startup.documentos[0]
    from src.state import Evidencia
    ev = [Evidencia.de_documento(doc, doc.conteudo_texto[:200])]
    perfil = PerfilStartup(
        startup_id=startup.startup_id, nome=startup.nome,
        dores_observadas=[DorObservada(dor=d, texto=f"dor {d}", evidencias=ev, validada=True)
                          for d in sorted(DORES_VALIDAS)],
    )
    return {
        "startup": startup,
        "perfil": perfil,
        "diagnostico": Diagnostico(
            classe="AI-native", maturidade_stack="baixa",
            quadrante=derivar_quadrante("AI-native", "baixa"),
            confianca="alta", justificativa="linha de base trivial", evidencias=ev),
        "elegibilidade": Elegibilidade(elegivel=True),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Contagem
# ─────────────────────────────────────────────────────────────────────────────


def _obtido(estado: dict, caminho: str):
    objeto, atributo = caminho.split(".")
    alvo = estado.get(objeto)
    if alvo is None:
        return None
    if atributo == "motivo":
        # o RÓTULO da exclusão, não a frase: "exclusão por 'consultoria': o termo ..."
        for m in alvo.motivos_exclusao:
            if m.startswith("exclusão por '"):
                return m.split("'")[1]
            if m.startswith("exclusão por idade"):
                return "idade"
        return None
    return getattr(alvo, atributo, None)


def medir(fixtures: list[dict], motor: str, usar_baseline: bool) -> dict:
    placar = {c: {"acerto": 0, "ambiguo": 0, "nao_medido": 0, "erro": 0} for c in CAMPOS}
    divergencias: list[str] = []
    proibidas_emitidas: list[str] = []
    precisoes: list[float] = []
    recalls: list[float] = []
    assinaturas: set[frozenset] = set()
    proibidas_validadas: list[str] = []
    precisoes_v: list[float] = []
    recalls_v: list[float] = []
    assinaturas_validadas: set[frozenset] = set()

    for i, f in enumerate(fixtures):
        g = f.get("gabarito") or {}
        estado = baseline(f, i) if usar_baseline else rodar(f, motor, i)

        for campo, (caminho, _) in CAMPOS.items():
            aceitos = _aceitaveis(g.get(campo))
            # `motivo_exclusao: null` NÃO é "não medido" quando o gabarito já decidiu a
            # elegibilidade: com `elegivel: true`, o motivo esperado é NENHUM, e emitir um é
            # erro. Sem esta distinção, Axenya e Freedom AI — excluídas pelo rótulo errado —
            # apareciam numa coluna limpa de 1/1, e era esse 1/1 que o CLAUDE.md publicava.
            # Achado nº 6 do code review de 25/08.
            if campo == "motivo_exclusao" and aceitos is None and g.get("elegivel") is True:
                aceitos = {None}
            if aceitos is None:
                placar[campo]["nao_medido"] += 1
                continue
            obtido = _obtido(estado, caminho)
            if obtido in aceitos:
                placar[campo]["ambiguo" if len(aceitos) > 1 else "acerto"] += 1
            else:
                placar[campo]["erro"] += 1
                divergencias.append(
                    f"{f['nome']:16} {campo:17} esperado {sorted(map(str, aceitos))} · obtido {obtido!r}")

        perfil = estado.get("perfil")
        dores = perfil.dores_observadas if perfil else []
        # DUAS COLUNAS, E A SEPARAÇÃO É O PASSO 0 DE D-074.
        #
        # `emitidas` é o que o Extractor produziu; `validadas` é o que sobrevive ao Evidence
        # Validator e chega ao Recommendation, que filtra por `d.validada`.
        #
        # Até 31/08 esta régua lia SÓ `dores_observadas` e ignorava `validada`. Isso a tornava
        # CEGA para a mudança que D-074 decide: um validator que marca a dor como inválida em vez
        # de deletá-la não moveria o placar um milímetro, e a medição mediria zero.
        #
        # Hoje as duas colunas são IDÊNTICAS, e essa identidade é o achado: `validada` só é
        # `False` quando não há evidência nenhuma, e o Extractor nunca cria dor sem evidência.
        # Medido em 31/08: 34 de 34 passam. É um portão que nunca fecha.
        emitidas = {d.dor for d in dores}
        validadas = {d.dor for d in dores if d.validada}
        assinaturas.add(frozenset(emitidas))
        assinaturas_validadas.add(frozenset(validadas))
        esperadas = set(g.get("dores_esperadas") or [])
        proibidas = set(g.get("dores_proibidas") or [])
        ambiguas = set(g.get("dores_ambiguas") or [])

        for dor in sorted(emitidas & proibidas):
            marca = "" if dor in validadas else " (mas o validator BARROU)"
            proibidas_emitidas.append(
                f"{f['nome']:16} emitiu `{dor}`, que o gabarito PROÍBE{marca}")
        for dor in sorted(validadas & proibidas):
            proibidas_validadas.append(
                f"{f['nome']:16} entregou `{dor}` ao Recommendation, e o gabarito PROÍBE")

        for conjunto, precs, recs in ((emitidas, precisoes, recalls),
                                      (validadas, precisoes_v, recalls_v)):
            # As ambíguas saem dos dois lados: não contam a favor nem contra.
            contaveis = conjunto - ambiguas
            if contaveis:
                precs.append(len(contaveis & esperadas) / len(contaveis))
            elif not esperadas:
                # Nada esperado e nada emitido é o comportamento CORRETO, e precisa ser premiado:
                # três fixtures (SunnyHUB, RD Station, Deal) existem justamente para medir isso.
                precs.append(1.0)
            # Emitiu nada e havia o que emitir: precisão é INDEFINIDA, não zero — "não previu" não
            # é o mesmo que "previu tudo errado", e é o recall que pune este caso. Simétrico com o
            # recall, que já pula fixtures sem `dores_esperadas`. Achado nº 7 do code review.
            if esperadas:
                recs.append(len(conjunto & esperadas) / len(esperadas))

    def _media(v):
        return sum(v) / len(v) if v else None

    return {
        "placar": placar, "divergencias": divergencias, "proibidas": proibidas_emitidas,
        "precisao": _media(precisoes),
        "recall": _media(recalls),
        "discriminacao": (len(assinaturas), len(fixtures)),
        # Coluna `validada` — o que chega ao Recommendation. Ver D-074.
        "proibidas_v": proibidas_validadas,
        "precisao_v": _media(precisoes_v),
        "recall_v": _media(recalls_v),
        "discriminacao_v": (len(assinaturas_validadas), len(fixtures)),
    }


def imprimir(titulo: str, r: dict, detalhar: bool) -> None:
    print(f"\n{titulo}")
    print(f"  {'campo':18} {'acertos':>10}  {'ambíguos':>9} {'não medidos':>12}")
    for campo, p in r["placar"].items():
        decididos = p["acerto"] + p["erro"]
        marca = f"{p['acerto']}/{decididos}" if decididos else "—"
        print(f"  {campo:18} {marca:>10}  {p['ambiguo']:>9} {p['nao_medido']:>12}")
    # DUAS COLUNAS (D-074, passo 0): `emitida` é o que o Extractor produziu, `validada` é o que
    # sobrevive ao Evidence Validator e chega ao Recommendation. Enquanto forem idênticas, o
    # portão `if d.validada` do recommendation.py não está filtrando nada.
    def _pct(v):
        return f"{v:.0%}" if v is not None else "—"

    d, n = r["discriminacao"]
    dv, _ = r["discriminacao_v"]
    identicas = (r["precisao"] == r["precisao_v"] and r["recall"] == r["recall_v"]
                 and len(r["proibidas"]) == len(r["proibidas_v"]))
    print(f"  {'dor':18} {'emitida':>10} {'validada':>10}")
    print(f"  {'  precisão':18} {_pct(r['precisao']):>10} {_pct(r['precisao_v']):>10}   <- manchete")
    print(f"  {'  recall':18} {_pct(r['recall']):>10} {_pct(r['recall_v']):>10}")
    print(f"  {'  discriminação':18} {f'{d}/{n}':>10} {f'{dv}/{n}':>10}")
    print(f"  {'  proibida':18} {len(r['proibidas']):>10} {len(r['proibidas_v']):>10}   emissão(ões)")
    if identicas:
        print("       ^ as duas colunas são IDÊNTICAS: o filtro `if d.validada` do "
              "recommendation.py não barrou nada (D-074)")
    if detalhar:
        for linha in r["divergencias"]:
            print(f"    x {linha}")
        for linha in r["proibidas"]:
            print(f"    ! {linha}")


def main() -> int:
    ap = argparse.ArgumentParser(description="A régua dos agentes. Ver o docstring do módulo.")
    ap.add_argument("--validar", action="store_true",
                    help="coerência do gabarito, evidência literal e teto do casador. Zero API")
    ap.add_argument("--baseline", action="store_true",
                    help="mede a linha trivial: sempre AI-native, todas as dores")
    ap.add_argument("--motor", default="validador",
                    choices=["extrator", "classificador", "validador", "ponta-a-ponta"],
                    help="ablação; `ponta-a-ponta` inclui nvidia_rag e CUSTA API")
    ap.add_argument("--falhas", action="store_true", help="detalha cada divergência")
    ap.add_argument("--juiz", action="store_true",
                    help="LIGA o juiz com LLM do Extractor (default é desligado, D-056). CUSTA API")
    # Os dois braços medidos na sessão 07 e REPROVADOS por D-058. Ficam ligáveis pelo mesmo motivo
    # que `--juiz`: a alternativa medida no repositório é material de defesa melhor que um registro
    # só no histórico do git, e o harness consegue medir os dois lados. Zero API nos dois.
    ap.add_argument("--exclusoes", action="store_true",
                    help="régua do filtro do Inception: falso positivo E falso negativo. Zero API")
    ap.add_argument("--justificativas", action="store_true",
                    help="régua da justificativa_tecnica: seletor vs. os 150 primeiros. Zero API")
    ap.add_argument("--rubrica", action="store_true",
                    help="LIGA a rubrica em degraus do Classifier (default desligado, D-060)")
    ap.add_argument("--confianca-diagnostico", action="store_true",
                    help="LIGA a confiança tirada da evidência do diagnóstico (default desligado, D-059)")
    ap.add_argument("--sustentacao", action="store_true",
                    help="LIGA o julgamento de sustentação no Evidence Validator (D-074). CUSTA API")
    args = ap.parse_args()

    # Braço ligado que o modo escolhido nunca executa é pior que erro: o título ANUNCIA o braço
    # e a tabela sai da produção. Mesma disciplina que `--juiz --validar` já tinha.
    # Achado nº 12 do code review de 27/08.
    inertes = [n for n, on in (("--rubrica", args.rubrica),
                               ("--sustentacao", args.sustentacao),
                               ("--confianca-diagnostico", args.confianca_diagnostico)) if on]
    if inertes and (args.baseline or args.exclusoes or args.validar
                    or args.justificativas
                    or args.motor == "extrator"):
        modo = ("--baseline" if args.baseline else "--exclusoes" if args.exclusoes
                else "--validar" if args.validar else "--motor extrator")
        print(f"  {', '.join(inertes)} ignorado(s) em {modo}: este modo não chama o agente")
        args.rubrica = args.confianca_diagnostico = args.sustentacao = False

    if args.rubrica:
        classifier.RUBRICA_EM_DEGRAUS = True
    if args.confianca_diagnostico:
        evidence_validator.CONFIANCA_DA_EVIDENCIA_DO_DIAGNOSTICO = True

    if args.sustentacao and args.juiz:
        # Os dois fazem A MESMA PERGUNTA em pontos diferentes (D-074). Ligados juntos, o juiz
        # deleta o candidato antes e o validator julga o que sobrou: paga-se duas vezes e o
        # número não fica atribuído a nenhuma das duas colocações, que é justamente o que o
        # passo 2 de D-074 existe para separar.
        print("  --sustentacao com --juiz é recusado: a mesma pergunta em dois pontos não atribui")
        return 1
    if args.sustentacao:
        # O braço que gasta API se pede pelo NOME. Mesma disciplina de `--juiz` e `--truncar-pool`.
        evidence_validator.JULGAR_SUSTENTACAO = True

    if args.juiz and args.validar:
        # `--validar` chama `extractor.node` nas 8 fixtures (evidência literal e teto do
        # casador). Com o juiz ligado isso gastaria as ~52 chamadas que a documentação atribui
        # só à medição — e, pior, o número medido deixaria de ser o TETO DO CASADOR para virar
        # o recall do juiz, que é outra coisa. Achado nº 8 do code review de 25/08.
        print("  --juiz é ignorado em --validar: o teto medido é o do CASADOR, por definição")
    elif args.juiz:
        # O braço que gasta API se pede pelo NOME — nunca por descuido. Mesma disciplina de
        # `--truncar-pool` no harness do RAG (D-044).
        import src.agents.extractor as _ex
        _ex.USAR_JUIZ_LLM = True

    if args.exclusoes:
        if problemas := validar_exclusoes():
            print("RÉGUA DE EXCLUSÃO INCOERENTE:")
            for p_ in problemas:
                print(f"  - {p_}")
            return 1
        r = medir_exclusoes()
        proc = ", ".join(f"{v} {k}" for k, v in r["proc"].items() if v)
        print(f"{r['n']} caso(s) em data/avaliacao/exclusoes.yaml ({proc})\n")
        print("  filtro do NVIDIA Inception — os dois lados, NUNCA somados:")
        print(f"    {'excluídas corretamente':30} {r['acertos'][True]}/{r['totais'][True]}"
              f"   <- falso NEGATIVO: o risco silencioso")
        print(f"    {'passaram corretamente':30} {r['acertos'][False]}/{r['totais'][False]}"
              f"   <- falso positivo: aparece no briefing")
        for f in r["falhas"]:
            print(f"      x {f}")
        return 0

    if args.justificativas:
        r = medir_justificativas()
        if r["faltando"]:
            print(f"chunks do gabarito ausentes do banco: {r['faltando']}")
            print("  a amostra é por ID e o corpus foi re-ingerido — re-amostre antes de medir")
            return 1
        print(f"{r['n']} chunk(s) em data/avaliacao/justificativas.yaml (amostra semeada "
              f"{r['seed']}) · {r['sem_alvo']} sem alvo, fora do denominador\n")
        print("  de onde sai a justificativa_tecnica:")
        for nome, rotulo in (("trivial", "os 150 primeiros caracteres  <- a linha trivial (D-051)"),
                             ("seletor", "melhor_trecho()              <- o seletor de D-086")):
            a = r["acertos"][nome]
            print(f"    {rotulo:56} {a}/{r['com_alvo']} = {a / r['com_alvo']:.0%}")
        for f in r["falhas"]:
            print(f"      x {f}")
        return 0

    fixtures = carregar()
    print(f"{len(fixtures)} fixture(s) em data/seed/")

    if args.validar:
        if problemas := validar(fixtures):
            print("\nGABARITO INCOERENTE:")
            for p in problemas:
                print(f"  - {p}")
            return 1
        print("  coerência do gabarito: ok")

        if falhas := evidencia_literal(fixtures):
            print("\nEVIDÊNCIA NÃO LITERAL:")
            for f in falhas:
                print(f"  - {f}")
            return 1
        print("  evidência literal: ok — todo trecho ocorre verbatim no documento citado")

        ok, total, perdidas = teto_do_casador(fixtures)
        print(f"  teto de recall do casador: {ok}/{total} = {ok / total:.0%}")
        for p in perdidas:
            print(f"      - {p}")

        ok, total, fora = teto_do_degrau_2a(fixtures)
        print(f"  teto do degrau 2a da rubrica: {ok}/{total} das AI-native decididas")
        for f in fora:
            print(f"      - {f}")
        return 0

    r = medir(fixtures, args.motor, args.baseline)
    bracos = [n for n, ligado in (("juiz LLM", args.juiz), ("rubrica em degraus", args.rubrica),
                                  ("confiança do diagnóstico", args.confianca_diagnostico)) if ligado]
    titulo = ("linha de base TRIVIAL (sempre AI-native, todas as 8 dores)" if args.baseline
              else f"motor: {args.motor}"
                   + (f" · LIGADO: {', '.join(bracos)}" if bracos else " · casador (produção)"))
    imprimir(titulo, r, args.falhas)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
