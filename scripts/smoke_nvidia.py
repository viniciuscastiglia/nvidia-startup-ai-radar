"""Smoke test do build.nvidia.com — as três capacidades que o projeto vai usar.

POR QUE ISTO É UM SCRIPT VERSIONADO E NÃO UM `curl` DESCARTÁVEL
---------------------------------------------------------------
1. É evidência reproduzível: o avaliador roda e vê os mesmos números.
2. É a fonte dos números de latência que vão para o vídeo.
3. É o teste de regressão de "os créditos ainda funcionam" ao longo dos 18 dias.

POR QUE HTTP CRU E NÃO `langchain-openai` AQUI
-----------------------------------------------
O objetivo do smoke test é provar que o ENDPOINT funciona. Se passasse por uma abstração,
uma falha seria ambígua — problema do endpoint ou da biblioteca? Aqui a falha é do endpoint.
Os agentes é que usam langchain; o smoke test não.

O QUE ESTE SCRIPT PROVA ALÉM DE "RESPONDE 200"
-----------------------------------------------
- embedding: que a dimensão Matryoshka pedida é a devolvida
- embedding: que a semântica funciona EM PORTUGUÊS (passagem relevante > irrelevante)
- embedding: que funciona CROSSLINGUAL — consulta em português contra passagem em inglês.
  Isso não é curiosidade: a base RAG da NVIDIA é em inglês e os perfis das startups em
  português. Se o crosslingual não funcionasse, a arquitetura inteira do RAG mudaria.
- rerank: qual dos paths candidatos do endpoint de ranking realmente responde
"""

from __future__ import annotations

import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import EMBEDDING, LLM, RERANK, tem_credencial  # noqa: E402

TIMEOUT = 60.0
RESULTADOS: list[dict] = []


def cabecalhos(api_key: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}


