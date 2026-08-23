"""Passos 1, 2, 4 e 5 do pipeline RAG do TAPI: ingestão, limpeza, embeddings, armazenamento.

O passo 3 (chunking) mora em `src/rag/chunking.py`, com a decisão em D-025.

NÃO É CRAWLER. Lê o manifesto `data/nvidia/fontes.yaml`, busca exatamente aquelas URLs e mais
nenhuma, não segue link e não descobre página. Cada URL foi escolhida e verificada por um
humano. O TAPI põe crawling fora de escopo; o mesmo raciocínio está no docstring de
`scripts/coletar.py`.

TRÊS DECISÕES QUE ESTE SCRIPT MATERIALIZA
------------------------------------------
1. **Uma chamada de embedding por chunk, não duas.** O modelo devolve 2048 dimensões e as
   1024 saem por truncagem local. Medi em 23/08 (`verificar_embedder.py`) que truncar e
   renormalizar dá cos = 0.99999996 contra pedir `dimensions=1024` à API — ver D-029. Metade
   das chamadas, e as duas colunas do banco saem da mesma resposta.

2. **`input_type="passage"`.** O NeMo Retriever é assimétrico e o erro é SILENCIOSO: embedar
   documento como se fosse consulta degrada a recuperação sem levantar exceção
   (`contexto/03` §3). É o tipo de defeito que só aparece como "o RAG é meio ruim".

3. **Piso de qualidade que falha alto.** Uma fonte abaixo de 3.000 chars ou 3 headings
   interrompe a ingestão com o nome da tecnologia na mensagem. Sem isso, cuDF entraria na
   base com 558 chars de índice de docs e o RAG responderia "não sei" sobre cuDF sem ninguém
   entender por quê. Ver D-028.

AS DUAS ESTRATÉGIAS SÃO INGERIDAS JUNTAS (D-027). São ~380 chunks no total; a comparação de
recall@k da sessão 04 depende das duas estarem na tabela ao mesmo tempo.

USO
---
    python scripts/ingerir_nvidia.py --so-validar   # sem banco e sem API: só a distribuição
    python scripts/ingerir_nvidia.py                # ingere; rodar de novo é upsert
    python scripts/ingerir_nvidia.py --tecnologia cuDF
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

import httpx
import yaml
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DATABASE_URL, EMBEDDING, tem_credencial
from src.db import conectar
from src.rag.chunking import Chunk, MetaDocumento, chunk_estrutural, chunk_fixo
from src.rag.limpeza import RUIDO_HTML

MANIFESTO = Path(__file__).resolve().parent.parent / "data" / "nvidia" / "fontes.yaml"

PISO_CHARS = 3000
PISO_HEADINGS = 3

# Lote conservador: a documentação não diz qual o máximo aceito por requisição. 16 passa com
# folga e o corpus inteiro cabe em ~24 chamadas — não vale otimizar contra um limite que eu
# não medi.
TAMANHO_LOTE = 16
TENTATIVAS = 3

CABECALHOS_WEB = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


class FonteInsuficiente(RuntimeError):
    """Piso de qualidade reprovado. Falha alto de propósito — é tarefa de curadoria."""


# ─────────────────────────────────────────────────────────────────────────────
# Passos 1 e 2 — buscar e validar
# ─────────────────────────────────────────────────────────────────────────────

def buscar(fonte: dict, cliente: httpx.Client) -> str:
    r = cliente.get(fonte["url_fetch"])
    r.raise_for_status()
    return r.text


def medir(bruto: str, formato: str) -> tuple[int, int]:
    """(chars de conteúdo, número de headings) — o que o piso de qualidade avalia."""
    if formato == "markdown":
        return len(bruto), sum(1 for ln in bruto.splitlines() if ln.lstrip().startswith("#"))
    sopa = BeautifulSoup(bruto, "lxml")
    for tag in sopa(RUIDO_HTML):
        tag.decompose()
    principal = sopa.find("main") or sopa.find("article") or sopa.body or sopa
    return len(principal.get_text(" ", strip=True)), len(sopa.find_all(["h1", "h2", "h3"]))


def titulo_de(bruto: str, formato: str, padrao: str) -> str:
    if formato == "markdown":
        for ln in bruto.splitlines():
            if ln.lstrip().startswith("#"):
                return ln.lstrip("# ").strip() or padrao
        return padrao
    sopa = BeautifulSoup(bruto, "lxml")
    return (sopa.title.get_text(strip=True) if sopa.title else "") or padrao


# ─────────────────────────────────────────────────────────────────────────────
# Passo 4 — embeddings
# ─────────────────────────────────────────────────────────────────────────────

def embedar(textos: list[str], cliente: httpx.Client) -> list[list[float]]:
    """Devolve os vetores de 2048 dimensões, em lote, com retry por falha transitória.

    `input_type="passage"` — ver a decisão 2 no docstring do módulo.
    """
    payload = {
        "input": textos,
        "model": EMBEDDING.modelo,
        "input_type": "passage",
        "encoding_format": "float",
        "truncate": "END",
        "dimensions": 2048,
    }
    cabecalhos = {"Authorization": f"Bearer {EMBEDDING.api_key}", "Accept": "application/json"}

    for tentativa in range(1, TENTATIVAS + 1):
        try:
            r = cliente.post(f"{EMBEDDING.base_url}/embeddings", headers=cabecalhos,
                             json=payload, timeout=120.0)
            r.raise_for_status()
            dados = r.json()["data"]
            return [d["embedding"] for d in sorted(dados, key=lambda x: x["index"])]
        except Exception as exc:  # noqa: BLE001
            if tentativa == TENTATIVAS:
                raise
            espera = 2 ** tentativa
            print(f"      tentativa {tentativa} falhou ({type(exc).__name__}); "
                  f"nova em {espera}s", file=sys.stderr)
            time.sleep(espera)
    raise RuntimeError("inalcançável")


def truncar(vetor: list[float], dim: int) -> list[float]:
    """Matryoshka: os primeiros `dim` valores, renormalizados.

    Equivalência com `dimensions=dim` da API medida em 23/08: cos = 0.99999996 (D-029).
    """
    fatia = vetor[:dim]
    norma = sum(x * x for x in fatia) ** 0.5
    return [x / norma for x in fatia] if norma else fatia


def como_vetor(v: list[float]) -> str:
    """Serialização literal do pgvector.

    Sem o pacote `pgvector`: são três linhas e uma dependência a menos, e deixa explícito no
    código o que vai pelo fio em vez de escondê-lo num adaptador.
    """
    return "[" + ",".join(repr(float(x)) for x in v) + "]"


# ─────────────────────────────────────────────────────────────────────────────
# Passo 5 — armazenamento
# ─────────────────────────────────────────────────────────────────────────────

SQL_UPSERT = """
INSERT INTO chunks_nvidia (
    tecnologia, documento_url, titulo_documento, caminho_secao,
    texto, texto_indexado, ordinal, n_tokens, estrategia,
    embedding, embedding_bruto, coletado_em
) VALUES (
    %(tecnologia)s, %(documento_url)s, %(titulo_documento)s, %(caminho_secao)s,
    %(texto)s, %(texto_indexado)s, %(ordinal)s, %(n_tokens)s, %(estrategia)s,
    %(embedding)s::vector, %(embedding_bruto)s::vector, CURRENT_DATE
)
ON CONFLICT (estrategia, documento_url, ordinal) DO UPDATE SET
    tecnologia       = EXCLUDED.tecnologia,
    titulo_documento = EXCLUDED.titulo_documento,
    caminho_secao    = EXCLUDED.caminho_secao,
    texto            = EXCLUDED.texto,
    texto_indexado   = EXCLUDED.texto_indexado,
    n_tokens         = EXCLUDED.n_tokens,
    embedding        = EXCLUDED.embedding,
    embedding_bruto  = EXCLUDED.embedding_bruto,
    coletado_em      = CURRENT_DATE
