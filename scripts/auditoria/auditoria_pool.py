"""Itens 2, 3 e 5 da auditoria: união real, pool do reranker, e a âncora da q17."""
import sys, json
from pathlib import Path
sys.path.insert(0, "/Users/viniciustavarescastiglia/case-nvidia")

import yaml
from src.rag.busca import buscar_denso_bruto
from src.rag.lexical import buscar_lexical_bruto
from src.rag.fusao import fundir_rrf
from src.rag.rerank import logits_de, LOTE

GAB = Path("/Users/viniciustavarescastiglia/case-nvidia/data/avaliacao/gabarito.yaml")
gab = yaml.safe_load(GAB.read_text())
POOL = 20
K_RRF, PD, PL = 10, 1.0, 0.3     # config de PRODUÇÃO (src/rag/pipeline.py)

dados = {}
tamanhos = []
for p in gab:
    q = p["pergunta"]
    denso = buscar_denso_bruto(q, k=POOL)
    lexical = buscar_lexical_bruto(q, k=POOL)
    fundido = fundir_rrf({"denso": denso, "lexical": lexical},
                         {"denso": PD, "lexical": PL}, K_RRF)
    uniao = [pa for pa, _ in fundido]
    tamanhos.append((p["id"], len(denso), len(lexical), len(uniao)))
    logits = logits_de(q, uniao)          # UMA chamada cobre os três pools
    dados[p["id"]] = {
        "p": p,
        "denso20": [pa for pa, _ in denso],
        "fusao20": uniao[:POOL],
        "uniao": uniao,
        "logits": logits,
    }

print("=== ITEM 5 — tamanho REAL da união (K=10, peso_lex=0.3, pool=20 por braço) ===")
print(f"{'id':5}{'denso':>7}{'lexical':>9}{'união':>7}{'lotes de rerank':>18}")
for i, d, l, u in tamanhos:
    print(f"{i:5}{d:>7}{l:>9}{u:>7}{-(-u//LOTE):>18}")
us = [u for _, _, _, u in tamanhos]
print(f"\n  união: min={min(us)} max={max(us)} média={sum(us)/len(us):.1f}  (n={len(us)} consultas)")
print(f"  consultas que passam de {LOTE} (2 lotes): {sum(1 for u in us if u > LOTE)} de {len(us)}")

def recall(pool_key):
    frouxo = {1:0,3:0,5:0}; estrito = {1:0,3:0,5:0}; n = 0; falhas=[]
    for id_, d in dados.items():
        p = d["p"]
        if p["tipo"] == "sem_resposta": continue
        n += 1
        lg = d["logits"]
        ordem = sorted(d[pool_key], key=lambda pa: -lg[pa.chunk_id])
        achou1 = False
        for k in (1,3,5):
            doc = [pa for pa in ordem[:k] if pa.documento_url == p["url_esperada"]]
            if doc:
                frouxo[k] += 1
                if any(p["frase_ancora"].lower() in pa.texto.lower() for pa in doc):
                    estrito[k] += 1
                if k == 1: achou1 = True
        if not achou1: falhas.append(id_)
    return frouxo, estrito, n, falhas

print("\n=== ITEM 3 + a divergência harness/produção: MESMOS logits, três pools ===")
print(f"{'pool reranqueado':28}{'r@1':>6}{'r@3':>6}{'r@5':>6}{'e@1':>6}{'e@3':>6}{'e@5':>6}   falhas r@1")
for chave, rotulo in (("denso20", "20 densos (rerank_denso)"),
                      ("fusao20", "top-20 da fusão (harness)"),
                      ("uniao",   "união INTEIRA (produção)")):
    f, e, n, falhas = recall(chave)
    print(f"{rotulo:28}" + "".join(f"{f[k]/n:>6.0%}" for k in (1,3,5))
          + "".join(f"{e[k]/n:>6.0%}" for k in (1,3,5)) + f"   {falhas}")

print("\n=== ITEM 2 — onde a âncora de cada pergunta cai no rerank da UNIÃO ===")
print(f"{'id':5}{'|união|':>8}{'pos. do chunk-âncora no rerank':>34}{'logit':>10}")
for id_, d in dados.items():
    p = d["p"]
    if p["tipo"] == "sem_resposta": continue
    lg = d["logits"]
    ordem = sorted(d["uniao"], key=lambda pa: -lg[pa.chunk_id])
    pos = next((i for i, pa in enumerate(ordem, 1)
                if p["frase_ancora"].lower() in pa.texto.lower()), None)
    marca = ""
    if pos is None: marca = "  ÂNCORA FORA DA UNIÃO"
    elif pos > 10:  marca = "  fora do top-10"
    elif pos > 5:   marca = "  fora do top-5"
    logit = f"{lg[ordem[pos-1].chunk_id]:+.4f}" if pos else "—"
    print(f"{id_:5}{len(d['uniao']):>8}{str(pos):>34}{logit:>10}{marca}")

print("\n=== A premissa de rerank.py:37 — lote não muda score? ===")
alvo = dados["q17"]
u = alvo["uniao"]
q = alvo["p"]["pergunta"]
inteiro = logits_de(q, u)                      # lote(s) natural(is)
metade_a = logits_de(q, u[:len(u)//2])
metade_b = logits_de(q, u[len(u)//2:])
juntos = {**metade_a, **metade_b}
difs = [(cid, inteiro[cid], juntos[cid]) for cid in inteiro if abs(inteiro[cid]-juntos[cid]) > 1e-9]
print(f"  união de {len(u)} passagens · {len(difs)} de {len(u)} logits diferem entre loteamentos")
for cid, a, b in difs[:8]:
    print(f"    chunk {cid}: {a:+.4f} vs {b:+.4f}  (Δ {a-b:+.4f})")
