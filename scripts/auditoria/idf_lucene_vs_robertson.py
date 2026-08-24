"""D-036 §1 sob teste: o robertson do bm25s produz IDF negativo? E muda o recall?"""
import sys, math
from pathlib import Path
sys.path.insert(0, "/Users/viniciustavarescastiglia/case-nvidia")

import bm25s, yaml
from src.db import conectar
from src.rag import lexical as lx

SQL = """SELECT id, tecnologia, texto_indexado, documento_url FROM chunks_nvidia
         WHERE estrategia='estrutural-v1' ORDER BY id"""
with conectar() as cx, cx.cursor() as cur:
    cur.execute(SQL); linhas = cur.fetchall()

corpus = [lx.tokenizar(l["texto_indexado"]) for l in linhas]
N = len(corpus)

print("=== 1. IDF que a BIBLIOTECA de fato usa (não a fórmula do papel) ===")
for metodo in ("lucene", "robertson"):
    r = bm25s.BM25(k1=lx.K1, b=lx.B, method=metodo)
    r.index(corpus, show_progress=False)
    vocab = r.vocab_dict
    print(f"\n  method={metodo}")
    for termo in ("nvidia", "ai", "colang", "and"):
        if termo not in vocab:
            print(f"    {termo:10} NÃO ESTÁ NO VOCABULÁRIO (stopword ou ausente)")
            continue
        tid = vocab[termo]
        df = sum(1 for doc in corpus if termo in doc)
        # score de um doc contendo o termo, isolando o efeito do idf:
        # a coluna do termo na matriz esparsa já traz idf*tfc
        col = r.scores["data"][r.scores["indptr"][tid]:r.scores["indptr"][tid+1]]
        print(f"    {termo:10} df={df:>4}  score_min={col.min():+.4f}  score_max={col.max():+.4f}")

print("\n=== 2. Recall do braço lexical: lucene vs robertson (zero chamada de API) ===")
gab = yaml.safe_load(Path("/Users/viniciustavarescastiglia/case-nvidia/data/avaliacao/gabarito.yaml").read_text())
com_resp = [p for p in gab if p["tipo"] != "sem_resposta"]

for metodo in ("lucene", "robertson"):
    r = bm25s.BM25(k1=lx.K1, b=lx.B, method=metodo)
    r.index(corpus, show_progress=False)
    frouxo = {1:0, 3:0, 5:0}
    estrito = {1:0, 3:0, 5:0}
    for p in com_resp:
        toks = lx.tokenizar(p["pergunta"])
        idx, sc = r.retrieve([toks], k=20, show_progress=False)
        ordem = [linhas[int(i)] for i, s in zip(idx[0], sc[0]) if s > 0]
        for k in (1,3,5):
            doc = [l for l in ordem[:k] if l["documento_url"] == p["url_esperada"]]
            if doc:
                frouxo[k] += 1
                if any(p["frase_ancora"].lower() in l["texto_indexado"].lower() for l in doc):
                    estrito[k] += 1
    n = len(com_resp)
    print(f"  {metodo:10} r@1 {frouxo[1]/n:.0%}  r@3 {frouxo[3]/n:.0%}  r@5 {frouxo[5]/n:.0%}   "
          f"e@1 {estrito[1]/n:.0%}  e@3 {estrito[3]/n:.0%}  e@5 {estrito[5]/n:.0%}   (n={n})")

print("\n=== 3. Quantas consultas do gabarito contêm 'nvidia' ou 'ai' como token? ===")
alvo = 0
for p in gab:
    t = set(lx.tokenizar(p["pergunta"]))
    if t & {"nvidia", "ai"}:
        alvo += 1
        print(f"    {p['id']}: {sorted(t & {'nvidia','ai'})} — {p['pergunta'][:70]}")
print(f"  {alvo} de {len(gab)} consultas")
