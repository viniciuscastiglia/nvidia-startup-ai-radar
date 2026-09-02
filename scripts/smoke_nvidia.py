"""Smoke test do build.nvidia.com — as três capacidades que o projeto vai usar.

POR QUE ISTO É UM SCRIPT VERSIONADO E NÃO UM `curl` DESCARTÁVEL
---------------------------------------------------------------
1. É evidência reproduzível: qualquer pessoa roda e vê os mesmos números.
2. É a fonte dos números de latência do sistema — inclusive os que vão para o vídeo.
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

POR QUE ESTE SCRIPT DISTINGUE **LENTO** DE **MORTO** (D-080)
-------------------------------------------------------------
D-079 catalogou tres assinaturas de "nao serve": 410 = morte anunciada, 404 com uuid =
entitlement, 404 texto puro = nome inexistente. Em 02/09 apareceu a QUARTA, e ela nao estava
no catalogo: **vivo, porem acima do relogio**. O modelo de producao respondia HTTP 200 com o
primeiro token entre 27 e 68 s, e este smoke — que rodava com TIMEOUT=60 fixo — imprimia
`[FALHOU] ReadTimeout`, a MESMA palavra que usa para morte.

O custo do erro e assimetrico e por isso ele importa: o CLAUDE.md manda rodar este script antes
de gravar o video e antes de entregar, e o chama de "a unica defesa que existe". Ler um timeout
como EOL faz abrir uma migracao de modelo desnecessaria a poucos dias da entrega.

Entao um timeout aqui **nunca mais e conclusao** — e gatilho de `diagnosticar_chat()`, que
classifica pela resposta real do endpoint. E o estado LENTO existe separado de FALHOU: a
capacidade esta la, o relogio e que nao esta.
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
# O chat usa o teto da PRODUCAO, nao um numero proprio: um smoke mais impaciente que o sistema
# reprova o que o sistema aceita. Piso de 60 s para o caso de alguem baixar LLM_TIMEOUT.
TIMEOUT_CHAT = max(LLM.timeout, 60.0)
# Acima disto a chamada passa, mas o estado vira LENTO: e o sinal de que o endpoint degradou
# antes de morrer. 10 s e folgado para um prompt de uma frase — o normal medido e sub-segundo.
LATENCIA_ESPERADA_MS = 10_000.0
RESULTADOS: list[dict] = []


def cabecalhos(api_key: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}


def cosseno(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return num / (na * nb) if na and nb else 0.0


def registrar(nome: str, estado: bool | str, ms: float | None, detalhe: str) -> None:
    """`estado` e True/False (compatibilidade) ou o literal "LENTO".

    LENTO conta como capacidade OK no placar e no codigo de saida — a capacidade existe. O que
    ele nao faz e passar despercebido: aparece na tabela do relatorio e no rodape.
    """
    marca = {True: "PASSOU", False: "FALHOU", "LENTO": "LENTO "}[estado]
    ok = estado is not False
    RESULTADOS.append({"nome": nome, "ok": ok, "estado": marca.strip(),
                       "ms": ms, "detalhe": detalhe})
    lat = f"{ms:.0f} ms" if ms is not None else "—"
    print(f"  [{marca}] {nome}  ({lat})")
    for linha in detalhe.splitlines():
        print(f"          {linha}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. CHAT COMPLETION
# ─────────────────────────────────────────────────────────────────────────────
def diagnosticar_chat() -> tuple[str, str]:
    """POR QUE UM TIMEOUT NAO E MAIS UMA CONCLUSAO (D-080).

    Chamado so quando a chamada principal falha. Faz duas sondas baratas e devolve
    `(rotulo, detalhe)`, onde o rotulo e um dos de D-079 mais os dois que faltavam:

        TRANSPORTE  nem a sonda de CONTROLE respondeu -> rede ou credencial, nao o modelo
        VIVO-LENTO  HTTP 200 chega, so que depois do relogio -> a QUARTA assinatura

    A sonda de controle vem primeiro de proposito: sem ela, "o modelo nao responde" e
    indistinguivel de "nada responde", e a conclusao erraria de alvo.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from sondar_catalogo import _classificar   # UMA definicao de "morto" no repositorio

    try:
        httpx.post(
            f"{LLM.base_url}/chat/completions",
            headers=cabecalhos(LLM.api_key),
            json={"model": "modelo/inexistente-sonda-de-controle",
                  "messages": [{"role": "user", "content": "x"}], "max_tokens": 1},
            timeout=15.0,
        )
    except Exception as exc:  # noqa: BLE001
        return ("TRANSPORTE",
                f"nem a sonda de controle respondeu ({type(exc).__name__}). O problema esta na "
                f"rede ou na credencial — NAO ha evidencia sobre o modelo.")

    try:
        t0 = time.perf_counter()
        with httpx.stream(
            "POST",
            f"{LLM.base_url}/chat/completions",
            headers=cabecalhos(LLM.api_key),
            json={"model": LLM.modelo, "temperature": 0, "max_tokens": 8, "stream": True,
                  "messages": [{"role": "user", "content": "Responda apenas: ok"}]},
            timeout=TIMEOUT_CHAT * 2,
        ) as r:
            if r.status_code >= 400:
                return _classificar(r.status_code, r.read().decode("utf-8", "replace"))
            for linha in r.iter_lines():
                if linha.strip():
                    return ("VIVO-LENTO",
                            f"HTTP 200 — primeiro token em {(time.perf_counter() - t0):.0f} s. "
                            f"O modelo esta VIVO; o que estourou foi o relogio, nao o catalogo.")
            return ("VAZIO", "HTTP 200 e nenhum token — endpoint degradado, mas nao aposentado.")
    except Exception as exc:  # noqa: BLE001
        return ("FALHA", f"{type(exc).__name__} tambem no streaming — reexecutar antes de concluir.")