"""

SQL_LIMPAR_SOBRAS = """
DELETE FROM chunks_nvidia
WHERE estrategia = %(estrategia)s AND documento_url = %(documento_url)s AND ordinal >= %(n)s
"""


def gravar(chunks: list[Chunk], vetores: list[list[float]]) -> None:
    """Upsert idempotente. A chave é (estrategia, documento_url, ordinal), do schema.

    O DELETE das sobras existe porque re-chunkar pode produzir MENOS chunks que a ingestão
    anterior — sem ele, os ordinais antigos ficariam órfãos na tabela, com embedding de um
    texto que não existe mais, poluindo a busca em silêncio.
    """
    with conectar() as conexao, conexao.cursor() as cur:
        for chunk, vetor in zip(chunks, vetores):
            cur.execute(SQL_UPSERT, {
                "tecnologia": chunk.tecnologia,
                "documento_url": chunk.documento_url,
                "titulo_documento": chunk.titulo_documento,
                "caminho_secao": chunk.caminho_secao,
                "texto": chunk.texto,
                "texto_indexado": chunk.texto_indexado,
                "ordinal": chunk.ordinal,
                "n_tokens": chunk.n_tokens,
                "estrategia": chunk.estrategia,
                "embedding": como_vetor(truncar(vetor, EMBEDDING.dimensao)),
                "embedding_bruto": como_vetor(vetor),
            })
        if chunks:
            cur.execute(SQL_LIMPAR_SOBRAS, {
                "estrategia": chunks[0].estrategia,
                "documento_url": chunks[0].documento_url,
                "n": len(chunks),
            })
        conexao.commit()


# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--so-validar", action="store_true",
                    help="busca e chunka, mas não chama a API de embedding nem toca no banco")
    ap.add_argument("--tecnologia", help="ingere só esta (nome exato do manifesto)")
    args = ap.parse_args()

    fontes = yaml.safe_load(MANIFESTO.read_text())
    if args.tecnologia:
        fontes = [f for f in fontes if f["tecnologia"] == args.tecnologia]
        if not fontes:
            print(f"Tecnologia não está no manifesto: {args.tecnologia}", file=sys.stderr)
            return 1

    if not args.so_validar and not tem_credencial():
        print("Sem credencial: defina NVIDIA_API_KEY ou LLM_API_KEY no .env", file=sys.stderr)
        return 1

    print(f"{len(fontes)} fontes · {'VALIDAÇÃO (sem banco, sem API)' if args.so_validar else DATABASE_URL}\n")
    print(f"{'tecnologia':30} {'chars':>7} {'head':>5} {'estrut':>7} {'fixo':>5} {'mediana':>8}")

    todos: list[Chunk] = []
    reprovadas: list[str] = []

    with httpx.Client(follow_redirects=True, timeout=60.0, headers=CABECALHOS_WEB) as web:
        for fonte in fontes:
            bruto = buscar(fonte, web)
            chars, headings = medir(bruto, fonte["formato"])
            if chars < PISO_CHARS or headings < PISO_HEADINGS:
                reprovadas.append(
                    f"{fonte['tecnologia']}: {chars} chars, {headings} headings "
                    f"em {fonte['url_fetch']} (piso: {PISO_CHARS} e {PISO_HEADINGS})"
                )
                print(f"{fonte['tecnologia']:30} {chars:>7} {headings:>5}   <-- REPROVADA NO PISO")
                continue

            meta = MetaDocumento(
                tecnologia=fonte["tecnologia"],
                documento_url=fonte["url_citacao"],
                titulo_documento=titulo_de(bruto, fonte["formato"], fonte["tecnologia"]),
                formato=fonte["formato"],
            )
            estrutural = chunk_estrutural(bruto, meta)
            fixo = chunk_fixo(bruto, meta)
            todos += estrutural + fixo
            mediana = int(statistics.median([c.n_tokens for c in estrutural])) if estrutural else 0
            print(f"{fonte['tecnologia']:30} {chars:>7} {headings:>5} {len(estrutural):>7} "
                  f"{len(fixo):>5} {mediana:>8}")

            if not args.so_validar:
                for estrategia in ("estrutural-v1", "fixo-800"):
                    grupo = [c for c in (estrutural + fixo) if c.estrategia == estrategia]
                    vetores: list[list[float]] = []
                    for i in range(0, len(grupo), TAMANHO_LOTE):
                        lote = grupo[i:i + TAMANHO_LOTE]
                        vetores += embedar([c.texto_indexado for c in lote], web)
                    gravar(grupo, vetores)

    if reprovadas:
        print("\nFONTES REPROVADAS NO PISO DE QUALIDADE — a ingestão não continua:")
        for r in reprovadas:
            print(f"  - {r}")
        print("\nIsto é tarefa de curadoria: achar uma página oficial com conteúdo estático,")
        print("verificar com `python scripts/coletar.py <url>` e corrigir o manifesto.")
        return 1

    toks = [c.n_tokens for c in todos if c.estrategia == "estrutural-v1"]
    print(f"\n{len(todos)} chunks no total "
          f"({len(toks)} estruturais, {len(todos) - len(toks)} no braço de controle)")
    if toks:
        print(f"tokens do estrutural: min {min(toks)} · mediana {int(statistics.median(toks))} "
              f"· max {max(toks)}")
    if args.so_validar:
        print("\nNada foi gravado (--so-validar).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
