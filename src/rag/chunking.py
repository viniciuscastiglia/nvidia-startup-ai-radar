"""Passo 3 do pipeline RAG do TAPI: chunking semântico. Ver D-025, D-026 e D-027.

A DECISÃO, EM UMA FRASE
-----------------------
A unidade é a **seção que o autor do documento escreveu**, normalizada para uma banda de
tamanho e indexada com o **caminho da seção prefixado**.

POR QUE NÃO JANELA FIXA — e este é o argumento que vale a decisão inteira
--------------------------------------------------------------------------
Medi o corpus antes de escolher (23/08/2026). Os `h3` da página do NIM incluem `Benefits`,
`Models`, `Features`, `Technology` — headings que não nomeiam produto nenhum. Uma janela fixa
corta a bullet

    - Quantização: FP8, FP4, INT8, INT4 com AWQ

e a separa para sempre da palavra "TensorRT-LLM". O denso ainda recupera por "quantização",
mas o **BM25 por "TensorRT-LLM" não recupera**, e o LLM que ler esse trecho não tem como
atribuir a tecnologia. Isso é perda de ATRIBUIÇÃO, e atribuição é o 7º campo obrigatório do
output do TAPI. Prefixar o caminho resolve para o denso e para o léxico ao mesmo tempo.

POR QUE AS DUAS NORMALIZAÇÕES SÃO CAMINHO PRINCIPAL, NÃO CASO DE CANTO
-----------------------------------------------------------------------
Também medido, e é o número que desenhou o algoritmo:

    NVIDIA NIM      51 seções /  9.909 chars  = ~194 chars por seção  -> FUNDE
    NVIDIA NeMo    102 seções / 22.160 chars  = ~217 chars por seção  -> FUNDE
    TensorRT-LLM     8 seções / 27.060 chars  = ~3.383 chars por seção -> DIVIDE

Um chunk por heading daria fragmento inútil nas páginas de produto e bloco grande demais nos
READMEs. Cada passagem manda em um tipo de documento do corpus.

AS DUAS REGRAS, CADA UMA EM UMA FRASE
--------------------------------------
- **Fundir:** acumula seções consecutivas até o piso; descarrega no piso, ou na troca de pai
  desde que já tenha metade do piso — para não emitir fragmento e também não colar dois
  assuntos sem relação.
- **Dividir:** enche até o teto em limite de parágrafo, com um parágrafo de sobreposição entre
  partes consecutivas, para que uma frase partida ao meio ainda apareça inteira em algum chunk.

O QUE `estrategia='fixo-800'` É, E O QUE ELA NÃO É
---------------------------------------------------
É o BRAÇO DE CONTROLE (D-027), não código morto: janela fixa, sem caminho prefixado, que é o
que se obtém dividindo e embedando sem pensar. A diferença de recall@k entre as duas mede o
pacote "estrutura + breadcrumb" junto. Separar as duas contribuições exige um terceiro braço
(janela fixa COM breadcrumb) — é uma linha a mais e fica para a sessão 04, que é onde a
pergunta "quanto vale cada metade?" precisa de resposta.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

import tiktoken
from bs4 import BeautifulSoup

from src.rag.limpeza import RUIDO_HTML, limpar_linhas, normalizar_markdown

# tiktoken é o tokenizer da OpenAI, NÃO o do NeMo Retriever. É aproximação deliberada: serve
# para dimensionar a banda, e a banda carrega margem por causa disso. Medi em 23/08 que o
# embedder aceita entre 6.144 e 8.192 tokens — ou seja, o teto abaixo NÃO é imposto pelo
# modelo. É escolha de precisão de recuperação.
_TOKENIZADOR = tiktoken.get_encoding("cl100k_base")

# PISO: abaixo de ~120 tokens um chunk raramente carrega um fato técnico completo — é o
# fragmento "- Quantização: FP8, FP4" sem o que o cerca.
PISO_TOKENS = 120

# TETO: NENHUM DOS DOIS MOTORES IMPÕE ESTE NÚMERO — medi os dois (D-029, D-034, D-046). O
# embedder aceita 6.144-8.192 tokens; o reranker atual (`rerank-qa-mistral-4b`) aceita ~6.958
# somando query e passagem, re-medido em 25/08 depois de o 1B de D-034 morrer com HTTP 410.
# 450 é ~6% da janela do reranker, não 88% dela como o comentário de antes de D-034 supunha ao
# falar em "512 de cross-encoder". Aquela janela nunca existiu em nenhum dos dois modelos.
#
# A janela encolheu 15% na troca de stack e continua sendo 15x o teto: o argumento não depende
# do valor exato, que é o ponto de tê-lo medido em vez de citado.
#
# O que o reranker de fato diz sobre o teto é outra coisa, e é DILUIÇÃO — o motor não PROÍBE
# chunk grande, ele COBRA por chunk grande. ATENÇÃO: a curva de diluição foi medida no 1B e
# **não foi re-medida** no 4B (D-046). Ela dizia que a cobrança começa entre 380 e 564 tokens
# com texto real e depois satura (revisão da sessão 03, §2.3), o que punha 450 confortavelmente
# dentro da região barata. Enquanto não for re-medida, o teto é INSPEÇÃO e não medição.
#
# Consequência prática: qualquer sweep de banda de chunk precisa re-medir a diluição ANTES de
# escolher a faixa de busca — a de ~120 a ~560 é do modelo antigo.
TETO_TOKENS = 450

# Tags que forçam quebra de linha ao achatar HTML. Sem isto, `get_text()` cola o fim de um
# parágrafo no começo do próximo e a divisão por parágrafo perde os limites.
_BLOCOS_HTML = {
    "p", "div", "li", "tr", "td", "th", "section", "article", "pre", "blockquote",
    "h4", "h5", "h6", "dt", "dd", "figcaption", "br", "ul", "ol", "table",
}

Formato = Literal["html", "markdown"]


def contar_tokens(texto: str) -> int:
    return len(_TOKENIZADOR.encode(texto))


@dataclass(frozen=True)
class MetaDocumento:
    """O que a curadoria sabe e o texto não diz."""

    tecnologia: str
    documento_url: str      # url_citacao do manifesto: a que um humano abre
    titulo_documento: str
    formato: Formato


@dataclass(frozen=True)
class Chunk:
    tecnologia: str
    documento_url: str
    titulo_documento: str
    caminho_secao: str
    texto: str              # limpo — vira CitacaoRAG.trecho
    texto_indexado: str     # o que é embedado
    ordinal: int
    n_tokens: int
    estrategia: str


@dataclass
class _Secao:
    nivel: int              # 1, 2 ou 3
    titulo: str
    corpo: str


# ─────────────────────────────────────────────────────────────────────────────
# Extração de estrutura — um parser por formato declarado no manifesto
# ─────────────────────────────────────────────────────────────────────────────

_ATX = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_SETEXT = re.compile(r"^(=+|-{3,})\s*$")


def secoes_de_markdown(texto: str) -> list[_Secao]:
    """Quebra markdown em seções por heading ATX (`##`) e setext (`====` / `----`).

    OS DOIS PRECISAM SER TRATADOS: o README do TensorRT-LLM abre com título setext
    (`TensorRT LLM` sobre uma linha de `=`) e usa `<h4>` embutido no meio do markdown.
    Um parser que só entendesse `#` perderia o título do documento inteiro.

    Heading de nível 4 a 6 NÃO abre seção — vira linha de corpo. Assim o subtópico não some,
    mas também não vira um chunk de três palavras.
    """
    texto = normalizar_markdown(texto)
    linhas = texto.split("\n")
    secoes: list[_Secao] = [_Secao(0, "", "")]
    i = 0
    dentro_de_codigo = False

    while i < len(linhas):
        linha = linhas[i]

        # Bloco de código é conteúdo, não estrutura: `# comentário` lá dentro não é heading.
        if linha.lstrip().startswith("```"):
            dentro_de_codigo = not dentro_de_codigo
            secoes[-1].corpo += linha + "\n"
            i += 1
            continue
        if dentro_de_codigo:
            secoes[-1].corpo += linha + "\n"
            i += 1
            continue

        atx = _ATX.match(linha)
        proxima = linhas[i + 1] if i + 1 < len(linhas) else ""
        # Setext: linha de conteúdo seguida de ==== ou ----. O `|---|` de tabela não casa
        # porque a regex exige a linha inteira; o `---` de regra horizontal não casa porque
        # exige linha anterior não vazia.
        setext = _SETEXT.match(proxima) and linha.strip() and not _ATX.match(linha)

        if atx:
            nivel, titulo = len(atx.group(1)), atx.group(2).strip()
            if nivel <= 3:
                secoes.append(_Secao(nivel, titulo, ""))
            else:
                secoes[-1].corpo += titulo + "\n"
            i += 1
        elif setext:
            nivel = 1 if proxima.strip().startswith("=") else 2
            secoes.append(_Secao(nivel, linha.strip(), ""))
            i += 2
        else:
            secoes[-1].corpo += linha + "\n"
            i += 1

    return [s for s in secoes if s.titulo or s.corpo.strip()]


class _Acumulador:
    """Estado do percurso no DOM: monta seções enquanto anda em ordem de documento."""

    def __init__(self) -> None:
        self.secoes: list[_Secao] = [_Secao(0, "", "")]

    def texto(self, t: str) -> None:
        self.secoes[-1].corpo += t

    def quebra(self) -> None:
        if not self.secoes[-1].corpo.endswith("\n"):
            self.secoes[-1].corpo += "\n"

    def nova_secao(self, nivel: int, titulo: str) -> None:
        self.secoes.append(_Secao(nivel, titulo, ""))


def secoes_de_html(html: str) -> list[_Secao]:
    """Percorre o DOM em ordem de documento, abrindo seção a cada h1/h2/h3.

    POR QUE PERCORRER E NÃO FATIAR POR `next_siblings`: nas páginas de produto da NVIDIA os
    headings e o conteúdo que eles introduzem moram em `div`s diferentes — não são irmãos.
    Fatiar por irmão devolveria seções vazias. O percurso recursivo não depende de onde a
    página resolveu pôr os `div`.
    """
    sopa = BeautifulSoup(html, "lxml")
    for tag in sopa(RUIDO_HTML):
        tag.decompose()
    raiz = sopa.find("main") or sopa.find("article") or sopa.body or sopa

    acc = _Acumulador()

    def percorrer(no) -> None:
        for filho in no.children:
            nome = getattr(filho, "name", None)
            if nome is None:
                conteudo = str(filho).strip()
                if conteudo:
                    acc.texto(conteudo + " ")
                continue
            if nome in ("h1", "h2", "h3"):
                acc.nova_secao(int(nome[1]), filho.get_text(" ", strip=True))
                continue
            if nome in _BLOCOS_HTML:
                acc.quebra()
                percorrer(filho)
                acc.quebra()
            else:
                percorrer(filho)

    percorrer(raiz)

    for s in acc.secoes:
        s.corpo = limpar_linhas(s.corpo)     # filtro de menu residual: só HTML
    return [s for s in acc.secoes if s.titulo or s.corpo.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# Caminho da seção (o breadcrumb)
# ─────────────────────────────────────────────────────────────────────────────

def _com_caminho(secoes: list[_Secao], tecnologia: str) -> list[tuple[tuple[str, ...], str]]:
    """Converte a lista plana de seções em (caminho, corpo).

    O PRIMEIRO ELEMENTO DO CAMINHO É SEMPRE A TECNOLOGIA, e vem do manifesto de curadoria —
    nunca do heading. É a razão de ser desta função: `Benefits` e `Models` são headings reais
    do corpus e não nomeiam nada. Sem esta âncora, o prefixo seria inútil justamente nos
    chunks onde ele mais importa.
    """
    saida: list[tuple[tuple[str, ...], str]] = []
    pilha: list[tuple[int, str]] = []

    for s in secoes:
        if s.titulo:
            while pilha and pilha[-1][0] >= s.nivel:
                pilha.pop()
            pilha.append((s.nivel, s.titulo))
        corpo = s.corpo.strip()
        if corpo:
            caminho = (tecnologia, *(t for _, t in pilha))
            saida.append((caminho, corpo))
    return saida


def _prefixo_comum(caminhos: list[tuple[str, ...]]) -> tuple[str, ...]:
    comum = caminhos[0]
    for c in caminhos[1:]:
        n = 0
        while n < min(len(comum), len(c)) and comum[n] == c[n]:
            n += 1
        comum = comum[:n]
    return comum or (caminhos[0][0],)


# ─────────────────────────────────────────────────────────────────────────────
# As duas normalizações de tamanho
# ─────────────────────────────────────────────────────────────────────────────

def _e_troca_de_pai(anterior: tuple[str, ...], novo: tuple[str, ...]) -> bool:
    """O novo bloco pertence a outro ramo da árvore?

    COMPARA COM O BLOCO ANTERIOR, NÃO COM O PREFIXO COMUM DO BUFFER — e a diferença é a
    correção de um defeito real. O prefixo comum é dominado pelo membro mais RASO do buffer:
    basta um parágrafo de introdução de 8 tokens (que mora no h1) para achatar o prefixo, e
    a partir daí nenhum bloco consegue encurtá-lo mais. A regra nunca mais disparava e o
    documento inteiro virava um chunk só.

    Descendente (`A > B` -> `A > B > C`) e irmão (`A > B > C` -> `A > B > D`) continuam o
    mesmo assunto. Só é troca de pai quando o caminho comum é mais curto que o do irmão.
    """
    n = 0
    while n < min(len(anterior), len(novo)) and anterior[n] == novo[n]:
        n += 1
    return n < len(anterior) - 1


def _fundir(
    blocos: list[tuple[tuple[str, ...], str]], piso: int, teto: int
) -> list[tuple[tuple[str, ...], str]]:
    """Acumula seções consecutivas até o piso. Ver a regra no docstring do módulo.

    O TETO ENTRA AQUI, e não só na divisão: fundir dois blocos acima do teto para dividi-los
    de volta logo em seguida é perda pura — troca dois breadcrumbs específicos ("... >
    Quantization", "... > Algorithmic Optimizations") por um genérico, sem ganhar nada.
    """
    saida: list[tuple[tuple[str, ...], str]] = []
    buffer: list[tuple[tuple[str, ...], str]] = []

    def descarregar() -> None:
        if not buffer:
            return
        caminho = _prefixo_comum([c for c, _ in buffer])
        partes: list[str] = []
        for cam, txt in buffer:
            # O sub-título que ficou abaixo do prefixo comum entra INLINE no texto, senão o
            # subtópico some ao fundir quatro irmãs numa só.
            extra = cam[len(caminho):]
            if extra and len(buffer) > 1:
                partes.append(" / ".join(extra))
            partes.append(txt)
        saida.append((caminho, "\n".join(partes)))
        buffer.clear()

    for caminho, texto in blocos:
        if buffer:
            total = contar_tokens("\n".join(t for _, t in buffer))
            estouraria = total + contar_tokens(texto) > teto
            troca_de_pai = _e_troca_de_pai(buffer[-1][0], caminho)
            if total >= piso or estouraria or (troca_de_pai and total >= piso // 2):
                descarregar()
        buffer.append((caminho, texto))
    descarregar()
    return saida


def _dividir(texto: str, teto: int) -> list[str]:
    """Enche até o teto em limite de parágrafo, com um parágrafo de sobreposição."""
    paragrafos = [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]

    # Parágrafo maior que o teto sozinho (bloco de bullets sem linha em branco, tabela longa):
    # desce um nível e quebra por linha. Se até uma linha estourar, quebra por token — é o
    # último recurso e o único lugar do chunker que corta no meio de uma frase.
    granulares: list[str] = []
    for p in paragrafos:
        if contar_tokens(p) <= teto:
            granulares.append(p)
            continue
        for linha in p.split("\n"):
            if contar_tokens(linha) <= teto:
                granulares.append(linha)
            else:
                ids = _TOKENIZADOR.encode(linha)
                for i in range(0, len(ids), teto):
                    granulares.append(_TOKENIZADOR.decode(ids[i:i + teto]))

    partes: list[str] = []
    atual: list[str] = []
    for p in granulares:
        candidato = atual + [p]
        if atual and contar_tokens("\n\n".join(candidato)) > teto:
            partes.append("\n\n".join(atual))
            atual = [atual[-1], p] if len(atual) > 1 else [p]    # sobreposição de 1 parágrafo
        else:
            atual = candidato
    if atual:
        partes.append("\n\n".join(atual))
    return partes


# ─────────────────────────────────────────────────────────────────────────────
# As duas estratégias
# ─────────────────────────────────────────────────────────────────────────────

def _montar(
    caminho: tuple[str, ...], texto: str, meta: MetaDocumento, ordinal: int, estrategia: str,
    com_caminho: bool = True,
) -> Chunk:
    trilha = " > ".join(caminho)
    indexado = f"{trilha}\n\n{texto}" if com_caminho else texto
    return Chunk(
        tecnologia=meta.tecnologia,
        documento_url=meta.documento_url,
        titulo_documento=meta.titulo_documento,
        caminho_secao=trilha,
        texto=texto,
        texto_indexado=indexado,
        ordinal=ordinal,
        n_tokens=contar_tokens(indexado),
        estrategia=estrategia,
    )


def chunk_estrutural(
    bruto: str, meta: MetaDocumento, piso: int = PISO_TOKENS, teto: int = TETO_TOKENS
) -> list[Chunk]:
    """A estratégia de D-025. Função pura: texto entra, chunks saem. Sem rede, sem banco."""
    secoes = (secoes_de_markdown(bruto) if meta.formato == "markdown"
              else secoes_de_html(bruto))
    blocos = _com_caminho(secoes, meta.tecnologia)
    if not blocos:
        return []

    fundidos = _fundir(blocos, piso, teto)

    chunks: list[Chunk] = []
    for caminho, texto in fundidos:
        # O TETO VALE PARA O TEXTO QUE É EMBEDADO, e o que é embedado inclui o breadcrumb.
        # Dividir por `teto` e só depois prefixar produziria chunks acima do teto — medi 457
        # com teto de 450 antes desta correção. Descontar aqui mantém a promessa do limite.
        custo_caminho = contar_tokens(" > ".join(caminho)) + 2      # +2 pelas duas quebras
        for parte in _dividir(texto, max(1, teto - custo_caminho)):
            chunks.append(_montar(caminho, parte, meta, len(chunks), "estrutural-v1"))
    return chunks


def chunk_fixo(
    bruto: str, meta: MetaDocumento, tamanho: int = 800, sobreposicao: float = 0.15
) -> list[Chunk]:
    """O braço de controle de D-027: janela fixa em caracteres, sem estrutura e sem caminho.

    Deliberadamente ingênuo — é o que se obtém dividindo e embedando sem pensar. `caminho_secao`
    guarda o nome da tecnologia só para exibição; ele NÃO entra em `texto_indexado`, senão o
    controle já teria metade do tratamento que ele existe para comparar.
    """
    texto = (normalizar_markdown(bruto) if meta.formato == "markdown"
             else limpar_linhas("\n".join(s.corpo for s in secoes_de_html(bruto))))

    passo = max(1, int(tamanho * (1 - sobreposicao)))
    chunks: list[Chunk] = []
    for inicio in range(0, len(texto), passo):
        fatia = texto[inicio:inicio + tamanho].strip()
        if fatia:
            chunks.append(
                _montar((meta.tecnologia,), fatia, meta, len(chunks),
                        f"fixo-{tamanho}", com_caminho=False)
            )
        if inicio + tamanho >= len(texto):
            break
    return chunks
