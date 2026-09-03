"""O veredito de elegibilidade das 30 empresas, numa tabela. Zero API, poucos segundos.

POR QUE ISTO EXISTE (D-094)
----------------------------
D-083 diz "rode o sistema; leitura de código não substitui execução". Este script é o
**corolário**: rode-o sobre a base INTEIRA, não sobre uma amostra.

Em 03/09 três defeitos da MESMA FORMA — o conceito da exclusão estava certo e o vocabulário era
estreito — escaparam de duas sessões de auditoria estática e de dezenas de greps. Os dois
primeiros foram achados LENDO um briefing, que é amostragem: dá para ler três empresas, não
trinta. Esta varredura achou os dois seguintes **na primeira execução**:

- `capital aberto` era B3-cêntrica (`"listada na b3"`), e a **Zenvia**, listada na **Nasdaq**,
  saía ELEGÍVEL. Metade das brasileiras que abrem capital lista fora do Brasil.
- a **Iniciador**, infraestrutura de Pix, era recusada por *"o mercado de stablecoins"* — um
  falso positivo que a própria sessão tinha criado 40 minutos antes, ao alargar a lista de
  cripto em D-091.

**O segundo é o que justifica o arquivo:** instrumento que só confirma o que você espera não é
instrumento. Este pega o defeito que VOCÊ acabou de introduzir.

O QUE ELE NÃO É
---------------
Não é régua. Régua é `avaliar_agentes.py --exclusoes`, que tem gabarito e mede os dois lados
separados. Aqui não há resposta certa declarada: é uma tabela para um humano LER, do mesmo jeito
que se lê um briefing — só que de todas as empresas de uma vez. Quando esta varredura acha algo,
o caso vai para `data/avaliacao/exclusoes.yaml` **antes** do conserto, e aí vira régua.

POR QUE NÃO PASSA PELO GRAFO
-----------------------------
`elegibilidade()` precisa de `perfil`, e `perfil` sai do `extractor` — mais nada. Rodar o grafo
inteiro custaria `nvidia_rag` (banco + API de rerank) por empresa, e em 03/09 foi exatamente esse
custo que estourou a cota mensal do Cohere (D-093). Um instrumento de varredura tem de ser barato
o bastante para ser rodado sem pensar.

USO
---
    python scripts/varrer_elegibilidade.py            # a tabela
    python scripts/varrer_elegibilidade.py --motivos  # com a evidência de cada exclusão
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import avaliar_agentes as regua  # noqa: E402
from src.agents import extractor  # noqa: E402
from src.agents.briefing import elegibilidade  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--motivos", action="store_true",
                    help="imprime a evidência que sustenta cada exclusão")
    args = ap.parse_args()

    fixtures = regua.carregar()
    excluidas: list[tuple[str, str]] = []

    print(f"{len(fixtures)} empresa(s) em data/seed/\n")
    print(f"{'empresa':22} {'ano':>5}  veredito")
    print("-" * 78)

    for i, f in enumerate(fixtures):
        startup = regua.como_startup(f, i)
        perfil = extractor.node({"startup": startup})["perfil"]
        e = elegibilidade(startup, perfil)
        ano = startup.ano_fundacao or "—"

        if e.elegivel:
            print(f"{f['nome']:22} {str(ano):>5}  ELEGÍVEL    "
                  f"{len(e.requisitos_nao_verificados)} requisito(s) não verificado(s)")
            continue

        rotulos = " · ".join(
            m.split(":")[0].replace("exclusão por ", "").strip("'")
            for m in e.motivos_exclusao
        )
        print(f"{f['nome']:22} {str(ano):>5}  NÃO ELEGÍVEL  {rotulos}")
        excluidas.append((f["nome"], rotulos))
        if args.motivos:
            for m in e.motivos_exclusao:
                print(f"{'':29}   x {m}")
            for ev in e.evidencias:
                print(f"{'':31}   « {ev.trecho.strip()[:100]}…")

    print(f"\n{len(excluidas)} de {len(fixtures)} recusadas: "
          + " · ".join(f"{n} ({r})" for n, r in excluidas))
    print("\nLEIA a tabela. Uma recusa errada aparece aqui e não aparece em nenhum teste verde —\n"
          "e uma recusa que FALTA não aparece em lugar nenhum (o falso negativo de D-052).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
