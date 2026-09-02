"""Passo 9 do pipeline RAG do TAPI: avaliação de qualidade. Ver D-030, D-031 e D-037.

Sem este passo o RAG é infalsificável: não há como saber se uma mudança de chunking, de dimensão
ou de fusão melhorou ou piorou a recuperação. Ele existe desde a sessão 02 exatamente por isso —
sem instrumento, essas decisões seriam argumento em vez de medida (D-031).

AS MÉTRICAS
-----------
1. **recall@k frouxo** — algum dos k primeiros chunks veio do documento esperado.
   É a principal porque SOBREVIVE a mudança de chunking: é o que permite comparar
   'estrutural-v1' com 'fixo-800' na mesma régua (D-030).

2. **recall@k estrito** — além do documento certo, o chunk contém `frase_ancora`.
   Um documento pode ser recuperado pelo motivo errado: a página do TensorRT-LLM tem 27 mil
   caracteres e recuperar QUALQUER pedaço dela não prova que o pedaço responde a pergunta.

3. **margem de abstenção** — a distância entre o pior acerto e o melhor score de uma pergunta
   SEM resposta na base. Se as duas distribuições se sobrepõem, nenhum limiar separa e o
   sistema não tem como dizer "não sei". Medida em D-033 sobre o score denso (−0,1879) e em
   D-035 sobre o logit do reranker.

QUATRO DECISÕES DE DESENHO DESTE HARNESS
------------------------------------------
1. **Recupera UMA vez em `--pool` e deriva recall@1, @3 e @5 fatiando a mesma lista.** A versão
   anterior chamava a busca uma vez por k, o que gastava 3x as chamadas de API e — pior —
   comparava k's obtidos em recuperações diferentes. Fatiar uma lista só torna a comparação
   entre k's exata.

2. **Cache por BRAÇO, não por motor.** As listas densa e lexical de cada consulta são guardadas
   dentro do run. Como RRF e soma ponderada são funções puras dessas duas listas, a varredura
   `K × peso × alfa` do `--varredura` custa **zero chamada de API** — o mesmo truque que D-029
   usou para o sweep de dimensão.

3. **`--motor` é uma ablação, não uma opção.** denso → lexical → híbrido → rerank é exatamente
   a ordem em que o pipeline foi construído, e a tabela com as quatro colunas é a evidência de
   que cada incremento pagou o que custou. Incremento que não move a métrica precisa de
   justificativa escrita ou de remoção.

4. **O HARNESS MEDE O QUE A PRODUÇÃO RODA (D-044).** `POOL_PADRAO`, `K_RRF_PADRAO` e os pesos
   são IMPORTADOS de `src.rag.pipeline`, não redeclarados aqui, e o pool NÃO é truncado antes do
   rerank — as duas coisas seguem `pipeline.buscar_com_rerank`. Até 24/08 este arquivo declarava
   os seus próprios defaults (K=20, peso 0,5) e cortava a união em 20, e as duas divergências
   custaram caro: a tabela publicada no `CLAUDE.md` não saía do comando documentado, e o
   `--geracao` mediu a q17 num pipeline em que a passagem-âncora não existia, produzindo o
   diagnóstico errado que D-040 registrou. O braço de controle sobrevive em `--truncar-pool`,
   que se pede pelo nome em vez de acontecer por descuido.

`--validar` NÃO MEDE NADA e deveria rodar primeiro: confere que toda `frase_ancora` ocorre no
corpus e em uma só tecnologia, e que todo `termos_ausentes` de pergunta `sem_resposta` NÃO
ocorre. A segunda metade é o espelho da primeira: uma prova de que a resposta não está lá.

USO
---
    python scripts/avaliar_rag.py --validar
    python scripts/avaliar_rag.py                          # ablação completa, estrutural-v1
    python scripts/avaliar_rag.py --motor denso            # reproduz a linha de base de D-032
    python scripts/avaliar_rag.py --motor rerank_hibrido --falhas
    python scripts/avaliar_rag.py --varredura              # grade de fusão, zero chamada de API
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import RERANK
from src.db import conectar
from src.rag.busca import Passagem, buscar_denso_bruto, para_citacao
from src.rag.fusao import fundir_rrf, fundir_soma
from src.rag.geracao import gerar
from src.rag.lexical import buscar_lexical_bruto
from src.rag.pipeline import (
    K_RRF_PADRAO,
    PESO_DENSO_PADRAO,
    PESO_LEXICAL_PADRAO,
    POOL_PADRAO,
)
from src.rag.rerank import logits_de

GABARITO = Path(__file__).resolve().parent.parent / "data" / "avaliacao" / "gabarito.yaml"
ESTRATEGIAS = ("estrutural-v1", "fixo-800")
MOTORES = ("denso", "lexical", "hibrido", "rerank_denso", "rerank_hibrido")
KS_PADRAO = (1, 3, 5)

Resultado = list[tuple[Passagem, float]]


def carregar() -> list[dict]:
    return yaml.safe_load(GABARITO.read_text())


# ─────────────────────────────────────────────────────────────────────────────
# Validação do gabarito contra o corpus — não mede recuperação
# ─────────────────────────────────────────────────────────────────────────────

def validar(perguntas: list[dict]) -> int:
    print("Validando o gabarito contra o corpus (não mede recuperação)\n")
    problemas = 0
    with conectar() as cx, cx.cursor() as cur:

        cur.execute("SELECT texto FROM chunks_nvidia WHERE estrategia = 'estrutural-v1'")
        corpus = [linha["texto"] for linha in cur.fetchall()]

        def ocorre_palavra(termo: str) -> bool:
            rx = re.compile(r"\b" + re.escape(termo) + r"\b", re.IGNORECASE)
            return any(rx.search(texto) for texto in corpus)

        def ocorre(frase: str) -> list[dict]:
            cur.execute(
                """SELECT DISTINCT tecnologia, documento_url FROM chunks_nvidia
                   WHERE estrategia = 'estrutural-v1' AND texto ILIKE %s""",
                (f"%{frase}%",),
            )
            return cur.fetchall()

        for p in perguntas:
            if p["tipo"] == "sem_resposta":
                if p["url_esperada"] is not None:
                    print(f"  {p['id']}: tipo sem_resposta mas tem url_esperada")
                    problemas += 1
                    continue
                if not p.get("justificativa_ausencia"):
                    # A prosa é obrigatória e os termos não: há ausências que NENHUM termo prova.
                    # A da q20 é de um NÚMERO — não existe string cuja falta demonstre que um
                    # preço não está publicado. Quando o termo serve, ele é a prova executável;
                    # quando não serve, a curadoria escreve o argumento e assina embaixo.
                    print(f"  {p['id']}: sem_resposta SEM justificativa_ausencia da curadoria")
                    problemas += 1
                    continue
                # A PROVA DE AUSÊNCIA: se a curadoria declarou termos que tornariam a pergunta
                # respondível, nenhum deles pode existir no corpus. É o espelho da frase_ancora.
                #
                # FRONTEIRA DE PALAVRA, E NÃO O `ILIKE` DA ÂNCORA. Substring engana em termo
                # curto: `ILIKE '%SLA%'` casa dentro de "tran(sla)tion" e reportaria como
                # presente um termo que não está lá. A âncora pode usar ILIKE porque é frase
                # longa; o termo ausente, não.
                presentes = [t for t in (p.get("termos_ausentes") or []) if ocorre_palavra(t)]
                if presentes:
                    print(f"  {p['id']}: NÃO é sem_resposta — {presentes} ocorrem no corpus")
                    problemas += 1
                else:
                    n = len(p.get("termos_ausentes") or [])
                    regime = p.get("regime", "—")
                    print(f"  {p['id']}: sem_resposta OK [{regime}] — "
                          f"{n} termo(s) confirmadamente ausente(s)")
                continue

            achados = ocorre(p["frase_ancora"])
            urls = {a["documento_url"] for a in achados}
            if not achados:
                print(f"  {p['id']}: ÂNCORA AUSENTE NO CORPUS — {p['frase_ancora']!r}")
                problemas += 1
            elif p["url_esperada"] not in urls:
                print(f"  {p['id']}: âncora existe mas em outro documento — "
                      f"{sorted(a['tecnologia'] for a in achados)}")
                problemas += 1
            elif len(urls) > 1:
                print(f"  {p['id']}: âncora AMBÍGUA, ocorre em "
                      f"{sorted(a['tecnologia'] for a in achados)}")
                problemas += 1
            else:
                print(f"  {p['id']}: OK — {p['frase_ancora']!r} só em {p['tecnologia_esperada']}")

    print(f"\n{len(perguntas) - problemas}/{len(perguntas)} válidas")
    return 1 if problemas else 0


# ─────────────────────────────────────────────────────────────────────────────
# Os motores, com cache por braço (ver decisão 2 do docstring)
# ─────────────────────────────────────────────────────────────────────────────

_CACHE_DENSO: dict[tuple[str, str, int], Resultado] = {}
_CACHE_LEXICAL: dict[tuple[str, str, int], Resultado] = {}
# O PROVEDOR ENTRA NA CHAVE, E ISSO NÃO É ZELO (D-068). Sem ele, rodar duas linhas de
# provedor no mesmo processo faria a segunda ler os scores da primeira e as duas sairiam
# IDÊNTICAS — um empate produzido pelo cache, não pela medição. É a mesma classe de erro
# que o bytecode obsoleto causou na sessão 07: o número aparece, e é de outra coisa.
_CACHE_RERANK: dict[tuple[str, str, tuple[int, ...]], dict[int, float]] = {}


def braco_denso(consulta: str, estrategia: str, pool: int) -> Resultado:
    chave = (consulta, estrategia, pool)
    if chave not in _CACHE_DENSO:
        _CACHE_DENSO[chave] = buscar_denso_bruto(consulta, k=pool, estrategia=estrategia)
    return _CACHE_DENSO[chave]


def braco_lexical(consulta: str, estrategia: str, pool: int) -> Resultado:
    chave = (consulta, estrategia, pool)
    if chave not in _CACHE_LEXICAL:
        _CACHE_LEXICAL[chave] = buscar_lexical_bruto(consulta, k=pool, estrategia=estrategia)
    return _CACHE_LEXICAL[chave]


def braco_rerank(consulta: str, passagens: list[Passagem]) -> dict[int, float]:
    chave = (consulta, RERANK.provedor, tuple(p.chunk_id for p in passagens))
    if chave not in _CACHE_RERANK:
        _CACHE_RERANK[chave] = logits_de(consulta, passagens)
    return _CACHE_RERANK[chave]


def recuperar(motor: str, consulta: str, estrategia: str, cfg: dict) -> Resultado:
    """Devolve a lista ORDENADA do motor pedido. O k da métrica é fatia disto."""
    pool = cfg["pool"]
    if motor == "denso":
        return braco_denso(consulta, estrategia, pool)
    if motor == "lexical":
        return braco_lexical(consulta, estrategia, pool)

    # A PERGUNTA QUE ESTES DOIS MOTORES EXISTEM PARA RESPONDER: o braço lexical paga o que custa?
    # Como o passo 7 reordena tudo, a contribuição real do BM25 não é a ordem que ele produz — é
    # o POOL que ele entrega ao reranker. Comparar rerank sobre denso puro com rerank sobre a
    # híbrida isola exatamente isso.
    if motor.startswith("rerank"):
        base = "denso" if motor == "rerank_denso" else "hibrido"
        candidatos = recuperar(base, consulta, estrategia, cfg)
        # POR PADRÃO NÃO TRUNCA — é o que `pipeline.buscar_com_rerank` faz em produção.
        # `--truncar-pool` restaura o corte em `pool` e é o BRAÇO DE CONTROLE da pergunta "vale
        # a pena mandar a união inteira ao reranker?". Ver D-044.
        if cfg["truncar_pool"]:
            candidatos = candidatos[:pool]
        logits = braco_rerank(consulta, [p for p, _ in candidatos])
        reordenado = [(p, logits[p.chunk_id]) for p, _ in candidatos if p.chunk_id in logits]
        reordenado.sort(key=lambda x: -x[1])
        return reordenado

    denso = braco_denso(consulta, estrategia, pool)
    lexical = braco_lexical(consulta, estrategia, pool)
    pesos = {"denso": cfg["peso_denso"], "lexical": cfg["peso_lexical"]}
    if cfg["fusao"] == "rrf":
        fundido = fundir_rrf({"denso": denso, "lexical": lexical}, pesos, cfg["k_rrf"])
    else:
        fundido = fundir_soma({"denso": denso, "lexical": lexical}, pesos, cfg["norm"])

    return fundido


# ─────────────────────────────────────────────────────────────────────────────
# Avaliação
# ─────────────────────────────────────────────────────────────────────────────

def avaliar(perguntas: list[dict], motor: str, estrategia: str, cfg: dict) -> dict:
    KS = cfg["ks"]
    com_resposta = [p for p in perguntas if p["tipo"] != "sem_resposta"]
    sem_resposta = [p for p in perguntas if p["tipo"] == "sem_resposta"]

    frouxo = {k: 0 for k in KS}
    estrito = {k: 0 for k in KS}
    falhas: list[tuple] = []
    piores: list[float] = []

    for p in com_resposta:
        ordenado = recuperar(motor, p["pergunta"], estrategia, cfg)
        do_doc_em_k = {}
        for k in KS:
            do_doc = [(pa, s) for pa, s in ordenado[:k] if pa.documento_url == p["url_esperada"]]
            do_doc_em_k[k] = do_doc
            if do_doc:
                frouxo[k] += 1
                if any(p["frase_ancora"].lower() in pa.texto.lower() for pa, _ in do_doc):
                    estrito[k] += 1

        # A margem usa a MESMA definição de D-033, para que os números sejam comparáveis:
        # por pergunta, o melhor score entre os chunks do documento certo; entre perguntas, o pior.
        if do_doc_em_k[max(KS)]:
            piores.append(max(s for _, s in do_doc_em_k[max(KS)]))
        else:
            falhas.append((p["id"], p["tipo"], p["tecnologia_esperada"],
                           ordenado[0][0].tecnologia if ordenado else "—"))

    melhores_vazios = []
    for p in sem_resposta:
        ordenado = recuperar(motor, p["pergunta"], estrategia, cfg)
        if ordenado:
            melhores_vazios.append((p["id"], ordenado[0][1]))

    n = len(com_resposta)
    return {
        "n": n,
        "frouxo": {k: frouxo[k] / n for k in KS},
        "estrito": {k: estrito[k] / n for k in KS},
        "falhas": falhas,
        "pior_acerto": min(piores) if piores else None,
        "melhor_vazio": max(melhores_vazios, key=lambda x: x[1]) if melhores_vazios else None,
    }


def imprimir(resultados: dict[tuple[str, str], dict], cfg: dict, mostrar_falhas: bool) -> None:
    KS = cfg["ks"]
    cab = "  ".join(f"r@{k:<4}" for k in KS) + "  " + "  ".join(f"e@{k:<4}" for k in KS)
    print(f"\n{'motor':10} {'estratégia':15} {cab}")
    print("-" * (27 + len(cab)))
    for (motor, estrategia), r in resultados.items():
        linha = "  ".join(f"{r['frouxo'][k]:>4.0%} " for k in KS)
        linha += "  " + "  ".join(f"{r['estrito'][k]:>4.0%} " for k in KS)
        print(f"{motor:10} {estrategia:15} {linha}")
    print(f"\nr@k = recall@k frouxo (documento certo) · e@k = estrito (chunk contém a âncora)")
    print(f"pool por braço = {cfg['pool']}")

    if mostrar_falhas:
        for (motor, estrategia), r in resultados.items():
            if r["falhas"]:
                print(f"\nFalhas de {motor}/{estrategia} em recall@{max(KS)}:")
                for id_, tipo, esperado, veio in r["falhas"]:
                    print(f"  {id_} [{tipo}] esperava {esperado!r}, 1º colocado foi {veio!r}")

    print("\nABSTENÇÃO — o acerto nas perguntas sem resposta é NÃO responder:")
    for (motor, estrategia), r in resultados.items():
        pior, vazio = r["pior_acerto"], r["melhor_vazio"]
        if pior is None or vazio is None:
            continue
        id_vazio, score_vazio = vazio
        margem = pior - score_vazio
        veredito = ("SEPARÁVEL: existe limiar que abstém sem perder acerto" if margem > 0
                    else "NÃO separável: as distribuições se sobrepõem, nenhum limiar funciona")
        print(f"  {motor:10} {estrategia:15} pior acerto {pior:>9.4f} · "
              f"pior sem-resposta {score_vazio:>9.4f} ({id_vazio}) · margem {margem:+.4f}")
        print(f"  {'':26} {veredito}")


# ─────────────────────────────────────────────────────────────────────────────
# Varredura de fusão — zero chamada de API depois do primeiro motor
# ─────────────────────────────────────────────────────────────────────────────

def varredura(perguntas: list[dict], estrategia: str, cfg: dict) -> None:
    KS = cfg["ks"]
    print("VARREDURA DE FUSÃO — as listas densa e lexical são recuperadas UMA vez por consulta")
    print("e reaproveitadas. RRF e soma ponderada são funções puras delas, então a grade toda")
    print("custa ZERO chamada de API depois da primeira passada (D-037).\n")

    print(f"{'fusão':7} {'K/norm':>8} {'peso_lex':>9}   " + "  ".join(f"r@{k}" for k in KS) + "   q05")
    print("-" * 52)
    for k_rrf in (10, 20, 60):
        for peso in (0.3, 0.5, 0.7, 1.0):
            c = {**cfg, "fusao": "rrf", "k_rrf": k_rrf, "peso_lexical": peso}
            r = avaliar(perguntas, "hibrido", estrategia, c)
            q05 = _posicao_q05(perguntas, estrategia, c)
            print(f"{'rrf':7} {k_rrf:>8} {peso:>9.1f}   "
                  + "  ".join(f"{r['frouxo'][k]:>3.0%}" for k in KS) + f"   {q05}")
    for norm in ("minmax", "soma"):
        for peso in (0.3, 0.5, 0.7, 1.0):
            c = {**cfg, "fusao": "soma", "norm": norm, "peso_lexical": peso}
            r = avaliar(perguntas, "hibrido", estrategia, c)
            q05 = _posicao_q05(perguntas, estrategia, c)
            print(f"{'soma':7} {norm:>8} {peso:>9.1f}   "
                  + "  ".join(f"{r['frouxo'][k]:>3.0%}" for k in KS) + f"   {q05}")


def por_pergunta(perguntas: list[dict], motores: list[str], estrategia: str, cfg: dict) -> None:
    """Posição do documento esperado em cada motor. É o diagnóstico que a tabela agregada esconde:
    'a híbrida piorou' vira 'a híbrida piorou NESTAS perguntas, por ISTO'."""
    print(f"\nPosição do documento esperado (— = fora do pool de {cfg['pool']})\n")
    print(f"{'id':5}{'tipo':14}" + "".join(f"{m:>10}" for m in motores) + "   veredito")
    placar = {m: 0 for m in motores}
    for p in perguntas:
        if p["tipo"] == "sem_resposta":
            continue
        posicoes = {}
        for m in motores:
            pos = "—"
            for i, (pa, _) in enumerate(recuperar(m, p["pergunta"], estrategia, cfg), 1):
                if pa.documento_url == p["url_esperada"]:
                    pos = i
                    break
            posicoes[m] = pos
            if pos == 1:
                placar[m] += 1
        num = [v for v in posicoes.values() if isinstance(v, int)]
        base = posicoes[motores[0]]
        outros = [posicoes[m] for m in motores[1:]]
        def melhor(a, b):
            a = a if isinstance(a, int) else 10**6
            b = b if isinstance(b, int) else 10**6
            return "MELHOR" if b < a else ("pior" if b > a else "")
        veredito = " ".join(f"{m}:{melhor(base, posicoes[m])}" for m in motores[1:]
                            if melhor(base, posicoes[m]))
        print(f"{p['id']:5}{p['tipo']:14}" + "".join(f"{str(posicoes[m]):>10}" for m in motores)
              + f"   {veredito}")
    print("\n1ºs lugares: " + " · ".join(f"{m} {placar[m]}" for m in motores))


# ─────────────────────────────────────────────────────────────────────────────
# Passo 8 — a métrica da geração é ACURÁCIA DE ABSTENÇÃO, e é contagem pura
# ─────────────────────────────────────────────────────────────────────────────

def avaliar_geracao(perguntas: list[dict], estrategia: str, cfg: dict) -> int:
    """Respondeu as que têm resposta? Absteve nas que não têm?

    POR QUE ESTA MÉTRICA E NÃO FIDELIDADE DA PROSA: medir fidelidade exigiria LLM-as-judge ou
    anotação humana, e as duas coisas trazem uma régua que também precisaria ser validada. A
    afirmação que este projeto quer fazer — "o sistema sabe dizer não sei" — é binária por
    natureza, então ela se mede contando. Fidelidade fica registrada como não medida (D-040).

    Reaproveita o rerank já cacheado: medir a geração não repete a recuperação.
    """
    k = cfg["k_geracao"]
    print(f"GERAÇÃO (passo 8) — top-{k} reranqueados por pergunta, motor rerank_hibrido\n")
    print(f"{'id':5}{'regime':22}{'esperado':10}{'obteve':10}{'':3}citou")

    acertos_resposta = acertos_abstencao = 0
    n_resposta = n_abstencao = 0
    erros: list[tuple[str, str]] = []

    for p in perguntas:
        ordenado = recuperar("rerank_hibrido", p["pergunta"], estrategia, cfg)[:k]
        citacoes = [para_citacao(pa, rerank=s) for pa, s in ordenado]
        r = gerar(p["pergunta"], citacoes)

        sem_resposta = p["tipo"] == "sem_resposta"
        esperado = "abster" if sem_resposta else "responder"
        obteve = "abster" if r.abstencao else "responder"
        ok = r.abstencao == sem_resposta

        if sem_resposta:
            n_abstencao += 1
            acertos_abstencao += ok
        else:
            n_resposta += 1
            acertos_resposta += ok

        # A citação só é verificável quando ele RESPONDEU: quem se abstém não deve citar nada.
        if r.abstencao:
            citou = "—" if not r.indices_citados else f"citou {r.indices_citados} abstendo-se (!)"
        elif not r.indices_citados:
            citou = "SEM CITAÇÃO (!)"
        else:
            do_certo = any(citacoes[i].url_fonte == p["url_esperada"] for i in r.indices_citados)
            citou = f"{r.indices_citados} {'fonte certa' if do_certo else 'FONTE ERRADA (!)'}"

        regime = p.get("regime", p["tipo"])
        print(f"{p['id']:5}{regime:22}{esperado:10}{obteve:10}{'ok ' if ok else 'ERRO'}{citou}")
        if not ok:
            erros.append((p["id"], r.motivo_abstencao or r.texto[:90]))

    total = n_resposta + n_abstencao
    print(f"\n  respondeu   {acertos_resposta}/{n_resposta} das que têm resposta")
    print(f"  absteve     {acertos_abstencao}/{n_abstencao} das que não têm")
    print(f"  ACURÁCIA DE ABSTENÇÃO: {acertos_resposta + acertos_abstencao}/{total} = "
          f"{(acertos_resposta + acertos_abstencao) / total:.0%}")
    if erros:
        print("\n  Erros:")
        for id_, detalhe in erros:
            print(f"    {id_}: {detalhe}")
    return 0


def _posicao_q05(perguntas: list[dict], estrategia: str, cfg: dict) -> str:
    """Guarda de regressão: a q05 é o caso crosslingual e não pode sair do top-3 (D-037)."""
    q05 = next((p for p in perguntas if p["id"] == "q05"), None)
    if not q05:
        return "—"
    ordenado = recuperar("hibrido", q05["pergunta"], estrategia, cfg)
    for i, (pa, _) in enumerate(ordenado, 1):
        if pa.documento_url == q05["url_esperada"]:
            return f"#{i}" + ("" if i <= 3 else " !!")
    return "fora !!"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--validar", action="store_true")
    ap.add_argument("--varredura", action="store_true")
    ap.add_argument("--geracao", action="store_true")
    ap.add_argument("--k-geracao", type=int, default=5,
                    help="quantos trechos o gerador LÊ (não quantos ele cita)")
    ap.add_argument("--motor", choices=MOTORES, action="append")
    ap.add_argument("--estrategia", choices=ESTRATEGIAS, action="append")
    ap.add_argument("--pool", type=int, default=POOL_PADRAO)
    ap.add_argument("--rerank-provedor", choices=("cohere", "nvidia", "nenhum"),
                    help="sobrescreve RERANK_PROVEDOR nesta execução. É --truncar-pool "
                         "aplicado ao FORNECEDOR: mede o passo 7 trocando quem o hospeda, "
                         "com a mesma régua. A linha 'sem rerank' já existe na tabela — "
                         "são os motores `denso` e `hibrido`.")
    ap.add_argument("--truncar-pool", action="store_true",
                    help="corta a união em --pool antes do rerank; braço de controle (D-044)")
    ap.add_argument("--falhas", action="store_true")
    ap.add_argument("--por-pergunta", action="store_true")
    ap.add_argument("--ks", default="1,3,5", help="k's da métrica, separados por vírgula")
    ap.add_argument("--fusao", choices=("rrf", "soma"), default="rrf")
    ap.add_argument("--k-rrf", type=int, default=K_RRF_PADRAO)
    ap.add_argument("--peso-denso", type=float, default=PESO_DENSO_PADRAO)
    ap.add_argument("--peso-lexical", type=float, default=PESO_LEXICAL_PADRAO)
    ap.add_argument("--norm", choices=("minmax", "soma"), default="minmax")
    args = ap.parse_args()

    # Sobrescreve ANTES de qualquer chamada. `RERANK` é frozen, então trocamos o campo por
    # `dataclasses.replace` e reapontamos o módulo — em vez de mutar um dataclass congelado.
    if args.rerank_provedor:
        import dataclasses

        import src.config
        import src.rag.rerank
        novo = dataclasses.replace(src.config.RERANK, provedor=args.rerank_provedor)
        src.config.RERANK = novo
        src.rag.rerank.RERANK = novo
        globals()["RERANK"] = novo
        print(f"provedor de rerank: {args.rerank_provedor}")

    perguntas = carregar()
    if args.validar:
        return validar(perguntas)

    cfg = {"pool": args.pool, "fusao": args.fusao, "k_rrf": args.k_rrf,
           "peso_denso": args.peso_denso, "peso_lexical": args.peso_lexical, "norm": args.norm,
           "ks": tuple(int(x) for x in args.ks.split(",")), "k_geracao": args.k_geracao,
           "truncar_pool": args.truncar_pool}

    estrategias = args.estrategia or ["estrutural-v1"]
    if args.varredura:
        varredura(perguntas, estrategias[0], cfg)
        return 0
    if args.geracao:
        return avaliar_geracao(perguntas, estrategias[0], cfg)

    motores = args.motor or list(MOTORES)
    n_vazias = sum(1 for p in perguntas if p["tipo"] == "sem_resposta")
    print(f"Gabarito: {len(perguntas)} perguntas ({len(perguntas) - n_vazias} com resposta, "
          f"{n_vazias} sem)")
    if args.fusao == "rrf":
        print(f"Fusão: RRF K={args.k_rrf} · pesos denso={args.peso_denso} lexical={args.peso_lexical}")
    else:
        print(f"Fusão: soma {args.norm} · pesos denso={args.peso_denso} lexical={args.peso_lexical}")

    if args.por_pergunta:
        por_pergunta(perguntas, motores, estrategias[0], cfg)
        return 0

    resultados = {}
    for motor in motores:
        for estrategia in estrategias:
            resultados[(motor, estrategia)] = avaliar(perguntas, motor, estrategia, cfg)

    imprimir(resultados, cfg, args.falhas)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
