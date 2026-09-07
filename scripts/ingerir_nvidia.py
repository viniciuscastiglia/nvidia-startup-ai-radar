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

AS FONTES SÃO LIDAS DO CACHE VERSIONADO, NÃO DA REDE (06/09) — ver o bloco de decisão em
`CACHE`, abaixo. Sem `--refetch`, este script não toca a internet.

USO
---
    python scripts/ingerir_nvidia.py --so-validar   # OFFLINE: chunking sem banco e sem API
    python scripts/ingerir_nvidia.py                # ingere do cache; rodar de novo é upsert
    python scripts/ingerir_nvidia.py --tecnologia cuDF
    python scripts/ingerir_nvidia.py --so-validar --refetch   # a rede é tocada: mede a DERIVA
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
import time
import unicodedata
from datetime import date
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

# ─────────────────────────────────────────────────────────────────────────────
# CACHE DAS FONTES — o corpus de quem clona passa a ser o corpus medido
#
# O DEFEITO, MEDIDO EM 03/09 (D-089) E NÃO SUPOSTO. Até 06/09 este script baixava ao vivo das
# 16 URLs a cada execução. O clone limpo daquele dia produziu a **mesma contagem (175 chunks)
# com hash diferente**: a página do TensorRT-LLM rolou o mural de novidades e entrou lixo novo
# (`✨ ➡️ link`). O gabarito de 24 perguntas aponta URL **e frase-âncora**, então quem avalia
# roda `avaliar_rag.py` contra um corpus que não é o medido — e o número que ele vê não é o
# número que este repositório afirma. O gabarito sobreviveu daquela vez porque a deriva bateu
# em ruído; a próxima pode bater em âncora. *"Projeto que não executa"* é eliminatório.
#
# O QUE SE CACHEIA É O BRUTO, E ISSO É A DECISÃO
# -----------------------------------------------
# `r.text` é a ENTRADA dos passos 2 e 3 do pipeline. Cachear o texto limpo — ou, pior, os
# chunks — economizaria espaço e tiraria `src/rag/limpeza.py` e `src/rag/chunking.py` do
# caminho de quem clona: `--so-validar`, que existe justamente para exercitar o chunking sem
# banco e sem API, deixaria de exercitar coisa nenhuma. E no dia em que a limpeza mudasse o
# cache mentiria em silêncio, porque o texto gravado descreveria uma limpeza que não é mais a
# do código. Guardando o bruto, o pipeline inteiro continua rodando em cima do cache.
#
# ALTERNATIVA DESCARTADA: pinar só o hash e FALHAR quando a página mudar, sem guardar conteúdo.
# Torna a deriva visível — que é metade do problema — e deixa o corpus de quem avalia refém da
# rede. O modo de falha piora: sai de "corpus diferente do medido" para "não roda".
#
# O CACHE ENTRA NO GIT, e é o ponto inteiro: sem ele versionado, o clone limpo não tem corpus.
# `--refetch` é como a deriva volta a ser visível — re-baixa, compara hash a hash e **imprime o
# que mudou**, em vez de sobrescrever calado.
#
# O ÍNDICE SE CHAMA `indice.json` E NÃO `manifesto.json` de propósito: `fontes.yaml` já é O
# manifesto deste script, e dois arquivos com o mesmo nome de papel é a divergência esperando
# a data.
# ─────────────────────────────────────────────────────────────────────────────
CACHE = MANIFESTO.parent / "cache"
INDICE_CACHE = CACHE / "indice.json"

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

def _slug(texto: str) -> str:
    """Nome de arquivo a partir do nome da tecnologia. Precisa ser ESTÁVEL: é chave de cache,
    e um slug que muda transforma re-execução em re-download silencioso."""
    limpo = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", limpo.lower()).strip("-")


def caminho_de_cache(fonte: dict) -> Path:
    """A extensão acompanha o `formato` do manifesto — o arquivo tem de ser legível por quem
    abrir a pasta para conferir o que foi congelado."""
    return CACHE / f"{_slug(fonte['tecnologia'])}.{'md' if fonte['formato'] == 'markdown' else 'html'}"


