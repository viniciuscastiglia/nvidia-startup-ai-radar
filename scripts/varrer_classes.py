"""O veredito de CLASSE das 30 empresas, numa tabela. Zero API, poucos segundos.

POR QUE ISTO EXISTE (D-098)
----------------------------
É o irmão de `varrer_elegibilidade.py` (D-094) para o outro eixo do Classifier, e nasce da
mesma regra: D-083 diz "rode o sistema"; o corolário é **rode-o sobre a base INTEIRA, não
sobre uma amostra**. Ler briefing é amostragem — dá para ler três empresas, não trinta.

O que ele tornou visível foi a P-24: `pontos == 0 -> non-AI` transformava **silêncio da
extração** em **afirmação sobre a empresa**, e `non-AI` levava a `fora-do-funil` em
`derivar_quadrante`, que levava a `recomendacoes: []` em `recommendation.py`. A coluna `ADT`
mostra qual dos três detectores disparou, então a linha `---` era literalmente "não achei nada"
sendo reportada ao gerente como "esta empresa não tem IA".

A coluna `dores` é o que fechava o argumento: as empresas com `---` **têm dores de IA extraídas
pelo mesmo Extractor**. O sistema encontrava o sinal e depois dizia que não existe.

DE DIAGNÓSTICO A VERIFICAÇÃO — 04/09 tarde (D-101)
---------------------------------------------------
A P-24 foi consertada, e este script mudou de papel junto: ele **lê o quadrante real** em vez
de afirmar a consequência antiga. Era o próximo defeito da mesma família — um instrumento que
descreve um sistema que não existe mais é pior que instrumento nenhum, porque parece medido.
A coluna `quadrante` é a verificação: com `---` na coluna `ADT`, o esperado hoje é
`prospect-de-evolucao` com `sinal_verificado=False`, e **não** `fora-do-funil`.

O QUE ELE NÃO É
---------------
Não é régua. Régua é `avaliar_agentes.py`, que tem gabarito e mede 8 fixtures. Aqui não há
resposta certa declarada: é uma tabela para um humano LER, sobre as 30. As 22 startups novas
entraram como DADO, sem gabarito (D-062), justamente para não calibrar contra o próprio
julgamento — então elas aparecem aqui e **não** aparecem em placar nenhum.

USO
---
    python scripts/varrer_classes.py                  # a tabela das 30
    python scripts/varrer_classes.py --custo-desenhos # o que cada conserto custa NA RÉGUA
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import avaliar_agentes as regua  # noqa: E402
from src.agents import classifier, extractor  # noqa: E402


def _detectores(perfil):
    """Os três sinais do eixo 1, na ordem em que `classifier.node` os lê."""
    autopilot = bool(perfil.modelo_entrega
                     and "autopilot" in perfil.modelo_entrega.texto.lower())
    return autopilot, bool(perfil.sinais_dado_proprietario), bool(perfil.sinais_otimizacao_tecnica)


def tabela(fixtures) -> None:
    contagem = {"AI-native": 0, "AI-enabled": 0, "non-AI": 0}
    linhas = []
    for i, f in enumerate(fixtures):
        startup = regua.como_startup(f, i)
        perfil = extractor.node({"startup": startup})["perfil"]
        diag = classifier.node({"perfil": perfil, "startup": startup})["diagnostico"]
        a, d, t = _detectores(perfil)
        contagem[diag.classe] += 1
        linhas.append((f["nome"], diag.classe,
                       f"{'A' if a else '-'}{'D' if d else '-'}{'T' if t else '-'}",
                       len(perfil.dores_observadas), diag.maturidade_stack,
                       diag.quadrante, diag.sinal_verificado))

    print(f"{len(fixtures)} empresas · detectores: A=autopilot D=dado_proprietário T=vocab_técnico\n")
    print(f"{'empresa':22} {'classe':12} {'ADT':5} {'dores':>5}  {'stack':6} quadrante")
    print("-" * 84)
    for nome, classe, det, nd, mat, quad, ver in sorted(linhas, key=lambda x: (x[1], x[0])):
        marca = "  <-- ZERO SINAL" if det == "---" else ""
        # `?` é o mesmo símbolo que o briefing usa para requisito não verificado. Ver D-101.
        selo = "" if ver else " ?"
        print(f"{nome:22} {classe:12} {det:5} {nd:>5}  {mat:6} {quad}{selo}{marca}")

    print(f"\nAI-native {contagem['AI-native']} · AI-enabled {contagem['AI-enabled']} · "
          f"non-AI {contagem['non-AI']}")

    mudas = [(n, nd, quad, ver) for n, c, det, nd, _, quad, ver in linhas if det == "---"]
    print(f"\n{len(mudas)} empresa(s) com ZERO detector — e `non-AI` sai daí, não de evidência.")
    com_dor = sorted([m for m in mudas if m[1] > 0], key=lambda x: -x[1])
    if com_dor:
        print("Destas, as que TÊM dores de IA extraídas pelo mesmo Extractor:")
        for n, nd, quad, ver in com_dor:
            selo = "sinal NÃO verificado" if not ver else "sinal verificado"
            print(f"   {n:22} {nd} dor(es) -> non-AI ({selo}) -> {quad}")
        print("\nLEIA a tabela. `non-AI` aqui significa 'não achei sinal', e o briefing o")
        print("apresentava ao gerente como 'esta empresa não tem IA'. São coisas diferentes —")
        print("é a mesma distinção que `Elegibilidade` já faz entre `x` (provado) e `?`.")

    # A VERIFICAÇÃO DE D-101, e ela falha ALTO: uma empresa sem detector nenhum não pode voltar
    # a `fora-do-funil`, porque isso seria o sistema afirmando de novo o que não constatou.
    regressao = [n for n, _, quad, ver in mudas if quad == "fora-do-funil" or ver]
    if regressao:
        print(f"\n*** REGRESSÃO DE D-101: {', '.join(regressao)} tem zero detector e voltou a "
              f"ser cortada do funil (ou marcada como verificada). ***")
    else:
        print(f"\nD-101 verificado: as {len(mudas)} sem detector saem com `sinal_verificado=False` "
              f"e NENHUMA foi cortada do funil por silêncio da extração.")


def custo_dos_desenhos(fixtures) -> None:
    """Quanto cada conserto possível de P-24 custa NA RÉGUA de `classe`.

    Existe porque em 04/09 a afirmação "consertar P-24 derruba classe de 3/7 para 2/7" foi
    feita por INFERÊNCIA e apresentada como propriedade do problema. Ela vale para um dos
    desenhos e não para o outro. Este braço mede em vez de inferir.
    """
    hoje = desenho_a = 0
    linhas = []
    for i, f in enumerate(fixtures):
        esp = (f.get("gabarito") or {}).get("classe")
        if esp is None or isinstance(esp, list):
            continue                       # sem gabarito, ou ambígua: fora do denominador
        startup = regua.como_startup(f, i)
        perfil = extractor.node({"startup": startup})["perfil"]
        diag = classifier.node({"perfil": perfil, "startup": startup})["diagnostico"]
        zero_sinal = not any(_detectores(perfil))
        ok = diag.classe == esp
        hoje += ok
        # Desenho A: `pontos == 0` deixa de emitir `non-AI` e passa a emitir rótulo próprio,
        # então nunca mais casa um gabarito `non-AI`.
        desenho_a += ok and not zero_sinal
        linhas.append((f["nome"], esp, diag.classe, zero_sinal, ok))

    print(f"{'empresa':16} {'gabarito':11} {'sistema':11} {'zero sinal':>10} {'acerta':>7}")
    print("-" * 60)
    for n, e, o, z, ok in linhas:
        print(f"{n:16} {e:11} {o:11} {str(z):>10} {str(ok):>7}")

    n = len(linhas)
    print(f"\nDESENHO A — `pontos == 0` vira rótulo próprio (ex.: `indeterminado`)")
    print(f"   classe {hoje}/{n}  ->  {desenho_a}/{n}   (o gabarito `non-AI` deixa de ser casável)")
    print(f"\nDESENHO B — o rótulo fica; muda só a CONSEQUÊNCIA (o corte do funil)")
    print(f"   classe {hoje}/{n}  ->  {hoje}/{n}   (a régua de `classe` não se move)")
    print("\nO trade-off NÃO é propriedade do problema: ele existe no desenho A e não no B.")
    print("O que o desenho B custa está em OUTRO lugar — o que entra no funil —, e isso")
    print("nenhuma régua de `classe` mede. O desenho B entrou em 04/09 — ver D-101.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--custo-desenhos", action="store_true",
                    help="o que cada conserto de P-24 custa na régua de `classe`")
    args = ap.parse_args()

    fixtures = regua.carregar()
    if args.custo_desenhos:
        custo_dos_desenhos(fixtures)
    else:
        tabela(fixtures)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
