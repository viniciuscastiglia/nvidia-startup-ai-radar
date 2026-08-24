"""O logit de uma passagem depende de QUEM está no mesmo lote? Decide rerank.py:37 e D-034."""
import sys, importlib.util
from pathlib import Path
sys.path.insert(0, "/Users/viniciustavarescastiglia/case-nvidia")
spec = importlib.util.spec_from_file_location(
    "vr", "/Users/viniciustavarescastiglia/case-nvidia/scripts/verificar_reranker.py")
vr = importlib.util.module_from_spec(spec); spec.loader.exec_module(vr)
from src.db import conectar

n_resp = vr.n_tokens(vr.RESPOSTA)
A = vr.encher(450)                                   # só enchimento
P = vr.encher(450 - n_resp) + " " + vr.RESPOSTA       # o alvo: 450 tok COM a resposta
Q = vr.QUERY

with conectar() as cx, cx.cursor() as cur:
    cur.execute("""SELECT texto_indexado FROM chunks_nvidia WHERE estrategia='estrutural-v1'
                   ORDER BY id LIMIT 30""")
    outros = [l["texto_indexado"] for l in cur.fetchall()]

def logit_de_P(passagens, pos_P):
    lg, _, err = vr._ranquear(Q, passagens)
    return None if err else lg[pos_P]

cenarios = [
    ("P sozinho",                  lambda: ([P], 0)),
    ("[A, P]  (o de D-034)",       lambda: ([A, P], 1)),
    ("[P, A]  (ordem trocada)",    lambda: ([P, A], 0)),
    ("P + 9 chunks reais",         lambda: ([P] + outros[:9], 0)),
    ("9 chunks reais + P",         lambda: (outros[:9] + [P], 9)),
    ("P + 29 chunks reais",        lambda: ([P] + outros[:29], 0)),
]
print(f"{'cenário':28}{'|lote|':>8}{'execução 1':>13}{'execução 2':>13}{'execução 3':>13}")
vistos = set()
for nome, faz in cenarios:
    passagens, pos = faz()
    vals = [logit_de_P(passagens, pos) for _ in range(3)]
    vistos.update(v for v in vals if v is not None)
    print(f"{nome:28}{len(passagens):>8}" + "".join(f"{v:>13.4f}" for v in vals))

print(f"\n  valores DISTINTOS observados para a MESMA passagem: {sorted(vistos)}")
print(f"  {'O logit NÃO é propriedade só do par (consulta, passagem)' if len(vistos) > 1 else 'O logit é estável em toda composição testada'}")
