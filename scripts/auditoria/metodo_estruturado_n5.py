"""`json_schema` vs `function_calling` vs `json_mode` na q23, com n=5. Fecha a §5 da revisão 03.

O PROBLEMA QUE ESTE SCRIPT EXISTE PARA RESOLVER
------------------------------------------------
D-040 escolheu `method="json_schema"` com uma tabela de TRÊS LINHAS — uma pergunta, uma execução
por método — contra um passo que a mesma decisão declara não-determinístico (22, 23 e 24 de 24
observados no mesmo código). A revisão da sessão 03 chamou isso de "o risco mais carregado" e
orçou o fechamento em ~15 chamadas. A escolha virou `METODO_ESTRUTURADO` em `src/llm.py`, o
portão único por onde os oito agentes da M4 vão passar.

Em 25/08 o risco deixou de ser teórico: na stack pós-EOL, `json_schema` ALUCINOU na q23
("o TensorRT-LLM é mais rápido que o vLLM em 60%") numa de três execuções do `--geracao`.
A afirmação de D-040 de que o método impede a alucinação já está derrubada por contraexemplo;
o que falta medir é a FREQUÊNCIA de cada método.

DESENHO
-------
A q23 é recuperada UMA vez e os mesmos top-5 alimentam as 15 gerações — assim a única variável
é o método de saída estruturada, e não o pool. Critério: acertar = `abstencao=True`, porque a
resposta não existe na base (a q23 é `sem_resposta`, regime `topicamente_perfeita`).

Uso:  python scripts/auditoria/metodo_estruturado_n5.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAIZ))

import yaml

from langchain_openai import ChatOpenAI

from src.config import LLM
from src.rag.geracao import INSTRUCAO, SaidaGerador, formatar
from src.rag.pipeline import buscar_com_rerank

METODOS = ("json_schema", "function_calling", "json_mode")
EXECUCOES = 5
K = 5

# Espelha `src.llm.chat(0.0)` e acrescenta DUAS coisas que a produção não tem, de propósito:
#
#   timeout=90     — a primeira tentativa deste script travou indefinidamente no `json_mode`.
#                    Sem teto, um método que pendura mata a auditoria dos outros dois.
#   max_retries=0  — o default do langchain_openai é 2. Com retry, "5 execuções" poderiam ser
#                    15 chamadas, e um método que falha e é re-tentado até passar pareceria mais
#                    confiável do que é. Aqui uma execução é UMA chamada, e falha conta como falha.
def cliente(metodo: str):
    base = ChatOpenAI(
        base_url=LLM.base_url,
        api_key=LLM.api_key,
        model=LLM.modelo,
        temperature=0.0,
        timeout=90,
        max_retries=0,
    )
    return base.with_structured_output(SaidaGerador, method=metodo)


def main() -> int:
    perguntas = yaml.safe_load((RAIZ / "data/avaliacao/gabarito.yaml").read_text())
    q23 = next(p for p in perguntas if p["id"] == "q23")
    assert q23["tipo"] == "sem_resposta", "a q23 deveria ser sem_resposta"

    print(f"Modelo: {LLM.modelo}  ·  temperatura 0.0  ·  {EXECUCOES} execuções por método")
    print(f"Pergunta (q23, {q23['tipo']}/{q23.get('regime', '-')}): {q23['pergunta']}")
    print("Acerto = abstencao=True. A base NÃO contém a comparação.\n")

    # Uma recuperação só: o pool é constante nas 15 gerações.
    citacoes = buscar_com_rerank(q23["pergunta"], k=K)
    prompt = f"{INSTRUCAO}\n\nTRECHOS:\n{formatar(citacoes)}\n\nPERGUNTA: {q23['pergunta']}"
    print(f"top-{K} reranqueados, fixos para todas as execuções:")
    for i, c in enumerate(citacoes):
        print(f"  [{i}] ({c.tecnologia}) logit={c.score_rerank:+.4f}  {c.trecho[:70]}...")
    print()

    placar: dict[str, list[str]] = {}
    for metodo in METODOS:
        print(f"{'─' * 78}\n{metodo}")
        resultados = []
        for i in range(1, EXECUCOES + 1):
            try:
                r = cliente(metodo).invoke(prompt)
                if r.abstencao:
                    resultados.append("absteve")
                    print(f"  {i}. ABSTEVE   — {(r.motivo_abstencao or '')[:88]}")
                else:
                    resultados.append("respondeu")
                    print(f"  {i}. RESPONDEU — {r.texto[:88]}")
            except Exception as exc:  # noqa: BLE001
                resultados.append("erro")
                print(f"  {i}. ERRO {type(exc).__name__}: {str(exc)[:80]}")
        placar[metodo] = resultados

    print(f"\n{'=' * 78}\nPLACAR — acerto é ABSTER (a resposta não existe na base)\n")
    print(f"  {'método':18}{'absteve':>9}{'respondeu':>11}{'erro':>7}   acurácia")
    for metodo, res in placar.items():
        a, r, e = (res.count(x) for x in ("absteve", "respondeu", "erro"))
        print(f"  {metodo:18}{a:>9}{r:>11}{e:>7}   {a}/{EXECUCOES}")

    print("\nLeitura: 'respondeu' na q23 é ALUCINAÇÃO — o número comparativo não existe no corpus.")
    print("'erro' no json_mode é falha de parse, que D-040 já havia observado com n=1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
