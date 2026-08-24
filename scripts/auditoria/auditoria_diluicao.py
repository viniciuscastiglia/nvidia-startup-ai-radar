"""Item 4: a curva de diluição de D-034 aguenta mais execuções? E o enchimento sintético vale?"""
import sys, importlib.util, statistics as st
from pathlib import Path
sys.path.insert(0, "/Users/viniciustavarescastiglia/case-nvidia")

spec = importlib.util.spec_from_file_location(
    "vr", "/Users/viniciustavarescastiglia/case-nvidia/scripts/verificar_reranker.py")
vr = importlib.util.module_from_spec(spec); spec.loader.exec_module(vr)

TAMANHOS = (64, 128, 200, 300, 450, 600, 800, 1200, 2000)
N_EXEC = 4

print("=== A. MESMO teste de D-034, 4 execuções novas (enchimento off-topic) ===")
obs = {t: [] for t in TAMANHOS}
n_resp = vr.n_tokens(vr.RESPOSTA)
for exec_i in range(N_EXEC):
    for alvo in TAMANHOS:
        b = vr.encher(max(0, alvo - n_resp)) + " " + vr.RESPOSTA
        logits, _, err = vr._ranquear(vr.QUERY, [b])
        if err:
            print(f"  ERRO {err}"); break
        obs[alvo].append(logits[0])
    print(f"  execução {exec_i+1} ok")

D034 = {64: [-7.96,-7.96], 200: [-9.10,-4.55], 450: [-10.24,-6.83], 600: [-5.69,-4.55],
        800: [-9.10,-9.10], 1200: [-10.24,-11.38], 2000: [-12.52,-10.24]}
print(f"\n  {'tam':>6}{'execuções novas':>44}{'min':>9}{'max':>9}{'+D-034 min':>12}{'+D-034 max':>12}")
for t in TAMANHOS:
    v = obs[t]
    todos = v + D034.get(t, [])
    print(f"  {t:>6}{'  '.join(f'{x:+7.2f}' for x in v):>44}{min(v):>9.2f}{max(v):>9.2f}"
          f"{min(todos):>12.2f}{max(todos):>12.2f}")

baixo = [x for t in (64,128,200,300,450,600) for x in obs[t] + D034.get(t, [])]
alto  = [x for t in (800,1200,2000)          for x in obs[t] + D034.get(t, [])]
p800  = obs[800] + D034[800]
p600  = obs[600] + D034[600]
p1200 = obs[1200] + D034[1200]
print(f"\n  faixa 64-600 (n={len(baixo)}): [{min(baixo):+.2f}, {max(baixo):+.2f}] média {st.mean(baixo):+.2f}")
print(f"  faixa 800+   (n={len(alto)}):  [{min(alto):+.2f}, {max(alto):+.2f}] média {st.mean(alto):+.2f}")
print(f"  as duas faixas se sobrepõem? {'SIM' if min(baixo) < max(alto) else 'não'}")
print(f"  600 vs 800: [{min(p600):+.2f},{max(p600):+.2f}] vs [{min(p800):+.2f},{max(p800):+.2f}]"
      f" -> fronteira em 600-800 {'SUSTENTADA' if max(p800) < min(p600) else 'NÃO sustentada'}")
print(f"  600 vs 1200: [{min(p600):+.2f},{max(p600):+.2f}] vs [{min(p1200):+.2f},{max(p1200):+.2f}]"
      f" -> queda depois de 1200 {'SUSTENTADA' if max(p1200) < min(p600) else 'NÃO sustentada'}")

print("\n=== B. O MESMO, com texto REAL do corpus (chunks vizinhos, mesmo documento) ===")
print("    É o que um TETO_TOKENS maior de fato produziria: mais texto SOBRE O MESMO produto.\n")
import yaml, tiktoken
from src.db import conectar
gab = yaml.safe_load(Path("/Users/viniciustavarescastiglia/case-nvidia/data/avaliacao/gabarito.yaml").read_text())
q19 = next(p for p in gab if p["id"] == "q19")

with conectar() as cx, cx.cursor() as cur:
    cur.execute("""SELECT id, texto_indexado, texto FROM chunks_nvidia
                   WHERE estrategia='estrutural-v1' AND documento_url=%s ORDER BY id""",
                (q19["url_esperada"],))
    chunks = cur.fetchall()

i_anc = next(i for i, c in enumerate(chunks)
             if q19["frase_ancora"].lower() in c["texto"].lower())
print(f"    doc: {q19['url_esperada']}  ({len(chunks)} chunks, âncora no índice {i_anc})")

acumulado = chunks[i_anc]["texto_indexado"]
crescente = [acumulado]
j, k = i_anc - 1, i_anc + 1
while j >= 0 or k < len(chunks):          # cresce alternando para os dois lados
    if k < len(chunks):
        acumulado = acumulado + "\n\n" + chunks[k]["texto"]; k += 1
        crescente.append(acumulado)
    if j >= 0:
        acumulado = chunks[j]["texto"] + "\n\n" + acumulado; j -= 1
        crescente.append(acumulado)

print(f"    {'tam (tok)':>10}{'logit da âncora (2 execuções)':>34}")
for texto in crescente:
    n = vr.n_tokens(texto)
    l1, _, e1 = vr._ranquear(q19["pergunta"], [texto])
    l2, _, e2 = vr._ranquear(q19["pergunta"], [texto])
    if e1 or e2:
        print(f"    {n:>10}  ERRO {e1 or e2}"); break
    print(f"    {n:>10}{l1[0]:>17.4f}{l2[0]:>17.4f}")
