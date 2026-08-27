"""A RÉGUA DOS AGENTES — o que o `avaliar_rag.py` é para o critério 2, este arquivo é para os
critérios 1 e 3 (40 pontos do barema).

POR QUE ELE EXISTE, E POR QUE VEM ANTES DO EXTRACTOR COM LLM
--------------------------------------------------------------
Até 25/08 a base tinha 3 startups e as 3 eram `perfil_alvo: AI-native`. Um classificador que
devolvesse `"AI-native"` incondicionalmente passava em 3 de 3 — não havia número capaz de
distinguir um Extractor com LLM do casador de substring que está lá desde a sessão 01. O RAG
chegou a nível 4 porque teve régua desde o primeiro dia; os agentes não tinham nenhuma, e
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
        emitidas = {d.dor for d in perfil.dores_observadas} if perfil else set()
        assinaturas.add(frozenset(emitidas))
        esperadas = set(g.get("dores_esperadas") or [])
        proibidas = set(g.get("dores_proibidas") or [])
        ambiguas = set(g.get("dores_ambiguas") or [])

        for dor in sorted(emitidas & proibidas):
            proibidas_emitidas.append(f"{f['nome']:16} emitiu `{dor}`, que o gabarito PROÍBE")

        # As ambíguas saem dos dois lados: não contam a favor nem contra.
        contaveis = emitidas - ambiguas
        if contaveis:
            precisoes.append(len(contaveis & esperadas) / len(contaveis))
        elif not esperadas:
            # Nada esperado e nada emitido é o comportamento CORRETO, e precisa ser premiado:
            # três fixtures (SunnyHUB, RD Station, Deal) existem justamente para medir isso.
            precisoes.append(1.0)
        # Emitiu nada e havia o que emitir: precisão é INDEFINIDA, não zero — "não previu" não
        # é o mesmo que "previu tudo errado", e é o recall que pune este caso. Simétrico com o
        # recall, que já pula fixtures sem `dores_esperadas`. Achado nº 7 do code review.
        if esperadas:
            recalls.append(len(emitidas & esperadas) / len(esperadas))

    return {
        "placar": placar, "divergencias": divergencias, "proibidas": proibidas_emitidas,
        "precisao": sum(precisoes) / len(precisoes),
        "recall": sum(recalls) / len(recalls) if recalls else None,
        "discriminacao": (len(assinaturas), len(fixtures)),
    }


def imprimir(titulo: str, r: dict, detalhar: bool) -> None:
    print(f"\n{titulo}")
    print(f"  {'campo':18} {'acertos':>10}  {'ambíguos':>9} {'não medidos':>12}")
    for campo, p in r["placar"].items():
        decididos = p["acerto"] + p["erro"]
        marca = f"{p['acerto']}/{decididos}" if decididos else "—"
        print(f"  {campo:18} {marca:>10}  {p['ambiguo']:>9} {p['nao_medido']:>12}")
    prec, rec = r["precisao"], r["recall"]
    print(f"  {'dor — precisão':18} {prec:>10.0%}   <- manchete")
    print(f"  {'dor — recall':18} {rec:>10.0%}" if rec is not None else "  dor — recall            —")
    d, n = r["discriminacao"]
    print(f"  {'discriminação':18} {f'{d}/{n}':>10}   conjuntos distintos de dores")
    print(f"  {'dor proibida':18} {len(r['proibidas']):>10}   emissão(ões)")
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
    args = ap.parse_args()

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
        return 0

    r = medir(fixtures, args.motor, args.baseline)
    titulo = ("linha de base TRIVIAL (sempre AI-native, todas as 8 dores)" if args.baseline
              else f"motor: {args.motor}" + (" · JUIZ LLM LIGADO" if args.juiz else " · casador (produção)"))
    imprimir(titulo, r, args.falhas)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
