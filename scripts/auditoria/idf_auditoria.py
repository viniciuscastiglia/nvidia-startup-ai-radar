"""Auditoria da tabela de IDF de D-036, com o tokenizador REAL de src/rag/lexical.py."""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path("/Users/viniciustavarescastiglia/case-nvidia")))

from src.db import conectar
from src.rag.lexical import tokenizar

SQL = """SELECT id, texto, texto_indexado FROM chunks_nvidia
         WHERE estrategia = 'estrutural-v1' ORDER BY id"""

with conectar() as cx, cx.cursor() as cur:
    cur.execute(SQL)
    linhas = cur.fetchall()

N = len(linhas)
print(f"N = {N} chunks (estrutural-v1)\n")

def df_de(campo):
    df = {}
    for l in linhas:
        for t in set(tokenizar(l[campo])):
            df[t] = df.get(t, 0) + 1
    return df

def robertson(df, n): return math.log((n - df + 0.5) / (df + 0.5))
def lucene(df, n):    return math.log(1 + (n - df + 0.5) / (df + 0.5))

TERMOS = ["and", "nvidia", "ai", "colang"]

for campo in ("texto_indexado", "texto"):
    df = df_de(campo)
    print(f"--- campo indexado: {campo} ---")
    print(f"{'termo':10}{'df':>5}{'df/N':>7}{'idf robertson':>16}{'idf lucene':>13}")
    for t in TERMOS:
        d = df.get(t, 0)
        if d == 0:
            print(f"{t:10}{'AUSENTE':>5}")
            continue
        print(f"{t:10}{d:>5}{d/N:>6.0%}{robertson(d,N):>16.4f}{lucene(d,N):>13.4f}")
    # quantos termos teriam idf negativo em robertson (df > (N-1)/2 aprox)
    negativos = sorted((t for t, d in df.items() if robertson(d, N) < 0),
                       key=lambda t: -df[t])
    print(f"  termos com idf robertson NEGATIVO: {len(negativos)} de {len(df)} "
          f"({len(negativos)/len(df):.1%} do vocabulário)")
    print(f"  os 12 de maior df: {[(t, df[t]) for t in negativos[:12]]}\n")
