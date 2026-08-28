"""Caracterização do Cohere Rerank — o passo 7 desde 28/08 (D-068).

Irmão de `verificar_embedder.py` e `verificar_reranker.py`: mede as PROPRIEDADES do componente,
não se ele responde. São três perguntas, e a terceira é a que decide o roteiro do vídeo.

1. ELE ORDENA? Responder 200 não é reranquear. A passagem que fala de latência de inferência
   precisa subir ao topo. Sem isto, o passo 7 é encanamento caro.

2. QUAL A JANELA? O cross-encoder da NVIDIA aceitava ~6.958 tokens somando query e passagem
   (D-034/D-046), e o maior chunk do corpus tem 446 — folga de 15x. Se o Cohere for mais
   apertado, `LOTE` e o chunking voltam à mesa. Medido por escalada, não por documentação.

3. QUANTAS REQ/MIN ATÉ O 429? A trial documenta **10 req/min no Rerank**, e um run do grafo faz
   ~20-30 chamadas SEQUENCIAIS de rerank — o que daria **~2-3 minutos parados** num vídeo cujo
   teto é 7. D-065 marcou isso como *"a verificar antes de o roteiro depender disso"*. É o que
   este script fecha, com número em vez de estimativa.

O QUE ESTE SCRIPT NÃO FAZ: comparar Cohere com NVIDIA lado a lado. Não dá — o reranker da NVIDIA
devolve 404 desde 27/08, e as escalas de score nem são comparáveis (logit cru vs. [0,1], D-068).
A comparação que resta é por MÉTRICA DE POSIÇÃO, e ela mora em `avaliar_rag.py`.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import RERANK  # noqa: E402
from src.rag.rerank import URL_COHERE, _chamar_cohere  # noqa: E402

CONSULTA = "Como reduzir a latência de inferência de um LLM em produção?"
PASSAGENS = [
    "O NVIDIA Inception é um programa gratuito para startups, sem taxa e sem equity.",
    "TensorRT-LLM aplica quantização FP8 e speculative decoding, com ganho de ~3x de throughput.",
    "cuDF acelera operações de pandas em GPU sem mudança de código, com fallback para CPU.",
]


def prova_de_ordenacao() -> bool:
    print("\n1. ELE ORDENA? (esperado: #1, a única que fala de latência de inferência)")
    t0 = time.perf_counter()
    scores = _chamar_cohere(CONSULTA, PASSAGENS)
    ms = (time.perf_counter() - t0) * 1000
    ordem = sorted(range(len(scores)), key=lambda i: -scores[i])
    for i in ordem:
        print(f"     #{i}  {scores[i]:.4f}  {PASSAGENS[i][:62]}")
    ok = ordem[0] == 1
    print(f"   topo = #{ordem[0]} {'(correto)' if ok else '(ERRADO)'} · "
          f"margem {scores[ordem[0]] - scores[ordem[1]]:.4f} · {ms:.0f} ms")
    print("   NOTA: `relevance_score` vive em [0,1]. NÃO é o logit da NVIDIA e não se compara "
          "com\n         os números de rerank anteriores a 28/08 (D-068).")
    return ok


def janela() -> None:
    print("\n2. QUAL A JANELA? (escalada até a API recusar)")
    print("   maior chunk real do corpus: 446 tokens (D-034)")
    unidade = "palavra " * 1000          # ~1.000 tokens por bloco
    ultimo_ok = 0
    for blocos in (1, 2, 4, 8, 16, 32):
        try:
            _chamar_cohere(CONSULTA, [unidade * blocos])
            ultimo_ok = blocos
            print(f"     ~{blocos * 1000:6d} tokens  OK")
        except httpx.HTTPStatusError as exc:
            print(f"     ~{blocos * 1000:6d} tokens  HTTP {exc.response.status_code} — o limite "
                  f"está entre ~{ultimo_ok * 1000} e ~{blocos * 1000}")
            break
        except Exception as exc:  # noqa: BLE001
            print(f"     ~{blocos * 1000:6d} tokens  {type(exc).__name__}")
            break
    else:
        print("     não recusou até ~32.000 tokens — folga enorme sobre os 446 do corpus")
    if ultimo_ok * 1000 >= 4000:
        print("   VEREDITO: cabe o corpus inteiro com folga; `LOTE=32` e o chunking ficam de pé.")


def throttle(n: int) -> None:
    """A pergunta do vídeo: quantas chamadas SEQUENCIAIS antes de o 429 aparecer, e por quanto."""
    print(f"\n3. THROTTLE — {n} chamadas SEQUENCIAIS, sem pausa (trial documenta 10 req/min)")
    t_inicio = time.perf_counter()
    primeiro_429 = None
    retry_after = None
    latencias: list[float] = []
    for i in range(1, n + 1):
        t0 = time.perf_counter()
        try:
            _chamar_cohere(CONSULTA, PASSAGENS)
            dt = time.perf_counter() - t0
            latencias.append(dt)
            marca = ""
        except httpx.HTTPStatusError as exc:
            dt = time.perf_counter() - t0
            if exc.response.status_code == 429:
                if primeiro_429 is None:
                    primeiro_429 = i
                    retry_after = exc.response.headers.get("retry-after")
                marca = f"  <- HTTP 429 (retry-after: {retry_after or 'ausente'})"
            else:
                marca = f"  <- HTTP {exc.response.status_code}"
        decorrido = time.perf_counter() - t_inicio
        print(f"     #{i:2d}  {dt*1000:6.0f} ms  ·  {decorrido:5.1f} s acumulados{marca}")

    total = time.perf_counter() - t_inicio
    print(f"\n   {n} chamadas em {total:.1f} s  ->  {n / total * 60:.1f} req/min efetivas")
    if primeiro_429:
        print(f"   PRIMEIRO 429 na chamada #{primeiro_429}. O teto da trial é REAL e o vídeo "
              f"precisa contorná-lo.")
    else:
        print(f"   NENHUM 429 em {n} chamadas.")
    if latencias:
        media = sum(latencias) / len(latencias)
        print(f"   latência média por chamada: {media*1000:.0f} ms")
        print(f"\n   PROJEÇÃO PARA A DEMO: um `python -m src.graph` faz ~20-30 chamadas de rerank")
        print(f"   sequenciais -> ~{20*media:.0f} a {30*media:.0f} s só de rerank, SE não houver 429.")
        if primeiro_429:
            print("   Com 429 no meio, some o tempo de espera. O vídeo tem teto de 7 min e o TAPI")
            print("   pede a demo PELA INTERFACE — uma consulta com MAX_STARTUPS baixo, não o run")
            print("   completo do grafo, é o que cabe.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--throttle", type=int, default=0, metavar="N",
                    help="faz N chamadas sequenciais e reporta onde o 429 aparece (sugestão: 15)")
    ap.add_argument("--janela", action="store_true", help="escalada de tamanho de passagem")
    args = ap.parse_args()

    if not RERANK.cohere_api_key:
        print("ERRO: COHERE_API_KEY ausente no .env.")
        print("Trial gratuita em https://dashboard.cohere.com/api-keys "
              "(1.000 chamadas/mês, Rerank a 10 req/min).")
        return 2

    print("=" * 78)
    print(f"COHERE RERANK — {RERANK.cohere_modelo}  ·  {URL_COHERE}")
    print("=" * 78)

    ok = prova_de_ordenacao()
    if args.janela:
        janela()
    if args.throttle:
        throttle(args.throttle)

    print("\n" + "=" * 78)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