def cosseno(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return num / (na * nb) if na and nb else 0.0


def registrar(nome: str, ok: bool, ms: float | None, detalhe: str) -> None:
    RESULTADOS.append({"nome": nome, "ok": ok, "ms": ms, "detalhe": detalhe})
    marca = "PASSOU" if ok else "FALHOU"
    lat = f"{ms:.0f} ms" if ms is not None else "—"
    print(f"  [{marca}] {nome}  ({lat})")
    for linha in detalhe.splitlines():
        print(f"          {linha}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. CHAT COMPLETION
# ─────────────────────────────────────────────────────────────────────────────
def teste_chat() -> None:
    print("\n1. CHAT COMPLETION — endpoint OpenAI-compatible")
    payload = {
        "model": LLM.modelo,
        "messages": [
            {
                "role": "user",
                "content": "Responda em uma frase curta, em português: o que é o NVIDIA Inception?",
            }
        ],
        "temperature": LLM.temperatura,
        "max_tokens": 120,
    }
    try:
        t0 = time.perf_counter()
        r = httpx.post(
            f"{LLM.base_url}/chat/completions",
            headers=cabecalhos(LLM.api_key),
            json=payload,
            timeout=TIMEOUT,
        )
        ms = (time.perf_counter() - t0) * 1000
        r.raise_for_status()
        dados = r.json()
        texto = dados["choices"][0]["message"]["content"].strip()
        uso = dados.get("usage", {})
        registrar(
            "chat completion",
            True,
            ms,
            f"modelo: {LLM.modelo}\n"
            f"tokens: {uso.get('prompt_tokens', '?')} prompt + "
            f"{uso.get('completion_tokens', '?')} completion\n"
            f"resposta: {texto[:160]}",
        )
    except Exception as exc:  # noqa: BLE001
        registrar("chat completion", False, None, f"{type(exc).__name__}: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# 2. EMBEDDING
# ─────────────────────────────────────────────────────────────────────────────
def _embed(textos: list[str], input_type: str, dimensao: int | None) -> tuple[list[list[float]], float]:
    payload: dict = {
        "input": textos,
        "model": EMBEDDING.modelo,
        "input_type": input_type,      # NeMo Retriever é ASSIMÉTRICO: query != passage
        "encoding_format": "float",
        "truncate": "END",
    }
    if dimensao is not None:
        payload["dimensions"] = dimensao   # Matryoshka

    t0 = time.perf_counter()
    r = httpx.post(
        f"{EMBEDDING.base_url}/embeddings",
        headers=cabecalhos(EMBEDDING.api_key),
        json=payload,
        timeout=TIMEOUT,
    )
    ms = (time.perf_counter() - t0) * 1000
    r.raise_for_status()
    dados = r.json()
    vetores = [item["embedding"] for item in sorted(dados["data"], key=lambda d: d["index"])]
    return vetores, ms


def teste_embedding() -> None:
    print(f"\n2. EMBEDDING — {EMBEDDING.modelo} (português + crosslingual)")

    consulta_pt = "startup que precisa reduzir o custo e a latência de inferência de LLM"
    passagem_pt_relevante = (
        "A empresa migrou da API externa para inferência self-hosted e reduziu o custo por "
        "token em 60%, usando quantização e batching dinâmico."
    )
    passagem_pt_irrelevante = (
        "A padaria do bairro abre às seis da manhã e vende pão francês, sonho e café coado."
    )
    passagem_en_relevante = (
        "NVIDIA NIM packages an optimized inference engine with an OpenAI-compatible API, "
        "cutting latency and cost per token for self-hosted large language models."
    )

    detalhes: list[str] = []
    ok_geral = True
    ms_total = None

    # 2a. dimensão Matryoshka
    try:
        vetores, ms = _embed([consulta_pt], "query", EMBEDDING.dimensao)
        ms_total = ms
        dim = len(vetores[0])
        bate = dim == EMBEDDING.dimensao
        detalhes.append(
            f"dimensão pedida {EMBEDDING.dimensao} -> devolvida {dim} "
            f"{'(bate)' if bate else '(NÃO BATE — Matryoshka pode não estar sendo aplicada)'}"
        )
        if not bate:
            ok_geral = False
    except Exception as exc:  # noqa: BLE001
        registrar("embedding", False, None, f"{type(exc).__name__}: {exc}")
        return

    # 2b. semântica em português
    try:
        q, _ = _embed([consulta_pt], "query", EMBEDDING.dimensao)
        ps, _ = _embed(
            [passagem_pt_relevante, passagem_pt_irrelevante, passagem_en_relevante],
            "passage",
            EMBEDDING.dimensao,
        )
        sim_pt_rel = cosseno(q[0], ps[0])
        sim_pt_irr = cosseno(q[0], ps[1])
        sim_en_rel = cosseno(q[0], ps[2])

        # Margem mínima, não apenas ">". Descoberto em 22/08 testando o nv-embedqa-e5-v5:
        # ele passava num teste de ">" com 0.3107 contra 0.3096 — diferença de 0.001, que é
        # ruído numérico, não separação semântica. Um teste que aceita isso não testa nada.
        MARGEM = 0.10
        pt_ok = (sim_pt_rel - sim_pt_irr) >= MARGEM
        cross_ok = (sim_en_rel - sim_pt_irr) >= MARGEM
        detalhes.append(
            f"PT  relevante {sim_pt_rel:.4f} vs irrelevante {sim_pt_irr:.4f} "
            f"{'(ok)' if pt_ok else '(FALHOU — semântica em português não separa)'}"
        )
        detalhes.append(
            f"EN  crosslingual {sim_en_rel:.4f} vs irrelevante PT {sim_pt_irr:.4f} "
            f"{'(ok)' if cross_ok else '(FALHOU — crosslingual não funciona; a arquitetura do RAG muda)'}"
        )
        ok_geral = ok_geral and pt_ok and cross_ok
    except Exception as exc:  # noqa: BLE001
        detalhes.append(f"checagem semântica falhou: {type(exc).__name__}: {exc}")
        ok_geral = False

    registrar("embedding", ok_geral, ms_total, "\n".join(detalhes))


# ─────────────────────────────────────────────────────────────────────────────
# 3. RERANKING
# ─────────────────────────────────────────────────────────────────────────────
def teste_rerank() -> None:
    """O passo 7 NO PROVEDOR CONFIGURADO, seja ele qual for (D-068).

    Até 27/08 este teste era NVIDIA hard-coded. Depois que o provedor virou configuração, um
    smoke preso a um fornecedor reportaria 404 com o passo 7 funcionando perfeitamente em outro —
    que é a definição de instrumento quebrado.

    A asserção NÃO é "respondeu 200": é que a passagem #1 (TensorRT-LLM, a única que fala de
    latência de inferência) vá para o TOPO. Um reranker que responde e não ordena passa no teste
    de encanamento e reprova no que se está comprando.
    """
    rotulo = {"cohere": RERANK.cohere_modelo, "nvidia": RERANK.modelo,
              "nenhum": "— passo 7 desligado"}.get(RERANK.provedor, "?")
    print(f"\n3. RERANKING — provedor {RERANK.provedor} · {rotulo}")

    if RERANK.provedor == "nenhum":
        registrar("reranking", True, None,
                  "RERANK_PROVEDOR=nenhum: o passo 7 sai do caminho de propósito e a resposta\n"
                  "vira a ordem da busca híbrida (95% r@1, 100% r@3 — D-046). Não é falha.")
        return

    consulta = "Como reduzir a latência de inferência de um LLM em produção?"
    passagens = [
        "O NVIDIA Inception é um programa gratuito para startups, sem taxa e sem equity.",
        "TensorRT-LLM aplica quantização FP8 e speculative decoding, com ganho de ~3x de throughput.",
        "cuDF acelera operações de pandas em GPU sem mudança de código, com fallback para CPU.",
    ]

    try:
        from src.rag.rerank import _chamar   # o MESMO caminho que a produção usa

        t0 = time.perf_counter()
        scores = _chamar(consulta, passagens)
        ms = (time.perf_counter() - t0) * 1000
        ordem_idx = sorted(range(len(scores)), key=lambda i: -scores[i])
        topo = ordem_idx[0]
        acertou = topo == 1
        ordem = " > ".join(f"#{i}({scores[i]:.4f})" for i in ordem_idx)
        registrar(
            "reranking",
            acertou,
            ms,
            f"provedor: {RERANK.provedor} · modelo: {rotulo}\n"
            f"ordem: {ordem}\n"
            f"topo = passagem #{topo} "
            f"{'(correto — TensorRT-LLM é a resposta certa)' if acertou else '(ERRADO — esperado #1)'}\n"
            f"margem topo->2º: {scores[topo] - scores[ordem_idx[1]]:.4f} "
            f"({'relevance_score em [0,1]' if RERANK.provedor == 'cohere' else 'logit cru'} "
            f"— as escalas NÃO se comparam entre provedores, D-068)",
        )
    except Exception as exc:  # noqa: BLE001
        registrar("reranking", False, None, f"{type(exc).__name__}: {str(exc)[:200]}")


# ─────────────────────────────────────────────────────────────────────────────
def escrever_relatorio() -> Path:
    destino = Path(__file__).resolve().parent.parent / "docs" / "smoke-nvidia.md"
    destino.parent.mkdir(exist_ok=True)
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    linhas = [
        "# Smoke test — build.nvidia.com",
        "",
        f"Gerado por `scripts/smoke_nvidia.py` em {agora}.",
        "",
        "| Capacidade | Resultado | Latência | Modelo |",
        "|---|---|---|---|",
    ]
    modelos = {
        "chat completion": LLM.modelo,
        "embedding": EMBEDDING.modelo,
        "reranking": RERANK.cohere_modelo if RERANK.provedor == "cohere" else RERANK.modelo,
    }
    for res in RESULTADOS:
        lat = f"{res['ms']:.0f} ms" if res["ms"] is not None else "—"
        linhas.append(
            f"| {res['nome']} | {'passou' if res['ok'] else 'falhou'} | {lat} | "
            f"`{modelos.get(res['nome'], '')}` |"
        )
    linhas += ["", "## Detalhes", ""]
    for res in RESULTADOS:
        linhas += [f"### {res['nome']}", "", "```", res["detalhe"], "```", ""]
    destino.write_text("\n".join(linhas), encoding="utf-8")
    return destino


def main() -> int:
    print("=" * 78)
    print("SMOKE TEST — build.nvidia.com")
    print("=" * 78)

    if not tem_credencial():
        print("\nERRO: nenhuma credencial encontrada.")
        print("Crie o arquivo .env (copie de .env.example) e preencha NVIDIA_API_KEY.")
        return 2

    teste_chat()
    teste_embedding()
    teste_rerank()

    destino = escrever_relatorio()
    passou = sum(1 for r in RESULTADOS if r["ok"])
    print("\n" + "=" * 78)
    print(f"{passou}/{len(RESULTADOS)} capacidades OK  ·  relatório em {destino.relative_to(Path.cwd())}")
    print("=" * 78)
    return 0 if passou == len(RESULTADOS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
