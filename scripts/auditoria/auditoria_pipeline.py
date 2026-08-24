"""Item 7: caminhos de src/rag/pipeline.py que nunca rodaram."""
import sys
from pathlib import Path
sys.path.insert(0, "/Users/viniciustavarescastiglia/case-nvidia")
import yaml
from src.rag import pipeline as pl
from src.rag.busca import buscar_denso_bruto

gab = yaml.safe_load(Path("/Users/viniciustavarescastiglia/case-nvidia/data/avaliacao/gabarito.yaml").read_text())
Q = next(p for p in gab if p["id"] == "q19")["pergunta"]

print("=== 1. `--fusao soma` pelo caminho de PRODUÇÃO (recuperar/buscar_hibrido) ===")
for fus, norm in (("rrf", "minmax"), ("soma", "minmax"), ("soma", "soma")):
    try:
        r = pl.buscar_hibrido(Q, k=3, fusao=fus, norm=norm)
        print(f"  fusao={fus:5} norm={norm:7} OK -> " + " · ".join(f"{c.tecnologia}" for c in r))
    except Exception as e:
        print(f"  fusao={fus:5} norm={norm:7} FALHOU: {type(e).__name__}: {e}")

print("\n=== 2. `peso_lexical=0.0` reduz à densa EXATAMENTE? (afirmação de pipeline.py:20) ===")
falhas = 0
for p in gab[:8]:
    q = p["pergunta"]
    denso = [pa.chunk_id for pa, _ in buscar_denso_bruto(q, k=20)]
    for fus in ("rrf", "soma"):
        fundido, _, sl = pl.recuperar(q, peso_lexical=0.0, fusao=fus)
        ids = [pa.chunk_id for pa, _ in fundido]
        ok = ids == denso
        if not ok:
            falhas += 1
            print(f"  {p['id']} fusao={fus}: DIVERGE  densa={denso[:5]} vs fundida={ids[:5]}")
        assert sl == {}, "braço lexical não deveria ter votado"
print(f"  {falhas} divergências em 8 consultas × 2 fusões (lexical não vota: confirmado)")

print("\n=== 3. buscar_com_rerank manda a UNIÃO inteira ao reranker? ===")
import src.rag.rerank as rr
tamanhos = []
orig = rr.logits_de
def espiao(consulta, passagens):
    tamanhos.append(len(passagens))
    return orig(consulta, passagens)
rr.logits_de = espiao
import src.rag.pipeline as plm
plm.reranquear.__globals__["logits_de"] = espiao
for p in gab[:4]:
    fundido, _, _ = pl.recuperar(p["pergunta"])
    r = pl.buscar_com_rerank(p["pergunta"], k=5)
    print(f"  {p['id']}: união={len(fundido):>3}  passou ao reranker={tamanhos[-1]:>3}  "
          f"{'IGUAL' if tamanhos[-1] == len(fundido) else 'TRUNCOU'}  devolveu k={len(r)}")

print("\n=== 4. responder() com consulta que não recupera nada (guarda de geracao.py) ===")
vazio = pl.buscar_hibrido("", k=3)
print(f"  buscar_hibrido('') -> {len(vazio)} resultados")
