"""O que o filtro do Inception NÃO enxerga, e o que custa mostrar tudo a ele. Zero API.

POR QUE ISTO EXISTE (D-102)
----------------------------
Em 04/09 quatro medições sobre a P-23 e a P-12 foram feitas em scripts descartáveis, e
DUAS delas viraram número em `decisoes.md` sem instrumento que as reproduza. É o defeito
que a própria sessão da manhã já tinha cometido e registrado — e a sessão da tarde o
repetiu. Um número no log sem comando que o derrube é afirmação, não medição.

AS TRÊS PERGUNTAS QUE ELE RESPONDE, e nenhuma é régua:

1. **Cobertura (P-23).** `briefing.elegibilidade()` varre `perfil.afirmacoes[*].evidencias
   [*].trecho`, não o documento. Quanto do texto ele nunca lê? Conta trechos ÚNICOS: uma
   frase que sustenta duas afirmações não amplia a cobertura, e somar bruto infla o número.

2. **O custo do conserto óbvio (P-23).** Varrer `conteudo_texto` inteiro. O resultado não é
   só "mais recusas": ele **quebra `_fala_de_terceiro` por construção**, porque o veto exige
   que TODA ocorrência do termo caia em frase com marcador (`all()`). Cada caractere a mais
   é outra chance de o quantificador falhar. `--terceiro` mostra o mecanismo frase a frase.

3. **`PROFUNDOS` e as datas (P-12, P-11).** Quantos marcadores de profundidade cada fixture
   de gabarito tem nos documentos INTEIROS, e quantos documentos têm `data_publicacao` —
   que é a metade desligada da regra 2/3 do Evidence Validator.

O QUE ELE NÃO É: régua. Não há resposta certa declarada, e o julgamento de quais recusas
novas são falso positivo é de quem LÊ a frase impressa. Ver `avaliar_agentes.py --exclusoes`,
que é a régua do filtro, com os dois lados e gabarito.

USO
---
    python scripts/medir_cobertura.py              # as três medições
    python scripts/medir_cobertura.py --terceiro   # por que o conserto óbvio quebra o veto
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import avaliar_agentes as regua  # noqa: E402
from src.agents import briefing, classifier, extractor  # noqa: E402
from src.state import Afirmacao, Evidencia  # noqa: E402


class _PerfilAmplo:
    """Duck-type mínimo para `elegibilidade()`: uma afirmação carregando o documento INTEIRO.

    `elegibilidade()` usa só `.afirmacoes` e `.sinais_otimizacao_tecnica`, então não é preciso
    construir um `PerfilStartup` — e construir um daria a impressão de que o Extractor produziu
    isto, que é o oposto do que se quer medir.
    """

    def __init__(self, startup, perfil):
        self.afirmacoes = [Afirmacao(texto="documento inteiro", evidencias=[
            Evidencia.de_documento(d, d.conteudo_texto) for d in startup.documentos])]
        self.sinais_otimizacao_tecnica = perfil.sinais_otimizacao_tecnica


def medir(fixtures) -> None:
    chars_doc = chars_ev = chars_bruto = 0
    docs_total = docs_sem_data = 0
    hoje, amplo = set(), {}
    por_empresa = []

    for i, f in enumerate(fixtures):
        startup = regua.como_startup(f, i)
        perfil = extractor.node({"startup": startup})["perfil"]

        cd = sum(len(d.conteudo_texto) for d in startup.documentos)
        trechos = [e.trecho for a in perfil.afirmacoes for e in a.evidencias]
        ce = sum(map(len, set(trechos)))          # ÚNICOS: repetido não amplia cobertura
        chars_doc += cd
        chars_ev += ce
        chars_bruto += sum(map(len, trechos))
        por_empresa.append((f["nome"], cd, ce, ce / cd if cd else 0))

        docs_total += len(startup.documentos)
        docs_sem_data += sum(1 for d in startup.documentos if not d.data_publicacao)

        if not briefing.elegibilidade(startup, perfil).elegivel:
            hoje.add(f["nome"])
        e_amplo = briefing.elegibilidade(startup, _PerfilAmplo(startup, perfil))
        if not e_amplo.elegivel:
            amplo[f["nome"]] = [m.split(":")[0] for m in e_amplo.motivos_exclusao]

    print("1. COBERTURA DE `elegibilidade()` SOBRE O TEXTO (P-23)\n")
    print(f"   caracteres nos documentos          {chars_doc:>9,}")
    print(f"   trechos de evidência, ÚNICOS       {chars_ev:>9,}   {chars_ev / chars_doc:6.1%}")
    print(f"   (soma BRUTA, com repetição)        {chars_bruto:>9,}   {chars_bruto / chars_doc:6.1%}"
          f"  <- não é cobertura")
    piores = sorted(por_empresa, key=lambda x: x[3])
    print("   pior cobertura: " + " · ".join(f"{n} {r:.1%}" for n, _, _, r in piores[:3]))
    print("   melhor:         " + " · ".join(f"{n} {r:.1%}" for n, _, _, r in piores[-3:]))

    print("\n2. O CUSTO DO CONSERTO ÓBVIO — varrer `conteudo_texto` inteiro (P-23)\n")
    print(f"   HOJE  ({len(hoje):2}): {', '.join(sorted(hoje))}")
    print(f"   AMPLO ({len(amplo):2}): {', '.join(sorted(amplo))}")
    novas = sorted(set(amplo) - set(hoje))
    print(f"\n   {len(novas)} recusa(s) NOVA(S) — LEIA a frase de cada uma com `--terceiro`:")
    for n in novas:
        print(f"      {n:20} {', '.join(amplo[n])}")
    sumiram = sorted(set(hoje) - set(amplo))
    print(f"   recusas que SUMIRIAM: {sumiram or 'nenhuma'}  (varrer mais nunca remove exclusão)")

    print("\n3. `PROFUNDOS` NAS FIXTURES DE GABARITO (P-12) E AS DATAS (P-11)\n")
    print(f"   {'fixture':20} {'gabarito':22} marcadores distintos nos DOCUMENTOS INTEIROS")
    zeros = 0
    for i, f in enumerate(fixtures):
        esp = (f.get("gabarito") or {}).get("classe")
        if esp is None:
            continue
        startup = regua.como_startup(f, i)
        texto = " ".join(d.conteudo_texto.lower() for d in startup.documentos)
        quais = [m for m in classifier.PROFUNDOS if m in texto]
        zeros += not quais
        print(f"   {f['nome']:20} {str(esp):22} {len(quais)}  {quais or ''}")
    print(f"\n   {zeros} de {sum(1 for f in fixtures if (f.get('gabarito') or {}).get('classe'))}"
          f" com ZERO — o degrau `2a` exige {classifier.MARCADORES_PARA_PROFUNDIDADE} distintos")
    print(f"   `data_publicacao` ausente em {docs_sem_data} de {docs_total} documentos "
          f"({docs_sem_data / docs_total:.1%}) — `_recente(None)` é False, então metade da "
          f"regra 2/3\n   do Evidence Validator nunca roda e `alta` é inalcançável por falta de "
          f"DADO, não por regra")


def por_que_o_veto_quebra(fixtures) -> None:
    """O mecanismo, frase a frase: o veto é um `all()`, e mais texto = mais chances de falhar."""
    print("`_fala_de_terceiro` só veta quando TODA ocorrência do termo cai em frase com marcador.")
    print("Varrer o documento inteiro acrescenta ocorrências — e basta UMA sem marcador para o")
    print("`all()` colapsar e a exclusão voltar. Abaixo, cada ocorrência nova e seu veredito.\n")
    for i, f in enumerate(fixtures):
        startup = regua.como_startup(f, i)
        perfil = extractor.node({"startup": startup})["perfil"]
        if not briefing.elegibilidade(startup, _PerfilAmplo(startup, perfil)).elegivel \
                and briefing.elegibilidade(startup, perfil).elegivel:
            for rotulo, termos in briefing.EXCLUSOES.items():
                for termo in termos:
                    for d in startup.documentos:
                        baixa = d.conteudo_texto.lower()
                        frases = [x.strip() for x in briefing._FIM_DE_FRASE.split(baixa)
                                  if briefing._ocorre(termo, x)]
                        if not frases:
                            continue
                        print(f"{f['nome']} · [{rotulo}/{termo}] · {len(frases)} frase(s) · "
                              f"veto={briefing._fala_de_terceiro(termo, baixa)}")
                        for x in frases:
                            marc = [m for m in briefing.MARCADORES_DE_TERCEIRO
                                    if briefing._ocorre(m, x)]
                            print(f"    {'marcador: ' + marc[0] if marc else 'SEM MARCADOR   '}"
                                  f" :: {re.sub(r'\s+', ' ', x)[:120]}")
                        print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--terceiro", action="store_true",
                    help="por que varrer o documento inteiro quebra o veto de terceiro")
    args = ap.parse_args()
    fixtures = regua.carregar()
    if args.terceiro:
        por_que_o_veto_quebra(fixtures)
    else:
        medir(fixtures)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
