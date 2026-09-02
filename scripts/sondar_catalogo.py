"""Sondagem do catálogo do build.nvidia.com — o que está VIVO, não o que está listado.

POR QUE ISTO É UM SCRIPT SEPARADO DO `smoke_nvidia.py` (D-070)
----------------------------------------------------------------
Os dois fazem perguntas diferentes e misturá-los estraga as duas respostas:

    smoke_nvidia.py   ->  "a configuração VIGENTE funciona?"      responde 3/3 ou 1/3
    sondar_catalogo.py -> "o que existe de vivo para substituí-la?" responde uma tabela

O docstring do smoke já diz, sobre o endpoint de rerank, que *"deixar o script tentando N
endpoints mascararia uma regressão futura ('passou, mas por outro caminho')"*. O argumento é
idêntico para modelos: um smoke que varre candidatos nunca falha e por isso não avisa nada.

O ACHADO QUE ESTE SCRIPT EXISTE PARA NÃO SE PERDER (D-070, medido em 27/08)
----------------------------------------------------------------------------
**Estar em `GET /v1/models` NÃO significa responder.** Sondados um a um, 10 candidatos
listados no catálogo deram **7 x HTTP 404 e 3 x 200**. Entre os 404 está o
`nvidia/mistral-nemo-minitron-8b-8k-instruct`, que **D-064 recomendou por nome** como
substituto do LLM morto, com base em ele aparecer na listagem.

Consequência de método: a única fonte de verdade sobre disponibilidade é uma chamada real — e é
isso que este script automatiza, para que o próximo EOL custe 30 segundos em vez de uma
sondagem manual.

A CORREÇÃO DE 01/09: "LISTADO MAS MORTO" ERA TRÊS COISAS SOMADAS (D-079)
--------------------------------------------------------------------------
D-070 concluiu que o catálogo "lista modelos mortos". Ler o CORPO das respostas, e não só o
status, mostrou que a conclusão era grosseira demais: dos 9 que não serviam em 01/09, **1 era
morte real e 8 eram falta de acesso da conta**. Contar as duas juntas inflava o risco de EOL
do projeto por um fator de 8.

A formulação correta, e ela é mais forte: **`GET /v1/models` devolve o catálogo GLOBAL, não o
que a conta pode chamar.** Morte tem assinatura própria — HTTP 410 com a data no corpo — e é
por isso que `_classificar()` existe.

O QUE NÃO EXISTE, E É O QUE MAIS IMPORTA SABER
------------------------------------------------
**Não há aviso prévio por nenhum canal da API.** Medido em 01/09: a listagem expõe só
`id/object/created/owned_by`, sem campo de depreciação; e a resposta de um modelo VIVO não
traz `Sunset` nem `Deprecation` (RFC 8594). Só a chamada real informa, e informa **depois**.

Portanto a mitigação não é prever — é **detectar rápido e trocar barato**: `smoke_nvidia.py`
custa 4 segundos, e o provedor está atrás de env var (D-002). Rodar o smoke antes de gravar
o vídeo e antes de entregar não é zelo, é a única defesa que existe.

E RESPONDER TAMBÉM NÃO BASTA: O PROJETO PRECISA DE SAÍDA ESTRUTURADA
----------------------------------------------------------------------
`src/llm.py` exige `with_structured_output(..., method=...)` em todo acesso a LLM (D-040).
Um modelo que faz chat e quebra no structured output é inútil aqui — e existe: o
`mistralai/mistral-nemotron` responde chat em 200 e devolve **HTTP 500** nos dois métodos.
Por isso `--structured` é parte da sondagem e não um extra.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import LLM, RERANK, tem_credencial  # noqa: E402

TIMEOUT = 90.0

# Curada à mão em 27/08 a partir do catálogo vivo, por proximidade com o
# `meta/llama-3.1-8b-instruct` que morreu: modelos instruct de porte comparável ou menor.
# `--todos` ignora esta lista e sonda o catálogo inteiro — caro, uma chamada por modelo.
CANDIDATOS_LLM = [
    "nvidia/nemotron-3-nano-30b-a3b",
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "mistralai/mistral-nemotron",
    "nvidia/mistral-nemo-minitron-8b-8k-instruct",
    "nv-mistralai/mistral-nemo-12b-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "mistralai/mistral-7b-instruct-v0.3",
    "ibm/granite-3.0-8b-instruct",
    "google/gemma-3-12b-it",
    "microsoft/phi-3.5-moe-instruct",
]

# Paths x modelos de reranking. A combinação toda deu 404/410 em 27/08 (18 sondagens, D-064);
# a lista fica para que "não existe reranker no catálogo" continue sendo uma AFIRMAÇÃO MEDIDA
# e não uma lembrança.
PATHS_RERANK = [
    "https://ai.api.nvidia.com/v1/retrieval/nvidia/reranking",
    "https://ai.api.nvidia.com/v1/retrieval/nvidia/llama-3_2-nemoretriever-500m-rerank-v2/reranking",
    "https://integrate.api.nvidia.com/v1/ranking",
]
MODELOS_RERANK = [
    "nvidia/rerank-qa-mistral-4b",
    "nvidia/llama-3_2-nemoretriever-500m-rerank-v2",
    "nvidia/nv-rerankqa-mistral-4b-v3",
]


def _cab() -> dict[str, str]:
    return {"Authorization": f"Bearer {LLM.api_key}", "Accept": "application/json"}


def catalogo() -> list[str]:
    r = httpx.get(f"{LLM.base_url}/models", headers=_cab(), timeout=TIMEOUT)
    r.raise_for_status()
    return sorted(m["id"] for m in r.json()["data"])


# OS TRÊS MOTIVOS DE UM MODELO NÃO SERVIR — medidos em 01/09, e são DIFERENTES (D-079)
# ---------------------------------------------------------------------------------------
# Até 01/09 este script tinha dois estados, `VIVO` e `morto`, e chamava de "morto" tudo que
# desse >= 400. A medição do EOL de 01/09 mostrou que isso junta três coisas distintas:
#
#   EOL         HTTP 410 + corpo com a DATA:  "has reached its end of life on <ISO>"
#               É morte de verdade, anunciada pelo fornecedor. Não volta.
#   SEM ACESSO  HTTP 404 + corpo "Function '<uuid>': Not found for account '<id>'"
#               O modelo EXISTE e está implantado; esta CONTA não alcança. Não é morte —
#               é entitlement, e pode mudar com o plano sem o modelo mudar.
#   INEXISTENTE HTTP 404 em texto puro ("404 page not found"). O nome não existe.
#
# Por que a distinção importa: contar entitlement como morte inflava o risco de EOL do
# projeto por um fator de 8 na sondagem de 01/09 — 1 morte real contra 8 "sem acesso".
# Decisão de arquitetura tomada sobre esse número seria tomada sobre ruído.
EOL_MARCA = "end of life"
SEM_ACESSO_MARCA = "not found for account"


def _classificar(status: int, corpo: str) -> tuple[str, str]:
    """(rótulo, detalhe) a partir do status e do CORPO — o corpo é quem distingue."""
    baixo = corpo.lower()
    if status == 410 or EOL_MARCA in baixo:
        # A data vem no corpo: "...end of life on 2026-09-01T09:00:00Z and is no longer..."
        data = ""
        if EOL_MARCA in baixo:
            resto = corpo[baixo.index(EOL_MARCA) + len(EOL_MARCA):].strip()
            data = resto.split()[1][:10] if resto.startswith("on ") else resto.split()[0][:10]
        return "EOL", f"EOL {data}".strip()
    if SEM_ACESSO_MARCA in baixo:
        return "SEM ACESSO", "conta sem direito"
    if status == 404:
        return "INEXISTENTE", "nome não existe"
    return "FALHA", f"HTTP {status}"


def sondar_chat(modelo: str) -> tuple[bool, str, str, float | None]:
    """Uma chamada real de 8 tokens. É o ÚNICO teste que distingue listado de servível.

    Devolve `(ok, rótulo, detalhe, ms)`. O rótulo é um dos quatro do bloco acima, ou `VIVO`.
    """
    try:
        t0 = time.perf_counter()
        r = httpx.post(
            f"{LLM.base_url}/chat/completions",
            headers=_cab(),
            json={
                "model": modelo,
                "messages": [{"role": "user", "content": "Responda apenas: OK"}],
                "max_tokens": 8,
                "temperature": 0,
            },
            timeout=TIMEOUT,
        )
        ms = (time.perf_counter() - t0) * 1000
        if r.status_code >= 400:
            rotulo, detalhe = _classificar(r.status_code, r.text)
            return False, rotulo, detalhe, None
        return True, "VIVO", r.json()["choices"][0]["message"]["content"].strip()[:24], ms
    except Exception as exc:  # noqa: BLE001
        return False, "FALHA", f"{type(exc).__name__}", None


def sondar_structured(modelo: str) -> dict[str, str]:
    """Testa os dois métodos de saída estruturada NA PERGUNTA-ARMADILHA de D-047.

    Não é só "o método funciona": a q23 do gabarito (*"o TensorRT-LLM é mais rápido que o vLLM?
    Em quantos por cento?"*) não tem resposta na base, então a saída correta é `abstencao=True`.
    Um modelo que responde 200 e inventa um número passa no teste de encanamento e reprova no
    que importa. A coluna mostra o método E se ele se absteve.
    """
    from langchain_openai import ChatOpenAI
    from pydantic import BaseModel, Field

    class Resposta(BaseModel):
        """Responda usando APENAS a passagem fornecida."""

        abstencao: bool = Field(description="true se a passagem não responde à pergunta")
        resposta: str = Field(description="a resposta, ou o motivo da abstenção")

    prompt = (
        "Passagem: O NVIDIA NIM oferece microsserviços de inferência com API "
        "compatível com OpenAI.\n"
        "Pergunta: O TensorRT-LLM é mais rápido que o vLLM? Em quantos por cento?"
    )

    saida: dict[str, str] = {}
    for metodo in ("json_schema", "function_calling"):
        try:
            cliente = ChatOpenAI(
                base_url=LLM.base_url, api_key=LLM.api_key, model=modelo,
                temperature=0, timeout=TIMEOUT, max_retries=0,
            ).with_structured_output(Resposta, method=metodo)
            r = cliente.invoke(prompt)
            saida[metodo] = "absteve" if r.abstencao else "ALUCINOU"
        except Exception as exc:  # noqa: BLE001
            saida[metodo] = f"erro {getattr(exc, 'status_code', type(exc).__name__)}"
    return saida


def sondar_rerank() -> list[tuple[str, str, str]]:
    corpo = {
        "query": {"text": "Como reduzir a latência de inferência?"},
        "passages": [{"text": "TensorRT-LLM aplica quantização FP8."}],
        "truncate": "END",
    }
    linhas = []
    for url in PATHS_RERANK:
        for modelo in MODELOS_RERANK:
            try:
                r = httpx.post(url, headers=_cab(), json={"model": modelo, **corpo}, timeout=TIMEOUT)
                estado = "VIVO" if r.status_code < 400 else f"HTTP {r.status_code}"
            except Exception as exc:  # noqa: BLE001
                estado = type(exc).__name__
            linhas.append((url.replace("https://", ""), modelo, estado))
    return linhas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--todos", action="store_true",
                    help="sonda TODO modelo do catálogo (uma chamada cada — caro)")
    ap.add_argument("--structured", action="store_true",
                    help="nos modelos vivos, testa json_schema e function_calling na q23")
    ap.add_argument("--rerank", action="store_true",
                    help="sonda os paths x modelos de reranking")
    args = ap.parse_args()

    if not tem_credencial():
        print("ERRO: nenhuma credencial. Preencha NVIDIA_API_KEY no .env.")
        return 2

    print("=" * 78)
    print("SONDAGEM DO CATÁLOGO — build.nvidia.com")
    print("=" * 78)

    listados = catalogo()
    print(f"\nGET /v1/models -> {len(listados)} modelos listados")
    com_rank = [m for m in listados if "rank" in m.lower()]
    print(f"  com 'rank' no nome: {com_rank or 'NENHUM — não há reranker no catálogo'}")

    if args.rerank:
        print("\nRERANKING — path x modelo")
        for url, modelo, estado in sondar_rerank():
            marca = "  " if estado == "VIVO" else "x "
            print(f"  {marca}{estado:10s} {modelo:48s} {url}")

    alvos = listados if args.todos else CANDIDATOS_LLM
    print(f"\nCHAT — {len(alvos)} candidato(s) sondado(s) com chamada REAL")
    print("  (estar listado não é estar vivo — ver o docstring deste arquivo)")
    vivos: list[str] = []
    por_rotulo: dict[str, list[str]] = {}
    for modelo in alvos:
        ok, rotulo, detalhe, ms = sondar_chat(modelo)
        listado = "listado" if modelo in listados else "NEM LISTADO"
        lat = f"{ms:.0f} ms" if ms else "—"
        print(f"  {rotulo:11s} {modelo:48s} {detalhe:20s} {lat:>8s}  {listado}")
        por_rotulo.setdefault(rotulo, []).append(modelo)
        if ok:
            vivos.append(modelo)

    print(f"\n  {len(vivos)} vivo(s) de {len(alvos)} sondado(s)")

    # OS TRÊS MOTIVOS, SEPARADOS. Somá-los é o erro que D-079 corrige: só o bucket EOL é
    # risco de fornecedor. `SEM ACESSO` é entitlement da conta e não diz nada sobre o modelo.
    for rotulo, texto in (
        ("EOL", "APOSENTADO pelo fornecedor — não volta, e a data está no corpo da resposta"),
        ("SEM ACESSO", "existe e roda; ESTA CONTA não alcança. NÃO é morte — é entitlement"),
        ("INEXISTENTE", "o nome não existe no serviço"),
        ("FALHA", "erro de transporte ou status inesperado — reexecutar antes de concluir"),
    ):
        if por_rotulo.get(rotulo):
            print(f"\n  {rotulo} ({len(por_rotulo[rotulo])}) — {texto}:")
            for m in por_rotulo[rotulo]:
                print(f"      {m}")

    fantasmas = [m for m in alvos if m in listados and m not in vivos]
    if fantasmas:
        print(f"\n  {len(fantasmas)} LISTADO(S) MAS NÃO SERVÍVEL(EIS) — `GET /v1/models` é o")
        print("  catálogo GLOBAL, não o que esta conta pode chamar (D-070, corrigido por D-079).")

    print("\n  AVISO PRÉVIO: não existe. A listagem expõe só id/object/created/owned_by, e a")
    print("  resposta viva não traz Sunset nem Deprecation (RFC 8594). Medido em 01/09 —")
    print("  só a chamada real informa, e ela informa DEPOIS. Rodar antes de gravar e de entregar.")

    if args.structured and vivos:
        print("\nSAÍDA ESTRUTURADA — na q23, a pergunta-armadilha de D-047")
        print("  'absteve' é o comportamento CORRETO: a resposta não existe na passagem")
        print(f"  {'modelo':48s} {'json_schema':16s} {'function_calling':16s}")
        for modelo in vivos:
            r = sondar_structured(modelo)
            print(f"  {modelo:48s} {r['json_schema']:16s} {r['function_calling']:16s}")

    print("\n" + "=" * 78)
    return 0 if vivos else 1


if __name__ == "__main__":
    raise SystemExit(main())
