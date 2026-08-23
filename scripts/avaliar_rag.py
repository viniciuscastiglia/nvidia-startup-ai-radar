"""Passo 9 do pipeline RAG do TAPI: avaliação de qualidade. Ver D-030 e D-031.

O TAPI chama este passo de "o mais ignorado, e o que mais separa nível 2 de nível 4 no
critério 2". Ele existe desde a sessão 02, e não da 04, por um motivo específico: a sessão 02
decide chunking e dimensão, e sem instrumento essas decisões seriam argumento em vez de
medida (D-031).

AS TRÊS MÉTRICAS
----------------
1. **recall@k frouxo** — algum dos k primeiros chunks veio do documento esperado.
   É a métrica principal porque SOBREVIVE a mudança de chunking: é o que permite comparar
   'estrutural-v1' com 'fixo-800' na mesma régua (D-030).

2. **recall@k estrito** — além do documento certo, o chunk contém `frase_ancora`.
   Um documento pode ser recuperado pelo motivo errado: a página do TensorRT-LLM tem 27 mil
   caracteres e recuperar QUALQUER pedaço dela não prova que o pedaço responde a pergunta.

3. **abstenção** — nas perguntas `sem_resposta`, o score do primeiro colocado.
   Não é recall: o acerto aqui é NÃO responder. A métrica é a margem entre o melhor score de
   uma pergunta sem resposta e o pior score de uma pergunta com resposta. Se as duas
   distribuições se sobrepõem, nenhum limiar separa e o sistema não tem como dizer "não sei".

`--validar` NÃO MEDE NADA, e é o modo que deveria rodar primeiro: confere que toda
`frase_ancora` ocorre no corpus e ocorre em uma só tecnologia. Um gabarito com âncora ausente
mede o recuperador contra uma resposta que não existe — e o erro parece do recuperador.

USO
---
    python scripts/avaliar_rag.py --validar
    python scripts/avaliar_rag.py                              # compara as duas estratégias
    python scripts/avaliar_rag.py --estrategia estrutural-v1 -k 5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import conectar
from src.rag.busca import buscar_denso

GABARITO = Path(__file__).resolve().parent.parent / "data" / "avaliacao" / "gabarito.yaml"
ESTRATEGIAS = ("estrutural-v1", "fixo-800")


def carregar() -> list[dict]:
    return yaml.safe_load(GABARITO.read_text())


# ─────────────────────────────────────────────────────────────────────────────

def validar(perguntas: list[dict]) -> int:
    """A âncora existe no corpus? E é exclusiva de uma tecnologia?"""
    print("Validando o gabarito contra o corpus (não mede recuperação)\n")
    problemas = 0
    with conectar() as cx, cx.cursor() as cur:
        for p in perguntas:
            if p["tipo"] == "sem_resposta":
                if p["url_esperada"] is not None:
                    print(f"  {p['id']}: tipo sem_resposta mas tem url_esperada"); problemas += 1
                else:
                    print(f"  {p['id']}: sem_resposta — OK, nada a verificar")
                continue

            cur.execute(
                """SELECT DISTINCT tecnologia, documento_url FROM chunks_nvidia
                   WHERE estrategia = 'estrutural-v1' AND texto ILIKE %s""",
                (f"%{p['frase_ancora']}%",),
            )
            achados = cur.fetchall()
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

def avaliar(perguntas: list[dict], estrategia: str, k: int) -> dict:
    com_resposta = [p for p in perguntas if p["tipo"] != "sem_resposta"]
    sem_resposta = [p for p in perguntas if p["tipo"] == "sem_resposta"]

    acertos_frouxo, acertos_estrito, por_tipo, falhas = 0, 0, {}, []
    piores_scores = []

    for p in com_resposta:
        citacoes = buscar_denso(p["pergunta"], k=k, estrategia=estrategia)
        do_documento = [c for c in citacoes if c.url_fonte == p["url_esperada"]]
        frouxo = bool(do_documento)
        estrito = any(p["frase_ancora"].lower() in c.trecho.lower() for c in do_documento)

        acertos_frouxo += frouxo
        acertos_estrito += estrito
        t = por_tipo.setdefault(p["tipo"], [0, 0])
        t[0] += frouxo
        t[1] += 1
        if frouxo:
            piores_scores.append(max(c.score_denso for c in do_documento))
        else:
            posicao = "—"
            falhas.append((p["id"], p["tipo"], p["tecnologia_esperada"],
                           citacoes[0].tecnologia if citacoes else posicao))

    melhor_sem_resposta = []
    for p in sem_resposta:
        citacoes = buscar_denso(p["pergunta"], k=k, estrategia=estrategia)
        if citacoes:
            melhor_sem_resposta.append(citacoes[0].score_denso)

    return {
        "n": len(com_resposta),
        "frouxo": acertos_frouxo / len(com_resposta),
        "estrito": acertos_estrito / len(com_resposta),
        "por_tipo": por_tipo,
        "falhas": falhas,
        "pior_acerto": min(piores_scores) if piores_scores else None,
        "melhor_sem_resposta": max(melhor_sem_resposta) if melhor_sem_resposta else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--validar", action="store_true")
    ap.add_argument("--estrategia", choices=ESTRATEGIAS)
    ap.add_argument("-k", type=int, default=5)
    args = ap.parse_args()

    perguntas = carregar()
    if args.validar:
        return validar(perguntas)

    alvos = [args.estrategia] if args.estrategia else list(ESTRATEGIAS)
    print(f"Gabarito: {len(perguntas)} perguntas · recuperação DENSA pura · k = {args.k}\n")
    print(f"{'estratégia':16} {'recall@k':>9} {'estrito':>8}   por tipo")

    resultados = {}
    for estrategia in alvos:
        r = avaliar(perguntas, estrategia, args.k)
        resultados[estrategia] = r
        tipos = " · ".join(f"{t}: {v[0]}/{v[1]}" for t, v in sorted(r["por_tipo"].items()))
        print(f"{estrategia:16} {r['frouxo']:>8.0%} {r['estrito']:>8.0%}   {tipos}")

    for estrategia, r in resultados.items():
        if r["falhas"]:
            print(f"\nFalhas de {estrategia} (recall@{args.k} frouxo):")
            for id_, tipo, esperado, veio in r["falhas"]:
                print(f"  {id_} [{tipo}] esperava {esperado!r}, 1º colocado foi {veio!r}")

    print("\nABSTENÇÃO — o acerto nas perguntas sem resposta é NÃO responder:")
    for estrategia, r in resultados.items():
        pior, melhor_vazio = r["pior_acerto"], r["melhor_sem_resposta"]
        if pior is None or melhor_vazio is None:
            continue
        margem = pior - melhor_vazio
        veredito = ("separável: um limiar entre os dois abstém sem perder acerto"
                    if margem > 0 else
                    "NÃO separável: as distribuições se sobrepõem, nenhum limiar funciona")
        print(f"  {estrategia:16} pior acerto {pior:.4f} · melhor sem-resposta {melhor_vazio:.4f} "
              f"· margem {margem:+.4f}\n{' ' * 20}{veredito}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
