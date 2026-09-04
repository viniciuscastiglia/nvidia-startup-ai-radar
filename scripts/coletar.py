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
página, e não uma paráfrase: quem abrir a `url_fonte` tem de encontrar lá o trecho que o sistema
citou. Paráfrase quebra a rastreabilidade sem que nada acuse.

USO
---
    python scripts/coletar.py <url> [--max-chars 4000]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rag.limpeza import RUIDO_HTML, limpar_linhas

CABECALHOS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

# RUIDO_HTML e limpar_linhas vivem em src/rag/limpeza.py: são o passo 2 do pipeline RAG
# (limpeza e normalização) e a ingestão da base NVIDIA usa exatamente os mesmos. Script
# depende de src, nunca o contrário — e a curadoria enxerga o mesmo texto que o embedder.


def extrair(html: str) -> tuple[str, str]:
    sopa = BeautifulSoup(html, "lxml")
    titulo = (sopa.title.get_text(strip=True) if sopa.title else "") or ""

    for tag in sopa(RUIDO_HTML):
        tag.decompose()

    # O MAIOR BLOCO, E NÃO O PRIMEIRO (03/09, D-090)
    # ------------------------------------------------
    # A versão anterior era `find("main") or find("article") or body`: preferência por tipo de
    # tag, resolvida pela ORDEM no documento. Medido em 03/09, ela mata duas das melhores
    # fontes da curadoria brasileira, e por dois caminhos diferentes:
    #
    #   braziljournal.com  o único <main> é uma tarja de teaser  ->  48 chars (corpo: 4.110)
    #   agfeed.com.br      não há <main>; o 1º <article> é o card ->  384 chars (corpo: 7.122)
    #
    # Em ambos os casos o texto ESTÁ na página — o seletor é que pegava a chamada em vez da
    # matéria. Tamanho é a heurística certa aqui porque a pergunta da curadoria é "onde está o
    # corpo do texto?", e a resposta é o bloco com mais prosa depois de `RUIDO_HTML` derrubar
    # nav/header/footer/aside. `<body>` entra como candidato — é ele que ganha nos dois sites
    # acima — e continua perdendo para o <article> certo quando a página o marca direito.
    #
    # O CUSTO, E ELE É REAL: o bloco maior traz junto post relacionado. Medido nos domínios já
    # usados na base: 5.062->5.390, 5.553->6.163, 3.245->4.649. Esse excedente é chamada de
    # outra empresa, e contaminação entre empresas é o defeito que D-086 e D-089 perseguiram.
    # Quem o remove é o curador ao recortar — este script imprime para leitura humana, nunca
    # escreve fixture. Ver o portão 4 da curadoria no plano de 03/09.
    #
    # POR QUE ISTO É BARATO: `coletar.py` é auxiliar de CURADORIA, não caminho de execução.
    # Nenhum agente o chama, `seed.py` lê YAML, e os `conteudo_texto` das fixtures existentes
    # já estão congelados. Mudá-lo não move um único número medido.
    candidatos = [*sopa.find_all("main"), *sopa.find_all("article")]
    if sopa.body:
        candidatos.append(sopa.body)
    # `\n` SÓ ENTRE BLOCOS — O INLINE VAI COM ESPAÇO (03/09, D-097)
    # ---------------------------------------------------------------
    # `get_text(separator="\n")` põe TODO elemento em linha própria, inclusive o inline. Nas
    # matérias brasileiras o nome da empresa vem quase sempre num `<a>` — `<a>Agrotools</a>` —
    # e virava uma linha de UMA palavra. Aí `limpar_linhas` a descartava por ser curta e não
    # terminar em pontuação, e o que sobrava no documento era:
    #
    #     "…afirma o CEO da"  /  "."  /  "Sergio Rocha, fundador e CEO da Agrotools"
    #
    # A ironia é exata: **o nome morre e o "." sobrevive**, porque o ponto termina em pontuação.
    # Medido nas 30 fixtures de 03/09: 62 parágrafos que eram só pontuação e 203 terminando em
    # preposição pendurada, em 62 dos 93 documentos.
    #
    # O CONSERTO É DESMONTAR O INLINE ANTES, E SÃO **DUAS** CHAMADAS, NÃO UMA:
    #   `.unwrap()` tira a tag — mas o BeautifulSoup deixa os nós de texto SEPARADOS, e
    #   `get_text("\n")` continua pondo um `\n` entre eles. Medido: sozinho, não muda nada.
    #   `.smooth()` funde os NavigableStrings adjacentes, e é ele que faz o nome voltar
    #   para dentro da frase.
    # Medido nesta mesma URL: `afirma o CEO da` / `.`  ->  `afirma o CEO da Agrotools.`
    #
    # ISTO NÃO CONSERTA AS 93 FIXTURES JÁ COLETADAS, e é importante dizer: o nome apagado não
    # está mais no texto delas. Recuperá-lo exige re-coletar e re-recortar à mão, incluindo as
    # 8 fixtures de gabarito — a 6 dias da entrega, é mexer em material medido por 1,7% das
    # citações. Isto vale da próxima coleta em diante; o resíduo visível (a pontuação órfã) o
    # portão do `seed.py` remove, e a frase decapitada fica como limitação conhecida.
    for inline in sopa.find_all(["a", "strong", "b", "em", "i", "span",
                                 "abbr", "mark", "sup", "sub", "code"]):
        inline.unwrap()
    sopa.smooth()
    textos = [c.get_text(separator="\n", strip=True) for c in candidatos]
    texto = max(textos, key=len) if textos else sopa.get_text(separator="\n", strip=True)

    return titulo, limpar_linhas(texto)


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