# As quatro assinaturas que NAO sao morte, e o que fazer com cada uma. Existe para que quem le a
# saida do smoke as 2 da manha nao precise abrir D-079 nem este arquivo.
CONDUTA = {
    "EOL": "MORTE REAL, anunciada com data. Trocar LLM_MODEL — e so isto justifica migracao.",
    "SEM ACESSO": "entitlement: o modelo roda, esta conta nao alcanca. NAO e morte.",
    "INEXISTENTE": "o nome nao existe no catalogo. Erro de digitacao ou de versao.",
    "VIVO-LENTO": "NAO MIGRE. Subir LLM_TIMEOUT, ou aceitar a latencia e planejar o video com ela.",
    "VAZIO": "endpoint degradado. Reexecutar antes de concluir qualquer coisa.",
    "TRANSPORTE": "olhe rede e credencial ANTES de olhar o modelo.",
    "FALHA": "inconclusivo — reexecutar.",
}


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
            timeout=TIMEOUT_CHAT,
        )
        ms = (time.perf_counter() - t0) * 1000
        if r.status_code >= 400:
            rotulo, detalhe = diagnosticar_chat()
            estado = "LENTO" if rotulo in ("VIVO-LENTO", "VAZIO") else False
            registrar("chat completion", estado, None,
                      f"modelo: {LLM.modelo}\nHTTP {r.status_code}\n"
                      f"diagnostico: {rotulo} — {detalhe}\n-> {CONDUTA[rotulo]}")
            return
        dados = r.json()
        texto = dados["choices"][0]["message"]["content"].strip()
        uso = dados.get("usage", {})
        # O modelo de 01/09 em diante emite o RACIOCINIO dentro do `content` no caminho cru
        # (D-079). Quem le "resposta: Here's a thinking process" sem saber disso conclui que o
        # modelo quebrou. Nao quebrou — e o caminho de PRODUCAO nao e afetado, porque
        # `with_structured_output(method="json_schema")` devolve so o schema (medido em 02/09).
        vaza_raciocinio = texto[:400].lower().startswith(("here's a thinking", "here is a thinking",
                                                          "<think", "thinking process"))
        nota_raciocinio = (
            "\nNOTA: o `content` cru comeca com o raciocinio do modelo. Isto e esperado (D-079) "
            "e NAO afeta a producao — `json_schema` devolve so o schema."
        ) if vaza_raciocinio else ""
        lento = ms > LATENCIA_ESPERADA_MS
        aviso = (
            f"\nLENTO: {ms / 1000:.0f} s contra ~{LATENCIA_ESPERADA_MS / 1000:.0f} s esperados. "
            f"A capacidade EXISTE — isto nao e EOL.\n"
            f"-> {CONDUTA['VIVO-LENTO']}"
        ) if lento else ""
        registrar(
            "chat completion",
            "LENTO" if lento else True,
            ms,
            f"modelo: {LLM.modelo}\n"
            f"tokens: {uso.get('prompt_tokens', '?')} prompt + "
            f"{uso.get('completion_tokens', '?')} completion\n"
            f"resposta: {texto[:160]}{nota_raciocinio}{aviso}",
        )
    except Exception as exc:  # noqa: BLE001
        # AQUI ESTAVA O DEFEITO DE D-080: um ReadTimeout virava "[FALHOU]", a mesma palavra
        # usada para morte. Agora ele so ABRE o diagnostico.
        rotulo, detalhe = diagnosticar_chat()
        estado = "LENTO" if rotulo in ("VIVO-LENTO", "VAZIO") else False
        registrar("chat completion", estado, None,
                  f"modelo: {LLM.modelo}\n"
                  f"a chamada direta falhou: {type(exc).__name__} (teto {TIMEOUT_CHAT:.0f} s)\n"
                  f"diagnostico: {rotulo} — {detalhe}\n-> {CONDUTA[rotulo]}")


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
    # O rótulo do rerank segue o PROVEDOR, não um if binário. A versão anterior era
    # `cohere_modelo if provedor == "cohere" else RERANK.modelo`, e com RERANK_PROVEDOR=nenhum
    # ela caía no else e publicava "reranking | passou | nvidia/rerank-qa-mistral-4b" — o nome de
    # um modelo MORTO desde 27/08 (D-064), ao lado de um "passou", num modelo que nem foi chamado.
    # Este arquivo vira `docs/smoke-nvidia.md`, que é artefato commitado e lido por quem avalia:
    # é a mesma "instrução contaminada" do achado 5 de D-066, agora na saída do instrumento que
    # existe justamente para denunciar modelo morto.
    modelos = {
        "chat completion": LLM.modelo,
        "embedding": EMBEDDING.modelo,
        "reranking": {
            "cohere": RERANK.cohere_modelo,
            "nvidia": RERANK.modelo,
        }.get(RERANK.provedor, "— passo 7 desligado"),
    }
    for res in RESULTADOS:
        lat = f"{res['ms']:.0f} ms" if res["ms"] is not None else "—"
        linhas.append(
            f"| {res['nome']} | {res.get('estado', 'PASSOU').lower()} | {lat} | "
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
    lentos = [r["nome"] for r in RESULTADOS if r.get("estado") == "LENTO"]
    print("\n" + "=" * 78)
    ressalva = f"  ({len(lentos)} LENTO: {', '.join(lentos)})" if lentos else ""
    print(f"{passou}/{len(RESULTADOS)} capacidades OK{ressalva}  ·  "
          f"relatório em {destino.relative_to(Path.cwd())}")
    if lentos:
        # LENTO nao derruba o codigo de saida: a capacidade existe. Mas quem le precisa saber
        # que o numero de latencia do video vai sair daqui, e que isto NAO e EOL (D-080).
        print("LENTO = a capacidade existe e o relógio estourou. NÃO é EOL, não migre o modelo.")
    print("=" * 78)
    return 0 if passou == len(RESULTADOS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
