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
    python scripts/varrer_classes.py --forca-bruta    # PROVA o que a tabela afirma (D-103)
    python scripts/varrer_classes.py --prioridades    # os 4 desenhos de `prioridade` (D-103)
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

    # ESTA CHECAGEM NÃO É UMA VERIFICAÇÃO, E DIZER QUE ERA FOI O DEFEITO (D-103).
    # A versão de 04/09 imprimia "D-101 verificado" quando `quad == "fora-do-funil" or ver` dava
    # falso para todas as linhas de `mudas`. Um code review provou que os DOIS disjuntos são
    # insatisfazíveis por construção: `mudas` é exatamente o conjunto sem detector, logo `ver` é
    # falso, logo `derivar_quadrante` devolve `prospect-de-evolucao`. A checagem nunca podia
    # falhar — e o `else` também rodava com `mudas` vazio, imprimindo "as 0 sem detector saem…".
    # É literalmente o que o docstring deste arquivo condena: *instrumento que parece medido*.
    #
    # O que se pode afirmar honestamente é a TAUTOLOGIA e a sua causa, que é o achado de verdade.
    incoerentes = [n for n, _, quad, ver in mudas if ver or quad == "fora-do-funil"]
    if incoerentes:
        print(f"\n*** INCOERÊNCIA: {', '.join(incoerentes)} tem zero detector e mesmo assim sai "
              f"verificada ou fora do funil. O invariante do classificador quebrou. ***")
    else:
        print(f"\nAs {len(mudas)} sem detector saem com `sinal_verificado=False` — o que é "
              f"TAUTOLÓGICO,\ne é esse o ponto: `pontos == 0` É a definição de `non-AI` neste "
              f"classificador, então\n`non-AI` CONSTATADO não existe e `fora-do-funil` é "
              f"inalcançável. Ver D-103.")


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


def forca_bruta() -> None:
    """A PROVA DA AFIRMAÇÃO QUE ESTE SCRIPT JÁ IMPRIMIA SEM PROVAR — D-103, paga em 05/09.

    `tabela()` termina dizendo que *"`non-AI` CONSTATADO não existe e `fora-do-funil` é
    inalcançável"*. Isso é uma afirmação sobre TODO o espaço de entradas, e a tabela das 30
    não a sustenta: 30 empresas são 30 pontos, não uma prova de inalcançabilidade. A força
    bruta que D-103 rodou ficou num heredoc e não entrou no repositório — **número sem comando
    é afirmação, não medição** (D-102), e a entrada que mais insiste nisso é a que o repetiu.

    O QUE ELA VARRE: `(autopilot, modelo_entrega, dado_proprietário, vocab_técnico, marcadores
    nos documentos, marcadores no trecho)` nos **dois braços da rubrica**, exercitando
    `classifier.node` de verdade — não uma reimplementação da aritmética, que é o modo de a
    força bruta concordar consigo mesma.

    UMA ARMADILHA MEDIDA NO CAMINHO: as frases sintéticas precisam ter **mais de 40 caracteres**,
    porque `extractor.frases` descarta o que for menor. Com frases curtas, `n_prof` vale 0 em
    silêncio e a varredura cobre menos do que anuncia — a primeira versão desta função caiu
    nisso e "verificou" o braço em degraus sem nunca alcançar o degrau 2a.
    """
    from itertools import product

    from src.state import (Afirmacao, DocumentoRef, Evidencia, PerfilStartup, StartupRef,
                           derivar_quadrante)

    def doc(i, texto):
        return DocumentoRef(documento_id=i, tipo="site", titulo=f"d{i}",
                            url_fonte=f"https://exemplo.test/{i}", conteudo_texto=texto)

    def af(trecho, i=900):
        return Afirmacao(texto=trecho, evidencias=[Evidencia.de_documento(doc(i, trecho), trecho)])

    def montar(autopilot, entrega, dado, tecnico, n_prof, n_mat):
        modelo = (af("entrega em modo autopilot, com o resultado pronto para o cliente")
                  if autopilot else
                  af("posicionamento de copilot: o time do cliente usa a ferramenta")
                  if entrega else None)
        tecnicos = ([af(f"stack tecnica declarada: {' '.join(classifier.PROFUNDOS[:n_mat])}", 901)]
                    if tecnico else [])
        perfil = PerfilStartup(
            startup_id=1, nome="Fixture", modelo_entrega=modelo,
            sinais_dado_proprietario=[af("base de dados propria e rotulada internamente", 902)]
                                     if dado else [],
            sinais_otimizacao_tecnica=tecnicos)
        # > 40 caracteres por frase, senão `extractor.frases` as descarta e `n_prof` vira 0.
        corpo = ". ".join(f"a plataforma de producao da empresa opera {m} em escala de cluster"
                          for m in classifier.PROFUNDOS[:n_prof]) or "texto sem marcador algum"
        return {"perfil": perfil,
                "startup": StartupRef(startup_id=1, nome="Fixture", documentos=[doc(1, corpo + ".")])}

    print("FORÇA BRUTA SOBRE `classifier.node` — os dois braços da rubrica\n")
    todos = {}
    for em_degraus in (False, True):
        original = classifier.RUBRICA_EM_DEGRAUS
        classifier.RUBRICA_EM_DEGRAUS = em_degraus
        vistos, n = {}, 0
        try:
            for a, e, d, t, np_, nm in product([False, True], [False, True], [False, True],
                                               [False, True], range(6), range(6)):
                if (a and not e) or (nm and not t):
                    continue     # autopilot exige modelo_entrega; sem afirmação técnica não há trecho
                n += 1
                diag = classifier.node(montar(a, e, d, t, np_, nm))["diagnostico"]
                vistos.setdefault((diag.classe, diag.sinal_verificado, diag.quadrante),
                                  (a, e, d, t, np_, nm))
        finally:
            classifier.RUBRICA_EM_DEGRAUS = original
        todos.update(vistos)
        rotulo = "RUBRICA_EM_DEGRAUS=True (o braço de D-060)" if em_degraus else "aritmética de PRODUÇÃO"
        print(f"── {rotulo} — {n} combinações")
        for (classe, ver, quad), args in sorted(vistos.items()):
            print(f"   classe={classe:<11} verificado={str(ver):<5} {quad:<21} "
                  f"testemunha (a,e,d,t,np,nm)={args}")
        print()

    quadrantes = sorted({q for _, _, q in todos})
    viola = [(c, v, q) for c, v, q in todos if (c == "non-AI") != (not v)]
    print(f"quadrantes alcançáveis:              {quadrantes}")
    print(f"`fora-do-funil` alcançável?          {'SIM' if 'fora-do-funil' in quadrantes else 'NÃO'}")
    print(f"existe (`non-AI`, verificado=True)?  "
          f"{'SIM -> ' + str(viola) if viola else 'NÃO'}")
    print(f"`sinal_verificado` == `classe != non-AI` em TODO o espaço?  "
          f"{'SIM' if not viola else 'NÃO'}")

    livre = sorted({derivar_quadrante(c, m, v)
                    for c in ("AI-native", "AI-enabled", "non-AI")
                    for m in ("alta", "media", "baixa") for v in (True, False)})
    print(f"\nCONTRAPROVA — a função `derivar_quadrante` isolada, espaço livre: {livre}")
    print("A célula da matriz de `contexto/02` §4 EXISTE na função; o que nenhum caminho de")
    print("`classifier.node` produz é a ENTRADA que a alcança. É por isso que o ramo fica.")


