"""Item 2: 'a âncora da q17 não está no top-10' (D-040) — nos DOIS pools."""
import sys
from pathlib import Path
sys.path.insert(0, "/Users/viniciustavarescastiglia/case-nvidia")
import yaml
from src.db import conectar
from src.rag.busca import buscar_denso_bruto
from src.rag.lexical import buscar_lexical_bruto
from src.rag.fusao import fundir_rrf
from src.rag.rerank import logits_de

gab = yaml.safe_load(Path("/Users/viniciustavarescastiglia/case-nvidia/data/avaliacao/gabarito.yaml").read_text())
q = next(p for p in gab if p["id"] == "q17")
print(f"q17: {q['pergunta']}\nâncora: {q['frase_ancora']!r}\n")

with conectar() as cx, cx.cursor() as cur:
    cur.execute("""SELECT id, caminho_secao FROM chunks_nvidia WHERE estrategia='estrutural-v1'
                   AND texto ILIKE %s ORDER BY id""", (f"%{q['frase_ancora']}%",))
    ancoras = cur.fetchall()
print(f"chunks do corpus que contêm a âncora: {[a['id'] for a in ancoras]}")
for a in ancoras:
    print(f"    {a['id']}: {a['caminho_secao'][:90]}")

denso = buscar_denso_bruto(q["pergunta"], k=20)
lexical = buscar_lexical_bruto(q["pergunta"], k=20)
for k_rrf, pl_ in ((10, 0.3), (20, 0.5)):
    fundido = fundir_rrf({"denso": denso, "lexical": lexical},
                         {"denso": 1.0, "lexical": pl_}, k_rrf)
    uniao = [pa for pa, _ in fundido]
    lg = logits_de(q["pergunta"], uniao)
    ids_anc = {a["id"] for a in ancoras}
    print(f"\n--- K={k_rrf} peso_lex={pl_} · união={len(uniao)} ---")
    for rotulo, pool in (("união INTEIRA (produção, pipeline.py)", uniao),
                         ("top-20 da fusão (harness, --geracao)", uniao[:20]),
                         ("20 densos (rerank_denso)", [pa for pa, _ in denso])):
        ordem = sorted(pool, key=lambda pa: -lg[pa.chunk_id])
        pos = next((i for i, pa in enumerate(ordem, 1) if pa.chunk_id in ids_anc), None)
        no_pool = [pa.chunk_id for pa in pool if pa.chunk_id in ids_anc]
        print(f"  {rotulo:40} âncora no pool: {no_pool or 'NÃO'}  posição: {pos}  "
              f"{'top-5' if pos and pos<=5 else ('top-10' if pos and pos<=10 else 'FORA do top-10')}")
