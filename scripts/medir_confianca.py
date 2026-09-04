"""Os braços de `diagnostico.confianca`, isolados para ATRIBUIR a causa. Zero API.

POR QUE ISTO EXISTE (D-098)
----------------------------
O campo sai `baixa` para TODAS as empresas: 0/6 na régua, contra 3/8 da linha trivial. Não é
impreciso, é **constante** — e um campo constante não carrega informação, no sentido literal.

D-059 (27/08) mediu o conserto óbvio — avaliar a evidência DO DIAGNÓSTICO em vez do `min()`
sobre o perfil inteiro — obteve 2/6 contra alvo de 4, e REPROVOU. E deixou escrita uma
hipótese sobre a causa que sobrou:

    "Melhorar isso é fazer o Classifier anexar evidência mais larga, e isso é trabalho do
     Extractor, que recorta uma frase por documento."

**Essa hipótese ficou 8 dias no log sem nunca ter sido testada, e é falsa.** O braço C mede
exatamente ela — anexar TODAS as afirmações de cada detector em vez de só a `[0]` — e dá o
mesmo 2 do braço B. Anexar mais evidência não move uma casa.

O que move é a RECÊNCIA, e por um motivo que não estava registrado: `avaliar()` exige
`>= 1 documento recente` para conceder `alta`, `_recente(None)` devolve `False`, e **86 dos
93 documentos da base têm `data_publicacao: null`** — porque `coletar.py` não captura data
nenhuma. Metade da regra está desligada desde sempre. O braço D mede quanto isso vale: +1.

E mesmo o melhor braço (D = 3) apenas EMPATA com a linha trivial em acertos absolutos. O que
a régua não vê, e decide: o trivial acerta 3 respondendo `alta` para todo mundo — constante e
inútil —, enquanto D acerta 3 DISCRIMINANDO (`alta` na Axenya, `media` no Deal, `baixa` na
SunnyHUB). **Contar acertos é cego para essa diferença**, e ela é a que o gerente sente.

CRITÉRIO, FIXADO ANTES DE MEDIR (o alvo de D-058): >= 4 acertos absolutos.
Piso de comparação: a linha trivial, 3.

USO
---
    python scripts/medir_confianca.py
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import avaliar_agentes as regua  # noqa: E402
from src.agents import evidence_validator as ev  # noqa: E402
from src.agents import extractor  # noqa: E402
from src.state import Afirmacao  # noqa: E402

ORDEM = {"baixa": 0, "media": 1, "alta": 2}
DATA_SINTETICA = date(2026, 6, 1)   # só no braço D, e só para isolar o efeito da recência


def _conf(evidencias, forcar_recente: bool = False) -> str:
    if not evidencias:
        return "baixa"
    a = Afirmacao(texto="sintética", justificativa="", evidencias=list(evidencias))
    if forcar_recente:
        for e in a.evidencias:
            if e.data_publicacao is None:
                e.data_publicacao = DATA_SINTETICA
    return ev.avaliar(a)[0]


def main() -> int:
    placar = {"A": 0, "B": 0, "C": 0, "D": 0}
    n = 0
    print("A=produção (min sobre o perfil) · B=D-059 · C=B+evidência larga · D=C+datas\n")
    print(f"{'empresa':16} {'espera':18} {'A':>6} {'B':>6} {'C':>6} {'D':>6}")
    print("-" * 62)

    for i, f in enumerate(regua.carregar()):
        esp = (f.get("gabarito") or {}).get("confianca")
        if esp is None:
            continue
        aceitos = esp if isinstance(esp, list) else [esp]
        ambigua = isinstance(esp, list)
        perfil = extractor.node({"startup": regua.como_startup(f, i)})["perfil"]

        confs = [ev.avaliar(a)[0] for a in perfil.afirmacoes]
        A = min(confs, key=lambda c: ORDEM[c]) if confs else "baixa"

        # O que o Classifier anexa hoje é só a `[0]` de cada detector (classifier.py:176-181).
        estreita, larga = [], []
        if perfil.modelo_entrega and "autopilot" in perfil.modelo_entrega.texto.lower():
            estreita += perfil.modelo_entrega.evidencias
            larga += perfil.modelo_entrega.evidencias
        for lista in (perfil.sinais_dado_proprietario, perfil.sinais_otimizacao_tecnica):
            if lista:
                estreita += lista[0].evidencias
                for a in lista:
                    larga += a.evidencias

        B, C = _conf(estreita), _conf(larga)
        D = _conf(larga, forcar_recente=True)

        if not ambigua:
            n += 1
            for k, v in (("A", A), ("B", B), ("C", C), ("D", D)):
                placar[k] += v in aceitos
        marca = "  (ambígua)" if ambigua else ""
        print(f"{f['nome']:16} {str(esp):18} {A:>6} {B:>6} {C:>6} {D:>6}{marca}")

    print(f"\nACERTOS ABSOLUTOS — denominador {n} · trivial faz 3 · alvo de D-058 = 4")
    for k, rotulo in (("A", "produção hoje (min sobre o perfil)"),
                      ("B", "D-059 — evidência do diagnóstico, `[0]`"),
                      ("C", "B + evidência LARGA (todas as afirmações)"),
                      ("D", "C + datas de publicação preenchidas")):
        alvo = "  <- passa o alvo" if placar[k] >= 4 else ""
        print(f"   {k}  {rotulo:44} {placar[k]}{alvo}")

    print(f"\nC == B refuta a hipótese que D-059 deixou escrita: anexar evidência mais larga")
    print(f"não move o campo. O que move é a recência — e ela depende de `coletar.py` capturar")
    print(f"`data_publicacao`, que hoje é `null` em 86 dos 93 documentos.")
    print(f"\nNENHUM braço passa o alvo de 4. D empata com o trivial em acertos, e o supera no")
    print(f"que a régua não conta: ele DISCRIMINA. Decidir isso é ato de produto, não de placar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