def sha256(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def normalizar_quebras(texto: str) -> str:
    """CRLF -> LF na borda da rede. **Não é cosmético — é a corretude do cache.**

    `Path.write_text` grava o que recebe; `Path.read_text` abre em modo texto e traduz `\r\n`
    e `\r` para `\n`. Sem normalizar, o texto que `--refetch` entrega ao chunker NÃO É o texto
    que uma leitura do cache entrega, e o cache deixa de ser reprodução do que foi medido — que
    é a única coisa que ele existe para ser.

    Medido em 06/09, e por isso a função existe: **7 das 16 fontes vêm com CRLF** (1.468
    ocorrências na do Healthcare). As contagens de chunk saíram iguais nos dois caminhos, mas
    isso é sorte do chunker, não desenho — e um `sha256` que não descreve o arquivo em disco é
    um instrumento de deriva que mede a si mesmo.

    Efeito de borda que é benefício: o hash passa a ser insensível à escolha de fim de linha do
    servidor. Um CRLF que vira LF do outro lado não é deriva de conteúdo, e não deve aparecer
    como se fosse.
    """
    return texto.replace("\r\n", "\n").replace("\r", "\n")


def ler_indice() -> dict:
    return json.loads(INDICE_CACHE.read_text(encoding="utf-8")) if INDICE_CACHE.exists() else {}


def buscar(fonte: dict, cliente: httpx.Client, *, refetch: bool = False) -> tuple[str, str]:
    """O bruto da fonte e DE ONDE ele veio — `cache` ou `rede`. Ver o bloco de decisão acima.

    A rede só é tocada quando o cache não tem a fonte ou quando `--refetch` pede. É isso que
    faz `--so-validar` rodar OFFLINE num clone limpo, que é o requisito inteiro.
    """
    arquivo = caminho_de_cache(fonte)
    if arquivo.exists() and not refetch:
        return arquivo.read_text(encoding="utf-8"), "cache"
    r = cliente.get(fonte["url_fetch"])
    r.raise_for_status()
    bruto = normalizar_quebras(r.text)
    CACHE.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(bruto, encoding="utf-8")
    return bruto, "rede"


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
    # A ÚNICA PORTA PARA A REDE. Sem ela o script é offline por construção, que é o requisito
    # do clone limpo. Combinada com `--so-validar` ela vira o instrumento de DERIVA: baixa,
    # compara e imprime, sem gastar embedding nem tocar no banco.
    ap.add_argument("--refetch", action="store_true",
                    help="re-baixa as fontes, reescreve o cache e IMPRIME o que mudou")
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

    print(f"{len(fontes)} fontes · {'VALIDAÇÃO (sem banco, sem API)' if args.so_validar else DATABASE_URL}"
          f" · {'REFETCH (toca a rede)' if args.refetch else 'do cache'}\n")
    print(f"{'tecnologia':30} {'fonte':>6} {'chars':>7} {'head':>5} {'estrut':>7} {'fixo':>5} {'mediana':>8}")

    todos: list[Chunk] = []
    reprovadas: list[str] = []
    indice = ler_indice()
    novo_indice: dict[str, dict] = {}
    derivaram: list[tuple[str, str, str]] = []
    # SEM LINHA DE BASE NÃO EXISTE "NADA MUDOU". A primeira coleta de uma fonte não tem hash
    # anterior para comparar, e imprimir "os hashes batem" ali seria afirmar uma verificação
    # que não aconteceu — o mesmo defeito que `varrer_classes.py` cometeu ao imprimir
    # "D-101 verificado" sem verificar nada (D-103).
    inauguradas: list[str] = []
    baixou = False

    with httpx.Client(follow_redirects=True, timeout=60.0, headers=CABECALHOS_WEB) as web:
        for fonte in fontes:
            bruto, origem = buscar(fonte, web, refetch=args.refetch)
            baixou = baixou or origem == "rede"
            # A CONTABILIDADE ACONTECE ANTES DO PISO DE QUALIDADE, e de propósito: uma fonte
            # que passou a reprovar no piso é exatamente o caso em que se quer saber que o
            # conteúdo mudou. Registrar só o que passa esconderia a causa.
            atual = sha256(bruto)
            anterior = (indice.get(fonte["tecnologia"]) or {}).get("sha256")
            if origem == "rede":
                if anterior is None:
                    inauguradas.append(fonte["tecnologia"])
                elif anterior != atual:
                    derivaram.append((fonte["tecnologia"], anterior, atual))
            novo_indice[fonte["tecnologia"]] = {
                "url_fetch": fonte["url_fetch"],
                "arquivo": caminho_de_cache(fonte).name,
                "formato": fonte["formato"],
                "bytes": len(bruto.encode("utf-8")),
                "sha256": atual,
                "baixado_em": (str(date.today()) if origem == "rede"
                               else (indice.get(fonte["tecnologia"]) or {}).get("baixado_em", "")),
            }
            chars, headings = medir(bruto, fonte["formato"])
            if chars < PISO_CHARS or headings < PISO_HEADINGS:
                reprovadas.append(
                    f"{fonte['tecnologia']}: {chars} chars, {headings} headings "
                    f"em {fonte['url_fetch']} (piso: {PISO_CHARS} e {PISO_HEADINGS})"
                )
                print(f"{fonte['tecnologia']:30} {origem:>6} {chars:>7} {headings:>5}"
                      f"   <-- REPROVADA NO PISO")
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
            print(f"{fonte['tecnologia']:30} {origem:>6} {chars:>7} {headings:>5} "
                  f"{len(estrutural):>7} {len(fixo):>5} {mediana:>8}")

            if not args.so_validar:
                for estrategia in ("estrutural-v1", "fixo-800"):
                    grupo = [c for c in (estrutural + fixo) if c.estrategia == estrategia]
                    vetores: list[list[float]] = []
                    for i in range(0, len(grupo), TAMANHO_LOTE):
                        lote = grupo[i:i + TAMANHO_LOTE]
                        vetores += embedar([c.texto_indexado for c in lote], web)
                    gravar(grupo, vetores)

    # O ÍNDICE É ESCRITO ANTES DA CHECAGEM DO PISO, e de propósito: os arquivos já estão em
    # disco, e um índice que só registra o que passou no piso descreve um cache que não existe.
    # Só grava quando alguma fonte veio da REDE — rodar do cache não pode reescrever `baixado_em`
    # e transformar leitura em falso registro de coleta.
    if baixou:
        CACHE.mkdir(parents=True, exist_ok=True)
        INDICE_CACHE.write_text(
            json.dumps(dict(sorted(novo_indice.items())), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        print(f"\ncache: {len(novo_indice)} fonte(s) em {CACHE.relative_to(CACHE.parents[2])}/")

    # A DERIVA DE D-089 DEIXA DE SER HIPÓTESE E VIRA SAÍDA DE INSTRUMENTO. Em 03/09 ela foi
    # descoberta comparando duas execuções à mão; a partir daqui o script a imprime.
    if derivaram:
        print(f"\nA PÁGINA MUDOU EM {len(derivaram)} FONTE(S) desde o último cache:")
        for tecnologia, antes, agora in derivaram:
            print(f"  {tecnologia:30} {antes[:12]} -> {agora[:12]}")
        print("  O cache foi reescrito. Se o gabarito apontar frase-âncora numa destas,")
        print("  rode `python scripts/avaliar_rag.py --validar` ANTES de re-ingerir.")
    elif args.refetch and len(inauguradas) < len(novo_indice):
        comparadas = len(novo_indice) - len(inauguradas)
        print(f"\nnenhuma das {comparadas} fonte(s) com hash anterior mudou")
    if inauguradas:
        print(f"\n{len(inauguradas)} fonte(s) entraram no cache pela PRIMEIRA vez — não há hash "
              f"anterior, logo não há deriva a comparar ainda")

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
