"""Qual a janela do `rerank-qa-mistral-4b`, o único reranker vivo depois do EOL de 25/08?

D-034 mediu 8.192 tokens CONJUNTOS no `llama-nemotron-rerank-1b-v2`, que morreu. Esse número é o
que sustenta `TETO_TOKENS = 450` em `src/rag/chunking.py` — e D-034 existe precisamente porque o
teto estava sustentado por um fato falso antes ("a janela típica de um cross-encoder é 512").
Deixar o 450 apoiado num fato sobre um modelo extinto recriaria o bug que D-034 foi escrita para
matar.

O `verificar_reranker.py` bisseca em [7000, 8600], faixa herdada do modelo 1B. Este script
BRACKETA primeiro por sondagem exponencial e só então bisseca — porque um 4B pode ter janela de
512, de 8k ou de 32k, e chutar a faixa é o erro que se está corrigindo.

Uso:  python scripts/auditoria/janela_rerank_qa_mistral_4b.py
"""

import importlib.util
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAIZ))

spec = importlib.util.spec_from_file_location("vr", str(RAIZ / "scripts" / "verificar_reranker.py"))
vr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vr)

from src.config import RERANK

chamadas = 0


def recusa(query: str, tam: int) -> str | None:
    """`truncate=None` faz a API RECUSAR em vez de cortar em silêncio (o truque de D-034)."""
    global chamadas
    chamadas += 1
    _, _, err = vr._ranquear(query, [vr.encher(tam)], truncate=None)
    return err


def bracketar(query: str) -> tuple[int, int] | None:
    """Acha [aceita, recusa] por sondagem exponencial, sem supor a ordem de grandeza."""
    anterior = 0
    for tam in (256, 1024, 4096, 16384, 65536):
        err = recusa(query, tam)
        marca = "RECUSA" if err else "aceita"
        print(f"      {tam:>6} tok -> {marca}")
        if err:
            return (anterior, tam) if anterior else (0, tam)
        anterior = tam
    return None


def main() -> int:
    print(f"Reranker sob teste: {RERANK.modelo}")
    print(f"Endpoint: {RERANK.url}\n")

    print("1. A API denuncia o limite quando o payload OMITE `truncate`?")
    err = recusa(vr.QUERY, 65536)
    print(f"   {err or 'respondeu 200 — corta em silêncio mesmo sem o parâmetro'}\n")

    print("2. BRACKET + BISSECÇÃO, com duas queries de tamanhos diferentes.")
    print("   Se o corte anda junto com a query, a janela é CONJUNTA — e aí o orçamento real")
    print("   do chunk é 'janela menos a maior consulta plausível'.\n")

    somas = []
    for nome, q in (("curta", vr.QUERY_CURTA), ("longa", vr.QUERY_LONGA)):
        nq = vr.n_tokens(q)
        print(f"   query {nome} ({nq} tok):")
        faixa = bracketar(q)
        if not faixa:
            print("      nenhuma recusa até 65536 — janela maior que a faixa sondada")
            continue
        lo, hi = faixa
        while hi - lo > 8:
            meio = (lo + hi) // 2
            if recusa(q, meio):
                hi = meio
            else:
                lo = meio
        soma = lo + nq
        somas.append((nome, nq, lo, soma))
        print(f"      maior passagem aceita ~{lo} tok  ·  passagem + query = {soma}")
        print(f"      mensagem no limite: {recusa(q, hi)}\n")

    if len(somas) == 2:
        (_, nq1, _, s1), (_, nq2, _, s2) = somas
        print(f"3. CONJUNTA? as queries diferem em {abs(nq2 - nq1)} tokens e as somas em "
              f"{abs(s2 - s1)}.")
        print("   Soma ~invariante = janela conjunta (o que D-034 mediu no 1B).")
        print("   Soma variando junto com a query = janela só da passagem.\n")

    print("4. REPETIBILIDADE do logit — a mesma passagem, 3 chamadas independentes.")
    print("   D-034 registrou variação; a revisão da sessão 03 mediu 36/36 idênticos.")
    print("   O 4B precisa do seu próprio número: é ele que decide se alguma lógica pode")
    print("   depender de margem pequena.")
    global chamadas
    vistos = []
    for i in range(3):
        chamadas += 1
        logits, ms, err = vr._ranquear(vr.QUERY, [vr.RESPOSTA])
        if err:
            print(f"   execução {i + 1}: ERRO {err}")
            break
        vistos.append(logits[0])
        print(f"   execução {i + 1}: logit = {logits[0]:.6f}  ({ms:.0f} ms)")
    if len(vistos) == 3:
        espalhamento = max(vistos) - min(vistos)
        print(f"   espalhamento: {espalhamento:.6f}  -> "
              f"{'IDÊNTICOS' if espalhamento == 0 else 'VARIAM'}")

    print(f"\n{'=' * 78}\nchamadas de API gastas: {chamadas}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
