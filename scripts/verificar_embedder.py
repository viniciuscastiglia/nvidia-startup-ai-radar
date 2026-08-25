"""Bloco 0 da sessão 02 — transforma em medição duas suposições do plano do RAG.

POR QUE ESTE SCRIPT EXISTE
--------------------------
O plano da sessão 02 tem duas afirmações que eram DEDUÇÃO, e as duas custam caro se
estiverem erradas depois que o corpus já foi embedado:

1. **Truncar localmente um vetor de 2048 e renormalizar é equivalente a pedir
   `dimensions=1024` à API.** Se for verdade, guardar `embedding_bruto vector(2048)` no
   banco faz o sweep de dimensão da sessão 04 (384 vs 768 vs 1024) custar ZERO chamada de
   API — é só fatiar a coluna. Se for mentira, D-014 continua valendo como está escrita:
   trocar de dimensão exige re-embedar o corpus inteiro.

   É isso que a propriedade Matryoshka promete: o modelo é treinado para que os primeiros
   k valores do vetor já sejam, sozinhos, uma representação boa. Promessa lida na
   documentação não é promessa verificada — daí este teste.

2. **Qual o limite de entrada do embedder configurado.** Nenhuma documentação que
   consultei diz. Esse número é o TETO da banda de tamanho do chunker: chunk maior que o
   limite é chunk cujo final não entra no vetor.

POR QUE O TESTE DE LIMITE É DIFERENCIAL, E NÃO "MANDAR ATÉ FALHAR"
-------------------------------------------------------------------
`_embed()` manda `"truncate": "END"` no payload. Com isso a API NÃO devolve erro quando o
texto passa do limite — ela corta o excesso e responde 200 normalmente. Mandar textos cada
vez maiores até dar erro nunca acharia nada.

O teste que funciona é diferencial: embeda `texto[:n]` e `texto[:n] + marcador`. Enquanto
n couber no limite, o marcador muda o vetor. Quando n já estourou, os dois são cortados no
mesmo ponto e os vetores ficam IDÊNTICOS. O menor n em que o marcador para de fazer
diferença é o limite — e o sintoma "cosseno exatamente 1.0" é a assinatura da truncagem
silenciosa.

USO
---
    python scripts/verificar_embedder.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tiktoken

from scripts.smoke_nvidia import _embed, cosseno
from src.config import EMBEDDING, tem_credencial

# tiktoken é o tokenizer da OpenAI, NÃO o do NeMo. Serve como aproximação para reportar o
# limite em ordem de grandeza; o número que vai para o chunker carrega margem por isso.
TOKENIZADOR = tiktoken.get_encoding("cl100k_base")

# Texto-base em inglês, no mesmo registro do corpus real (documentação técnica NVIDIA),
# para que a contagem de tokens se pareça com a do uso de verdade.
SEMENTE = (
    "NVIDIA NIM microservices package a model together with an optimized inference engine "
    "and a standard API, so that deployment on any NVIDIA-accelerated infrastructure takes "
    "minutes instead of weeks. The engine may be TensorRT-LLM, vLLM or SGLang depending on "
    "the model. Quantization options include FP8, FP4, INT8 and INT4 with AWQ. Algorithmic "
    "optimizations cover speculative decoding, paged KV cache, chunked context and multiblock "
    "attention. Parallelism spans tensor, pipeline, context, data and wide expert parallelism. "
)

MARCADOR = " The secret passphrase for this document is xylophone-marmalade-quasar. "


def norma(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def normalizar(v: list[float]) -> list[float]:
    n = norma(v)
    return [x / n for x in v] if n else v


def n_tokens(texto: str) -> int:
    return len(TOKENIZADOR.encode(texto))


# ─────────────────────────────────────────────────────────────────────────────
# 1. A truncagem Matryoshka é equivalente a pedir a dimensão à API?
# ─────────────────────────────────────────────────────────────────────────────
def teste_matryoshka() -> bool:
    print("\n1. MATRYOSHKA — truncar localmente 2048 == pedir dimensions=N à API?")
    texto = SEMENTE.strip()

    completo, _ = _embed([texto], "passage", 2048)
    v2048 = completo[0]
    print(f"   vetor bruto: {len(v2048)} dims · norma L2 = {norma(v2048):.6f}")

    ok_geral = True
    for dim in (1024, 768, 384):
        api, _ = _embed([texto], "passage", dim)
        v_api = api[0]

        local_cru = v2048[:dim]                 # a truncagem que a Matryoshka promete
        local_norm = normalizar(local_cru)

        c_cru = cosseno(v_api, local_cru)        # cosseno já normaliza — deve bater com o de baixo
        c_norm = cosseno(v_api, local_norm)
        delta_norma = abs(norma(v_api) - norma(local_norm))

        veredito = "EQUIVALENTE" if c_norm > 0.9999 else ("PRÓXIMO" if c_norm > 0.99 else "DIFERENTE")
        if c_norm <= 0.9999:
            ok_geral = False
        print(f"   dim {dim:>4}: cos(api, trunc_local) = {c_norm:.8f} "
              f"(sem renormalizar: {c_cru:.8f}) · |Δnorma| = {delta_norma:.2e}  → {veredito}")

    print("   Leitura: EQUIVALENTE nas três significa que a coluna embedding_bruto(2048)")
    print("            deixa o sweep de dimensão da sessão 04 sair sem gastar crédito.")
    return ok_geral


# ─────────────────────────────────────────────────────────────────────────────
# 2. Onde o embedder corta o texto em silêncio?
# ─────────────────────────────────────────────────────────────────────────────
def teste_limite_entrada() -> int | None:
    print("\n2. LIMITE DE ENTRADA — a partir de quantos tokens o texto é cortado?")
    print("   (payload manda truncate=END, então não há erro para observar: o sinal é")
    print("    o marcador do fim do texto parar de mudar o vetor)")

    limite_detectado: int | None = None
    for alvo in (256, 512, 1024, 2048, 4096, 8192, 16384):
        # Repete a semente até passar do alvo, depois corta no token exato.
        bruto = SEMENTE * (alvo // n_tokens(SEMENTE) + 2)
        ids = TOKENIZADOR.encode(bruto)[:alvo]
        texto = TOKENIZADOR.decode(ids)

        try:
            vetores, ms = _embed([texto, texto + MARCADOR], "passage", EMBEDDING.dimensao)
        except Exception as exc:  # noqa: BLE001
            print(f"   {alvo:>6} tokens: ERRO {type(exc).__name__}: {str(exc)[:90]}")
            limite_detectado = limite_detectado or alvo
            break

        c = cosseno(vetores[0], vetores[1])
        cortado = c > 0.999999
        marca = "CORTADO" if cortado else "íntegro"
        print(f"   {alvo:>6} tokens: cos(texto, texto+marcador) = {c:.8f}  → {marca}  ({ms:.0f} ms)")
        if cortado and limite_detectado is None:
            limite_detectado = alvo
            break

    if limite_detectado:
        print(f"   Limite fica entre o último 'íntegro' e {limite_detectado} tokens (aprox. tiktoken).")
    else:
        print("   Nenhum corte observado na faixa testada.")
    return limite_detectado


def main() -> int:
    if not tem_credencial():
        print("Sem credencial: defina NVIDIA_API_KEY ou LLM_API_KEY no .env")
        return 1

    print(f"Embedder sob teste: {EMBEDDING.modelo}")
    ok = teste_matryoshka()
    teste_limite_entrada()

    print("\n" + "=" * 78)
    print("D-029 se sustenta." if ok else
          "D-029 NÃO se sustenta: a truncagem local diverge da API. Guardar a coluna bruta\n"
          "continua barato, mas o sweep da sessão 04 volta a exigir re-embed — e D-014\n"
          "permanece como está escrita.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