def prioridades() -> None:
    """A TABELA QUE DECIDIU TIRAR O REBAIXAMENTO POR NÃO-ELEGIBILIDADE — D-103, sem comando.

    O segundo achado de D-103 se apoia numa distribuição sobre as 30 sob quatro desenhos, e a
    entrada a publicou sem instrumento. Ela é a razão de `prioridade` — um dos 7 campos
    obrigatórios do TAPI — ter só um dos dois rebaixamentos: com os dois, a JetBov (único
    `sweet-spot` da base) empatava com a SunnyHUB (energia solar) no piso.

    Zero API: `_prioridade` é função pura sobre `(quadrante, confianca, sinal_verificado)`.
    """
    from src.agents import briefing, evidence_validator
    from src.agents.recommendation import _prioridade

    desenhos = {"antes de 04/09 (nenhum rebaixamento)": (False, False),
                "os dois rebaixamentos": (True, True),
                "só verificação (o escolhido, D-103)": (True, False),
                "só elegibilidade": (False, True)}

    linhas = []
    for i, f in enumerate(regua.carregar()):
        startup = regua.como_startup(f, i)
        perfil = extractor.node({"startup": startup})["perfil"]
        diag = classifier.node({"perfil": perfil, "startup": startup})["diagnostico"]
        estado = {"perfil": perfil, "diagnostico": diag, "startup": startup}
        diag = evidence_validator.node(estado).get("diagnostico", diag)
        eleg = briefing.node_analise({"startup": startup, "perfil": perfil})["elegibilidade"]
        linhas.append((f["nome"], diag, eleg.elegivel))

    print(f"{len(linhas)} empresas · `_prioridade` sob os quatro desenhos de D-103\n")
    print(f"{'desenho':38} {'alta':>5} {'media':>6} {'baixa':>6}   {'JetBov':>7} {'SunnyHUB':>9}")
    print("-" * 80)
    for nome, (usa_ver, usa_eleg) in desenhos.items():
        conta = {"alta": 0, "media": 0, "baixa": 0}
        por_empresa = {}
        for empresa, diag, elegivel in linhas:
            p = _prioridade(diag.quadrante, diag.confianca,
                            sinal_verificado=(diag.sinal_verificado if usa_ver else True))
            if usa_eleg and not elegivel:
                p = "baixa"
            conta[p] += 1
            por_empresa[empresa] = p
        print(f"{nome:38} {conta['alta']:>5} {conta['media']:>6} {conta['baixa']:>6}   "
              f"{por_empresa['JetBov']:>7} {por_empresa['SunnyHUB']:>9}")
    print("\nLEIA as duas últimas colunas. A JetBov é o único `sweet-spot` das 30; a SunnyHUB é")
    print("energia solar. Achatar as duas no piso destrói o que a regra 1 de `contexto/03` §4")
    print("existe para produzir — *a prioridade sai do GAP, não do rótulo*.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--custo-desenhos", action="store_true",
                    help="o que cada conserto de P-24 custa na régua de `classe`")
    ap.add_argument("--forca-bruta", action="store_true",
                    help="PROVA a inalcançabilidade de `fora-do-funil` que a tabela afirma (D-103)")
    ap.add_argument("--prioridades", action="store_true",
                    help="a distribuição de `prioridade` sob os 4 desenhos de D-103")
    args = ap.parse_args()

    if args.forca_bruta:
        forca_bruta()
    elif args.prioridades:
        prioridades()
    elif args.custo_desenhos:
        custo_dos_desenhos(regua.carregar())
    else:
        tabela(regua.carregar())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
