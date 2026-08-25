"""Na stack pós-EOL, `rerank_hibrido` bate `rerank_denso` em e@5 (100% vs 95%). QUAL pergunta?

O braço de controle já disse ONDE nasce a vantagem: com `--truncar-pool` os dois voltam a 95%,
então ela vem do POOL MAIOR — dos candidatos que só o braço lexical traz, além do top-20 da
fusão — e não da reordenação da fusão. Falta o diagnóstico: qual pergunta, e por quê.

Isso importa porque, sem ele, D-037 ganharia um argumento vivo baseado num número que ninguém
sabe explicar — que é o modo de falha que a revisão da sessão 03 encontrou duas vezes (o IDF de
D-036 e a q17 de D-040).

POR QUE NÃO `--por-pergunta`: ele reranqueia os dois pools nas 24 perguntas (81 chamadas). Aqui
a condição NECESSÁRIA para uma pergunta produzir a diferença é a âncora estar na CAUDA da união
(além do top-20 da fusão). Isso se calcula com o braço denso + o lexical (24 chamadas, o lexical
é local), e só as candidatas sobreviventes precisam de rerank.

Uso:  python scripts/auditoria/quem_o_lexico_compra.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAIZ))

import yaml

from src.rag.busca import buscar_denso_bruto
from src.rag.lexical import buscar_lexical_bruto
from src.rag.fusao import fundir_rrf
from src.rag.rerank import logits_de
from src.rag.pipeline import K_RRF_PADRAO, PESO_DENSO_PADRAO, PESO_LEXICAL_PADRAO, POOL_PADRAO

ESTRATEGIA = "estrutural-v1"
chamadas = 0


def tem_ancora(passagem, pergunta: dict) -> bool:
    """Mesmo critério ESTRITO do harness: o chunk contém a frase-âncora."""
    ancora = pergunta.get("frase_ancora")
    return bool(ancora) and ancora.lower() in passagem.texto_indexado.lower()


def main() -> int:
    global chamadas
    perguntas = yaml.safe_load((RAIZ / "data/avaliacao/gabarito.yaml").read_text())
    com_resposta = [p for p in perguntas if p["tipo"] != "sem_resposta"]
    print(f"{len(com_resposta)} perguntas com resposta · pool={POOL_PADRAO} · "
          f"RRF K={K_RRF_PADRAO} pesos {PESO_DENSO_PADRAO}/{PESO_LEXICAL_PADRAO}\n")

    candidatas = []
    for p in com_resposta:
        denso = buscar_denso_bruto(p["pergunta"], k=POOL_PADRAO, estrategia=ESTRATEGIA)
        chamadas += 1
        lexical = buscar_lexical_bruto(p["pergunta"], k=POOL_PADRAO, estrategia=ESTRATEGIA)
        fundido = fundir_rrf({"denso": denso, "lexical": lexical},
                             {"denso": PESO_DENSO_PADRAO, "lexical": PESO_LEXICAL_PADRAO},
                             K_RRF_PADRAO)

        ids_denso = {pa.chunk_id for pa, _ in denso}
        cabeca = {pa.chunk_id for pa, _ in fundido[:POOL_PADRAO]}
        cauda = [(pa, s) for pa, s in fundido[POOL_PADRAO:]]

        # A âncora está na CAUDA da união e FORA do pool denso? Só aí a não-truncagem pode
        # comprar alguma coisa que o rerank sobre o denso puro não teria.
        ancora_na_cauda = [pa for pa, _ in cauda if tem_ancora(pa, p)]
        ancora_no_denso = any(tem_ancora(pa, p) for pa, _ in denso)

        marca = ""
        if ancora_na_cauda and not ancora_no_denso:
            marca = "  <== CANDIDATA (âncora só na cauda da união)"
            candidatas.append((p, denso, fundido))
        elif ancora_na_cauda:
            marca = "  (âncora na cauda, mas também no pool denso)"
        print(f"  {p['id']}  união={len(fundido):>2}  cauda={len(cauda):>2}  "
              f"âncora_no_denso={'sim' if ancora_no_denso else 'NÃO'}{marca}")

    print(f"\n{len(candidatas)} candidata(s). Reranqueando só elas.\n")

    for p, denso, fundido in candidatas:
        for rotulo, pool in (("rerank_denso  ", [pa for pa, _ in denso]),
                             ("rerank_hibrido", [pa for pa, _ in fundido])):
            logits = logits_de(p["pergunta"], pool)
            chamadas += -(-len(pool) // 32)
            ordenado = sorted(pool, key=lambda pa: -logits[pa.chunk_id])
            pos = next((i + 1 for i, pa in enumerate(ordenado) if tem_ancora(pa, p)), None)
            print(f"  {p['id']} {rotulo}: pool={len(pool):>2}  "
                  f"âncora em {pos if pos else 'AUSENTE'}  "
                  f"{'-> dentro do top-5' if pos and pos <= 5 else '-> fora do top-5'}")
        print(f"      pergunta: {p['pergunta']}")
        print(f"      âncora:   {p['frase_ancora'][:100]}")
        print(f"      esperado: {p['url_esperada']}\n")

    print(f"{'=' * 78}\nchamadas de API gastas: {chamadas}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
