"""Auxiliar de CURADORIA: busca uma URL e extrai o texto legível da página.

ONDE ISTO FICA EM RELAÇÃO AO ESCOPO DO TAPI
--------------------------------------------
O TAPI põe explicitamente FORA de escopo "a construção de crawlers, scrapers ou qualquer
pipeline de coleta automatizada na web". Esta ferramenta não é isso, e a diferença importa:

- um crawler segue links e coleta em escala, sozinho, decidindo o que entra na base;
- isto busca UMA URL que um humano escolheu e imprime o texto para ele ler, recortar e
  colar numa fixture curada à mão.

Todas as decisões de curadoria — qual empresa, qual página, qual trecho, qual tipo de
documento — continuam humanas. Este script não escreve no banco e não é chamado por nenhum
agente em tempo de execução. Ele existe para que `conteudo_texto` seja o texto REAL da
página, e não uma paráfrase — o que é requisito de credibilidade: o avaliador abre a
`url_fonte` e compara.

USO
---
    python scripts/coletar.py <url> [--max-chars 4000]
"""

from __future__ import annotations

import argparse
import re
import sys

import httpx
from bs4 import BeautifulSoup

CABECALHOS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

# Boilerplate que não é conteúdo: some antes da extração.
RUIDO = ["script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg"]


def extrair(html: str) -> tuple[str, str]:
    sopa = BeautifulSoup(html, "lxml")
    titulo = (sopa.title.get_text(strip=True) if sopa.title else "") or ""

    for tag in sopa(RUIDO):
        tag.decompose()

    # Prefere <main> ou <article> quando a página os declara; senão cai para o <body>.
    principal = sopa.find("main") or sopa.find("article") or sopa.body or sopa
    texto = principal.get_text(separator="\n", strip=True)

    # Colapsa linhas vazias e descarta linhas de uma palavra só (menu residual).
    linhas = [ln.strip() for ln in texto.split("\n")]
    linhas = [ln for ln in linhas if len(ln.split()) > 2 or ln.endswith((".", "!", "?"))]
    texto = "\n".join(linhas)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return titulo, texto.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("url")
    ap.add_argument("--max-chars", type=int, default=4000)
    args = ap.parse_args()

    try:
        with httpx.Client(follow_redirects=True, timeout=30.0, headers=CABECALHOS) as cli:
            r = cli.get(args.url)
        print(f"HTTP {r.status_code}  ·  {r.headers.get('content-type','?')}", file=sys.stderr)
        r.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        print(f"FALHA: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    titulo, texto = extrair(r.text)
    print(f"=== TITULO === {titulo}")
    print(f"=== {len(texto)} caracteres extraídos ===")
    print(texto[: args.max_chars])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
