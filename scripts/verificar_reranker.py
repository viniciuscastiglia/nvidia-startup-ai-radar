"""Bloco 0 da sessão 03 — mede a janela de entrada do reranker. Ver D-034.

POR QUE ESTE SCRIPT EXISTE
--------------------------
`TETO_TOKENS = 450` em `src/rag/chunking.py` foi escolhido supondo que um cross-encoder tem
janela de 512 tokens. Isso era DEDUÇÃO. Se a janela real fosse menor, todo chunk acima dela
teria o final truncado no rerank — e o trecho que responde a pergunta pode ser justamente o
que se perde. O bloco era bloqueante porque a resposta poderia obrigar a re-chunkar e
re-embedar o corpus inteiro.

Não obrigou: a janela é **8.192 tokens**, e o teto do chunk não é imposto por ela.

OS TRÊS TESTES, E POR QUE SÃO TRÊS
-----------------------------------
1. **A API denuncia o limite se o payload OMITIR `truncate`.** Com `truncate="END"` ela corta em
   silêncio e responde 200 — não há erro para observar, exatamente como no embedder. Sem o
   parâmetro, ela recusa com o número na mensagem. Um teste, uma chamada, resposta exata.

2. **A janela é conjunta (query + passagem) ou só da passagem?** Isso não é curiosidade: se for
   conjunta, o orçamento real da passagem é `janela - tokens_da_query`, e o teto do chunker teria
   que descontar a maior consulta plausível. Bissecção do maior tamanho de passagem aceito, com
   query curta e com query longa. Se o ponto de corte anda junto com a query, é conjunta.

3. **Diluição.** É o teste que o bloco não previa e o único cujo resultado ainda vale para
   decidir alguma coisa: a MESMA frase-resposta, afogada em quantidade crescente de enchimento.
   Caber na janela não é o mesmo que pontuar bem nela.

O teste diferencial ao estilo do `verificar_embedder.py` também está aqui, no teste 1: dois
logits EXATAMENTE iguais para `A` e `A + marcador` significam que os dois foram cortados no
mesmo ponto. É o mesmo raciocínio, com escalar no lugar de vetor.

USO
---
    python scripts/verificar_reranker.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
import tiktoken

from src.config import RERANK, tem_credencial

# tiktoken é o tokenizer da OpenAI, NÃO o do NeMo. A própria API mostrou o quanto isso custa:
# num texto que o tiktoken conta como 20.000 tokens, ela contou 19.886 — ~0,6% de diferença.
# Serve para dimensionar; os números saem como ordem de grandeza.
TOKENIZADOR = tiktoken.get_encoding("cl100k_base")

# ENCHIMENTO fala de OUTRO assunto (dataframes em GPU) no mesmo registro do corpus. Não pode
# conter a resposta, senão o marcador deixa de ser a única coisa que separa A de B.
ENCHIMENTO = (
    "The cuDF library provides a pandas-like API for dataframe manipulation on the GPU. "
    "It supports groupby aggregations, joins, sorting and string operations at scale. "
    "The accelerator mode intercepts pandas calls and dispatches them to the device, "
    "falling back to the CPU whenever an operation is not yet implemented. "
    "Columnar memory layout follows the Apache Arrow specification for interoperability. "
)
RESPOSTA = (
    "NVIDIA NIM packages the model together with an optimized inference engine and "
    "exposes a standard OpenAI-compatible API endpoint for deployment."
)

# A query do teste é a q19 do gabarito: tamanho típico das perguntas reais do sistema.
QUERY = "Qual produto empacota o modelo com uma engine de inferencia otimizada e expoe API padrao?"
QUERY_CURTA = "O que e NIM?"
QUERY_LONGA = (
    "Qual produto da NVIDIA empacota o modelo junto de uma engine de inferencia otimizada, "
    "que pode ser TensorRT-LLM, vLLM ou SGLang conforme o modelo, e ainda expoe uma API padrao "
    "compativel com OpenAI para que a implantacao em qualquer infraestrutura acelerada por GPU "
    "leve minutos em vez de semanas de trabalho?"
)


def n_tokens(texto: str) -> int:
    return len(TOKENIZADOR.encode(texto))


def encher(alvo: int) -> str:
    bruto = ENCHIMENTO * (alvo // n_tokens(ENCHIMENTO) + 2)
    return TOKENIZADOR.decode(TOKENIZADOR.encode(bruto)[:alvo])


def _ranquear(query: str, passagens: list[str], truncate: str | None = "END"):
    """Devolve (logits_na_ordem_de_entrada, ms, erro). `truncate=None` faz a API RECUSAR."""
    payload: dict = {
        "model": RERANK.modelo,
        "query": {"text": query},
        "passages": [{"text": p} for p in passagens],
    }
    if truncate:
        payload["truncate"] = truncate

    t0 = time.perf_counter()
    r = httpx.post(
        RERANK.url,
        headers={"Authorization": f"Bearer {RERANK.api_key}", "Accept": "application/json"},
        json=payload,
        timeout=120.0,
    )
    ms = (time.perf_counter() - t0) * 1000
    if r.status_code >= 400:
        return None, ms, f"HTTP {r.status_code}: {r.text[:200]}"
    por_indice = {x["index"]: x["logit"] for x in r.json()["rankings"]}
    return [por_indice[i] for i in range(len(passagens))], ms, None


# ─────────────────────────────────────────────────────────────────────────────
# 1. Onde o reranker corta, e ele avisa?
# ─────────────────────────────────────────────────────────────────────────────
def teste_limite() -> None:
    print("\n1. LIMITE DE ENTRADA")
    print("   1a. SEM o parametro truncate, a API recusa em vez de cortar em silencio?")
    _, ms, err = _ranquear(QUERY, [encher(20000)], truncate=None)
    print(f"       {err or 'respondeu 200 — trunca em silencio mesmo sem o parametro'}  ({ms:.0f} ms)")

    print("\n   1b. Diferencial: logit(enchimento) vs logit(enchimento + resposta).")
    print("       IGUAIS = os dois foram cortados no mesmo ponto = a resposta nao entrou.")
    print(f"       {'N tok':>7} {'logit A':>10} {'logit B':>10} {'delta':>9}   veredito")
    for alvo in (128, 512, 2048, 4096):
        a = encher(alvo)
        logits, ms, err = _ranquear(QUERY, [a, a + " " + RESPOSTA])
        if err:
            print(f"       {alvo:>7} ERRO {err}")
            break
        la, lb = logits
        cortado = abs(lb - la) < 1e-9
        print(f"       {alvo:>7} {la:>10.4f} {lb:>10.4f} {lb - la:>+9.4f}   "
              f"{'CORTADO (identicos)' if cortado else 'integro'}")


# ─────────────────────────────────────────────────────────────────────────────
# 2. A janela é conjunta? (é o que decide se o teto do chunk desconta a query)
# ─────────────────────────────────────────────────────────────────────────────
def teste_janela_conjunta() -> None:
    print("\n2. A JANELA E CONJUNTA (query + passagem) OU SO DA PASSAGEM?")
    print("   Bissecao do maior tamanho de PASSAGEM aceito, com duas queries de tamanhos")
    print("   diferentes. Se o ponto de corte anda junto com a query, e conjunta — e ai o")
    print("   orcamento real do chunk e 'janela menos a maior consulta plausivel'.\n")

    def recusa(query: str, tam: int) -> str | None:
        _, _, err = _ranquear(query, [encher(tam)], truncate=None)
        return err

    # BRACKET EXPONENCIAL ANTES DA BISSECAO. A versao anterior fixava [7000, 8600], faixa
    # herdada do llama-nemotron-rerank-1b-v2 (janela 8.192). Quando esse modelo morreu e o
    # rerank-qa-mistral-4b entrou (janela ~6.958), o guard passou a disparar e o teste
    # IMPRIMIA "faixa invalida" sem dizer por que — um teste que nao testa nada, em silencio.
    # Sondar antes de bissecar tira a ordem de grandeza do chute. Ver D-046.
    def bracket(q: str) -> tuple[int, int] | None:
        anterior = 0
        for tam in (256, 1024, 4096, 16384, 65536):
            if recusa(q, tam):
                return (anterior, tam) if anterior else (0, tam)
            anterior = tam
        return None

    for nome, q in (("curta", QUERY_CURTA), ("longa", QUERY_LONGA)):
        faixa = bracket(q)
        if not faixa:
            print(f"   query {nome}: nenhuma recusa ate 65.536 tokens — janela acima da faixa sondada")
            continue
        lo, hi = faixa
        while hi - lo > 4:
            meio = (lo + hi) // 2
            if recusa(q, meio):
                hi = meio
            else:
                lo = meio
        print(f"   query {nome:6} ({n_tokens(q):>3} tok): maior passagem aceita ~{lo} tok"
              f"  ·  passagem + query = {lo + n_tokens(q)}")
        print(f"       mensagem no limite: {recusa(q, hi)}")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Diluição — o achado que de fato informa o teto do chunker
# ─────────────────────────────────────────────────────────────────────────────
def teste_diluicao() -> None:
    print("\n3. DILUICAO — a MESMA frase-resposta, afogada em enchimento crescente.")
    print("   logit(com resposta) e o que decide o ranking. Se ele cai com o tamanho, chunk")
    print("   longo perde para chunk curto mesmo contendo a mesma resposta.\n")
    print(f"   {'tam passagem':>13} {'so enchimento':>14} {'COM resposta':>13} {'ganho':>9}")

    logits, _, _ = _ranquear(QUERY, [RESPOSTA])
    print(f"   {n_tokens(RESPOSTA):>13} {'—':>14} {logits[0]:>13.4f} {'—':>9}   <- a frase sozinha")

    n_resposta = n_tokens(RESPOSTA)
    for alvo in (64, 128, 200, 300, 450, 600, 800, 1200, 2000):
        a = encher(alvo)
        b = encher(max(0, alvo - n_resposta)) + " " + RESPOSTA
        logits, _, err = _ranquear(QUERY, [a, b])
        if err:
            print(f"   {alvo:>13} ERRO {err}")
            break
        la, lb = logits
        print(f"   {n_tokens(b):>13} {la:>14.4f} {lb:>13.4f} {lb - la:>+9.4f}")
        time.sleep(0.2)


def main() -> int:
    if not tem_credencial():
        print("Sem credencial: defina NVIDIA_API_KEY ou LLM_API_KEY no .env")
        return 1

    print("=" * 78)
    print(f"JANELA DO RERANKER — {RERANK.modelo}")
    print("=" * 78)
    teste_limite()
    teste_janela_conjunta()
    teste_diluicao()

    print("\n" + "=" * 78)
    print(f"Leitura: os numeros ACIMA sao deste modelo ({RERANK.modelo}) e de hoje.")
    print("NAO ha conclusao fixa impressa aqui de proposito. A versao anterior deste script")
    print("afirmava 'a janela e 8.192 CONJUNTOS' como texto codificado — e continuou afirmando")
    print("isso depois de o modelo que a media morrer (D-046). Um script de medicao que imprime")
    print("a conclusao da medicao PASSADA e' pior que nenhum script.")
    print("\nO que se decide com o que saiu acima:")
    print("  · TETO_TOKENS (chunking.py) e' imposto pela janela? Compare com o maior chunk do")
    print("    corpus — 446 tokens em 25/08. Se a janela for muito maior, o teto e' escolha de")
    print("    PRECISAO DE RECUPERACAO e nao restricao do motor.")
    print("  · Alguma logica pode depender de margem pequena? Logits quantizados tem passo de")
    print("    grade, e a repetibilidade e' medida em")
    print("    scripts/auditoria/janela_rerank_qa_mistral_4b.py (3 chamadas, espalhamento 0 em 25/08).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
