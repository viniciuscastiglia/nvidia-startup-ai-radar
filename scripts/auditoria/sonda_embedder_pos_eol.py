"""Qual embedder substitui o `llama-nemotron-embed-1b-v2`, morto em 25/08/2026? Decide D-046.

A sonda é a de D-014 (a mesma de `smoke_nvidia.teste_embedding`), rodada lado a lado nos dois
candidatos vivos, para que a escolha saia de número e não de família de modelo.

REGRA DE DESEMPATE, FIXADA ANTES DE MEDIR (plano da sessão 05, regra 1)
-----------------------------------------------------------------------
Adotar o `nemotron-3-embed-1b` SÓ SE as duas condições valerem:
  (a) a separação crosslingual dele bater a do VL por >= 1.5x, E
  (b) a truncagem local 2048->1024 preservar a separação — porque ele RECUSA `dimensions=1024`
      (HTTP 400, medido em 25/08, como D-014 já registrava), e a coluna indexada é vector(1024).
Se qualquer uma falhar, ou se ficarem dentro de 1.5x, o VL vence por custo arquitetural:
schema, índice HNSW e D-029 ficam intactos. O empate em si vira o motivo escrito em D-046.

Uso:  python scripts/auditoria/sonda_embedder_pos_eol.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import httpx

from src.config import EMBEDDING, tem_credencial
from scripts.smoke_nvidia import cosseno

URL = f"{EMBEDDING.base_url}/embeddings"

CANDIDATOS = [
    # (modelo, dimensao_pedida ou None se o modelo recusar o parâmetro)
    ("nvidia/llama-nemotron-embed-vl-1b-v2", 1024),
    ("nvidia/nemotron-3-embed-1b", None),
]

# Exatamente os textos de `smoke_nvidia.teste_embedding`, para que os números desta sonda
# sejam comparáveis aos que D-014 registrou para o modelo que morreu.
CONSULTA_PT = "startup que precisa reduzir o custo e a latência de inferência de LLM"
PT_RELEVANTE = (
    "A empresa migrou da API externa para inferência self-hosted e reduziu o custo por "
    "token em 60%, usando quantização e batching dinâmico."
)
PT_IRRELEVANTE = (
    "A padaria do bairro abre às seis da manhã e vende pão francês, sonho e café coado."
)
EN_RELEVANTE = (
    "NVIDIA NIM packages an optimized inference engine with an OpenAI-compatible API, "
    "cutting latency and cost per token for self-hosted large language models."
)

# Uma pergunta REAL do gabarito (q19) contra o chunk que a responde. O corpus é EN e a
# pergunta é PT: é o caminho principal do RAG (D-014), não um caso de borda.
CONSULTA_Q19 = "qual engine de inferência o NVIDIA NIM usa por baixo?"
Q19_RELEVANTE = (
    "NVIDIA NIM selects the most suitable inference backend for the model and hardware, "
    "which may be TensorRT-LLM, vLLM or SGLang."
)

MARGEM_MINIMA = 0.10   # a de smoke_nvidia: abaixo disso é ruído numérico, não separação


def embedar(textos: list[str], input_type: str, modelo: str, dim: int | None) -> list[list[float]]:
    payload: dict = {
        "input": textos,
        "model": modelo,
        "input_type": input_type,
        "encoding_format": "float",
        "truncate": "END",
    }
    if dim is not None:
        payload["dimensions"] = dim
    r = httpx.post(
        URL,
        headers={"Authorization": f"Bearer {EMBEDDING.api_key}", "Accept": "application/json"},
        json=payload,
        timeout=90.0,
    )
    r.raise_for_status()
    dados = r.json()
    return [x["embedding"] for x in sorted(dados["data"], key=lambda d: d["index"])]


def separacoes(q: list[float], ps: list[list[float]], corte: int | None = None) -> dict:
    """As três similaridades e as duas margens. `corte` trunca localmente antes de comparar."""
    if corte:
        q = q[:corte]
        ps = [p[:corte] for p in ps]
    pt_rel, pt_irr, en_rel, q19_rel = (cosseno(q, p) for p in ps)
    return {
        "pt_rel": pt_rel, "pt_irr": pt_irr, "en_rel": en_rel, "q19_rel": q19_rel,
        "margem_pt": pt_rel - pt_irr,
        "margem_cross": en_rel - pt_irr,
    }


def imprimir(rotulo: str, s: dict) -> None:
    ok_pt = "ok" if s["margem_pt"] >= MARGEM_MINIMA else "FALHOU"
    ok_cx = "ok" if s["margem_cross"] >= MARGEM_MINIMA else "FALHOU"
    print(f"   {rotulo}")
    print(f"      PT  relevante {s['pt_rel']:.4f}  vs irrelevante {s['pt_irr']:.4f}"
          f"   -> margem {s['margem_pt']:+.4f}  ({ok_pt})")
    print(f"      EN  crosslingual {s['en_rel']:.4f}  vs irrelevante PT {s['pt_irr']:.4f}"
          f"   -> margem {s['margem_cross']:+.4f}  ({ok_cx})")
    print(f"      q19 PT->EN real  {s['q19_rel']:.4f}")


def main() -> int:
    if not tem_credencial():
        print("Sem credencial no .env")
        return 1

    passagens = [PT_RELEVANTE, PT_IRRELEVANTE, EN_RELEVANTE, Q19_RELEVANTE]
    resultados: dict[str, dict] = {}

    for modelo, dim in CANDIDATOS:
        print(f"\n{'=' * 78}\n{modelo}   (dimensions={dim if dim else 'nativo 2048'})")
        try:
            q = embedar([CONSULTA_PT], "query", modelo, dim)[0]
            ps = embedar(passagens, "passage", modelo, dim)
            q19 = embedar([CONSULTA_Q19], "query", modelo, dim)[0]
        except httpx.HTTPStatusError as e:
            print(f"   INDISPONÍVEL: {e.response.status_code} {e.response.text[:120]}")
            continue

        s = separacoes(q, ps)
        s["q19_rel"] = cosseno(q19, ps[3])
        print(f"   dims devolvidas: {len(q)}")
        imprimir("nativo:", s)
        resultados[modelo] = s

        # Condição (b) da regra de desempate: o modelo que recusa `dimensions=1024` só serve
        # se a truncagem LOCAL para 1024 preservar a separação — é ela que preencheria a
        # coluna indexada vector(1024).
        if dim is None and len(q) > 1024:
            st = separacoes(q, ps, corte=1024)
            st["q19_rel"] = cosseno(q19[:1024], ps[3][:1024])
            imprimir("truncado localmente para 1024:", st)
            delta = st["margem_cross"] - s["margem_cross"]
            sinal = "GANHO" if delta > 0 else "perda"
            print(f"      efeito da truncagem na margem crosslingual: {delta:+.4f} ({sinal})")
            resultados[modelo + " @1024-truncado"] = st

        # Para o VL, a propriedade de D-029: pedir 1024 à API == truncar 2048 localmente?
        if dim == 1024:
            ps2048 = embedar(passagens, "passage", modelo, 2048)
            cos_matry = cosseno(ps[0], ps2048[0][:1024])
            veredito = ("EQUIVALENTE" if cos_matry > 0.9999
                        else "PRÓXIMO" if cos_matry > 0.99 else "DIFERENTE")
            print(f"      Matryoshka (D-029): cos(api_1024, trunc_local_1024) = "
                  f"{cos_matry:.8f}  -> {veredito}")

    print(f"\n{'=' * 78}\nDESEMPATE (regra fixada antes de medir)")
    vl = resultados.get("nvidia/llama-nemotron-embed-vl-1b-v2")
    n3 = resultados.get("nvidia/nemotron-3-embed-1b")
    n3t = resultados.get("nvidia/nemotron-3-embed-1b @1024-truncado")
    if not (vl and n3):
        print("   Um dos candidatos não respondeu — decisão não automatizável.")
        return 0

    razao = n3["margem_cross"] / vl["margem_cross"] if vl["margem_cross"] > 0 else float("inf")
    cond_a = razao >= 1.5
    cond_b = bool(n3t and n3t["margem_cross"] >= MARGEM_MINIMA
                  and n3t["margem_pt"] >= MARGEM_MINIMA)
    print(f"   (a) margem crosslingual n3/VL = {n3['margem_cross']:.4f}/{vl['margem_cross']:.4f}"
          f" = {razao:.2f}x   (precisa >= 1.50x) -> {'passa' if cond_a else 'NÃO passa'}")
    print(f"   (b) truncagem local 2048->1024 preserva as duas margens -> "
          f"{'passa' if cond_b else 'NÃO passa'}")
    if cond_a and cond_b:
        print("\n   => nemotron-3-embed-1b, e o schema muda (coluna 1024 por truncagem local).")
    else:
        print("\n   => llama-nemotron-embed-vl-1b-v2. Vence por custo arquitetural:")
        print("      vector(1024) + HNSW e vector(2048) sem índice ficam como estão, e D-029")
        print("      continua valendo. O empate é o motivo, e vai escrito em D-046.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
