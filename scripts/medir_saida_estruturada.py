"""Re-medição de D-047: `json_schema` vs `function_calling` vs `json_mode` no passo 8.

POR QUE ISTO VIROU SCRIPT VERSIONADO EM 28/08, TENDO SIDO MEDIÇÃO SOLTA EM 24/08
---------------------------------------------------------------------------------
D-047 fixou a convenção mais transversal do repositório — *"todo acesso a LLM passa por
`src/llm.py` e sempre com `method='json_schema'`"* — com uma medição de n=5 num modelo que
**morreu em 27/08**. Trocar o LLM (D-067) não conserta esse número: **invalida**.

E a primeira sonda com o modelo novo veio **invertida**: na mesma pergunta-armadilha,
`json_schema` alucinou e `function_calling` se absteve. Uma execução não decide nada — mas
mostra que a conclusão de D-047 podia ser propriedade do MODELO e não do método, e uma
convenção que vale para o repositório inteiro não pode ficar apoiada numa lembrança.

O PROTOCOLO É O DE D-047, DE PROPÓSITO — SENÃO OS NÚMEROS NÃO SE COMPARAM
--------------------------------------------------------------------------
q23 do gabarito (*"o TensorRT-LLM é mais rápido que o vLLM? Em quantos por cento?"*), cuja
resposta **não existe no corpus**; `temperature=0`; n=5 por método. A saída correta é
`abstencao=True` — a passagem é altamente relevante (logit +8,53, dos mais altos do gabarito) e
simplesmente não contém a comparação. É o erro que o passo 8 existe para evitar.

DUAS DIFERENÇAS EM RELAÇÃO A 24/08, E ELAS FAVORECEM ESTA MEDIÇÃO
-------------------------------------------------------------------
1. **Os trechos são recuperados UMA vez e reusados nos três métodos.** Em 24/08 cada braço
   recuperava por conta própria. Fixar a entrada isola a variável que se quer medir: o que muda
   entre os braços é só o método de decodificação.
2. **Usa `SaidaGerador` e `INSTRUCAO` reais**, importados de `src.rag.geracao`. Medir com um
   schema de brinquedo mediria o schema de brinquedo — e D-045 já registrou que **o docstring do
   schema é prompt**, então um schema diferente é um prompt diferente.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from langchain_openai import ChatOpenAI  # noqa: E402

from src.config import LLM  # noqa: E402
from src.rag.geracao import INSTRUCAO, SaidaGerador, formatar  # noqa: E402
from src.rag.pipeline import buscar_com_rerank  # noqa: E402

METODOS = ("json_schema", "function_calling", "json_mode")
GABARITO = Path(__file__).resolve().parent.parent / "data" / "avaliacao" / "gabarito.yaml"


def pergunta_de(pid: str) -> str:
    for p in yaml.safe_load(GABARITO.read_text(encoding="utf-8")):
        if p["id"] == pid:
            return p["pergunta"]
    raise SystemExit(f"pergunta {pid} não está no gabarito")


def uma_chamada(metodo: str, prompt: str) -> tuple[str, str]:
    """Devolve (veredito, detalhe). O veredito CORRETO nesta pergunta é 'absteve'."""
    cliente = ChatOpenAI(
        base_url=LLM.base_url, api_key=LLM.api_key, model=LLM.modelo,
        temperature=0.0, timeout=120.0, max_retries=0,
    ).with_structured_output(SaidaGerador, method=metodo)
    try:
        r = cliente.invoke(prompt)
    except Exception as exc:  # noqa: BLE001
        return "erro", f"{type(exc).__name__}: {str(exc)[:70]}"
    if r.abstencao:
        return "absteve", (r.motivo_abstencao or "")[:70]
    return "ALUCINOU", (r.texto or "")[:70]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-n", type=int, default=5, help="execuções por método (D-047 usou 5)")
    ap.add_argument("--pergunta", default="q23", help="id no gabarito; default é a armadilha")
    ap.add_argument("--k", type=int, default=5, help="trechos lidos, igual ao passo 8")
    ap.add_argument("--metodos", nargs="+", choices=METODOS, default=list(METODOS),
                    help="restringe os braços — útil para subir o n só onde a diferença é real")
    args = ap.parse_args()

    consulta = pergunta_de(args.pergunta)
    print("=" * 78)
    print(f"D-047 RE-MEDIDO — modelo: {LLM.modelo}")
    print("=" * 78)
    print(f"\n{args.pergunta}: {consulta}")

    # UMA recuperação, reusada nos três braços. Ver o docstring.
    citacoes = buscar_com_rerank(consulta, k=args.k)
    prompt = f"{INSTRUCAO}\n\nTRECHOS:\n{formatar(citacoes)}\n\nPERGUNTA: {consulta}"
    print(f"trechos fixados: {len(citacoes)} — {[c.tecnologia for c in citacoes]}")
    print(f"\n{'método':18s} {'placar':12s} detalhe da 1ª execução")

    resultados: dict[str, Counter] = {}
    for metodo in args.metodos:
        contagem: Counter = Counter()
        primeiro = ""
        for i in range(args.n):
            veredito, detalhe = uma_chamada(metodo, prompt)
            contagem[veredito] += 1
            if i == 0:
                primeiro = f"{veredito}: {detalhe}"
        resultados[metodo] = contagem
        placar = f"{contagem['absteve']}/{args.n}"
        print(f"  {metodo:16s} {placar:12s} {primeiro}")

    print(f"\n'absteve' é o CORRETO — a resposta não existe no corpus (n={args.n})")
    print("  D-047 em 24/08, com meta/llama-3.1-8b-instruct (MORTO): 4/5 · 0/5 · 0/5")
    atual = " · ".join(f"{m} {resultados[m]['absteve']}/{args.n}" for m in args.metodos)
    print(f"  agora, com {LLM.modelo}: {atual}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
