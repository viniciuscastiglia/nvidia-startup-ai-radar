"""Passo 6a do pipeline RAG do TAPI: o braço lexical da busca híbrida. Ver D-016 e D-036.

POR QUE BM25 EM PROCESSO E NÃO `ts_rank_cd` DO POSTGRES
--------------------------------------------------------
Está em D-016 e o resumo é: `ts_rank_cd` **não é BM25**. É cobertura de termos, sem saturação
de frequência nem normalização por comprimento. Chamar aquilo de BM25 no vídeo seria impreciso.
`bm25s` dá Okapi de verdade, com `k1` e `b` ajustáveis — e ajustável só vale se os valores forem
escolhidos, e é por isso que eles estão explícitos abaixo em vez de no default da biblioteca.

O QUE O BRAÇO LEXICAL TEM PARA FAZER AQUI, MEDIDO ANTES DE ESCREVER
--------------------------------------------------------------------
Somei o idf dos termos de cada consulta do gabarito que casam no corpus, marcando se caem no
documento esperado: **11 perguntas AJUDA · 5 MUDO · 2 ATRAPALHA · 1 neutro**.

As 5 mudas (q05, q06, q09, q12, q18) são as conceituais em português puro — léxico não atravessa
idioma. As 11 que ajudam são nome de produto e termo técnico que sobrevive à tradução: `colang`,
`batching`, `pytorch`, `scikit`, `vllm`. **A complementaridade com o denso é medida, não suposta**,
e é ela que justifica a fusão do passo 6b em vez de trocar um motor pelo outro.
"""

from __future__ import annotations

import re
import unicodedata

import bm25s

from src.db import conectar
from src.rag.busca import ESTRATEGIA_PADRAO, Passagem, para_citacao
from src.state import CitacaoRAG

# ─────────────────────────────────────────────────────────────────────────────
# Os parâmetros do Okapi, explícitos porque D-016 justifica a escolha por eles
# ─────────────────────────────────────────────────────────────────────────────

# MÉTODO: `lucene`, não o `robertson` (o Okapi original). Medido neste corpus: a palavra
# "nvidia" ocorre em 163 dos 177 chunks (92%), e o IDF de Robertson para ela é **−2,42** —
# negativo. Com o Okapi original, um chunk seria PUNIDO por conter a marca, numa base que é
# inteiramente documentação da NVIDIA e em consultas que quase sempre dizem "NVIDIA". O IDF do
# Lucene, `ln(1 + (N-df+0.5)/(df+0.5))`, é sempre positivo: 0,0850 no mesmo caso.
# Corpus pequeno e temático é exatamente onde essa diferença morde.
METODO = "lucene"

# k1 — saturação de frequência de termo. Alto = repetir o termo continua valendo; baixo = satura
# rápido. 1.2 é o valor clássico do Okapi. Importa concretamente na q14: "pandas" ocorre 15 vezes
# em 2 chunks do cuDF contra 3 vezes em 1 do RAPIDS, e é a repetição que separa os dois.
K1 = 1.2

# b — normalização por comprimento. 0.75 é o clássico. Aqui ele pesa menos que o normal porque o
# chunker estrutural JÁ normaliza comprimento numa banda de 120 a 450 tokens (D-025): a variação
# que `b` existe para corrigir foi em boa parte corrigida antes, no passo 3.
B = 0.75

# ─────────────────────────────────────────────────────────────────────────────
# Tokenização — três decisões, todas medidas (D-036)
# ─────────────────────────────────────────────────────────────────────────────

# 1. DOBRA DE ACENTO. Sem `NFD` + remoção de diacrítico, o `re` parte a palavra no acento:
#    "genômica" -> "gen" + "mica", "inferência" -> "infer" + "ncia", "português" -> "portugu" + "s".
#    Metade do vocabulário das consultas viraria lixo — e virou, na primeira medição do gabarito,
#    onde a q12 apareceu como ATRAPALHA por causa do termo espúrio "gen".
#
# 2. O PONTO SOBREVIVE ENTRE ALFANUMÉRICOS E MORRE NO FIM DA FRASE. `cudf.pandas` é identificador
#    e é a âncora da q14; `containers.` é pontuação. A regex casa o token maximal, então os dois
#    casos saem certos sem tratamento especial.
#    Efeito colateral aceito: uma ocorrência de "cudf.pandas" NÃO conta como ocorrência de
#    "pandas". Nas páginas reais o termo solto aparece muitas vezes ao lado, então a perda é
#    pequena — e a alternativa (emitir o token inteiro E as partes) inflaria tf e comprimento
#    do documento, mexendo em `k1` e `b` por via indireta.
#
# 3. SEM STEMMER. `PyStemmer` seria dependência nova, e stemming de inglês não ajuda consulta em
#    português — o valor do léxico aqui é nome literal de produto, que stemmer nenhum melhora.
_TOKEN = re.compile(r"[a-z0-9]+(?:\.[a-z0-9]+)*")

# Lista curta e explícita, PT + EN, porque os dois idiomas se encontram aqui: as consultas são em
# português e o corpus é em inglês. Termos de altíssimo df já são quase neutralizados pelo IDF do
# Lucene; tirá-los serve sobretudo para o comprimento do documento não inflar e distorcer `b`.
STOPWORDS = frozenset("""
a o as os um uma uns umas de do da dos das em no na nos nas por pelo pela para com sem sob sobre
ao aos que qual quais quanto quantos quando como onde se ja mais menos muito pouco ha tem tenho
temos pode podem posso e ou nao sim isso este esta esse essa aquele aquela seu sua meu minha
entre antes depois ate desde numa num dele dela lhe eu voce nos eles elas ser estar foi era
the a an and or of in on at to for with without from by as is are was were be been being this
that these those it its their his her our your my we you they he she i not no do does did can
could should would will shall may might must have has had there here what which who whom whose
when where why how all any both each few more most other some such only own same so than too very
""".split())


def dobrar_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if not unicodedata.combining(c))


def tokenizar(texto: str) -> list[str]:
    """Texto -> tokens. Ver as três decisões acima."""
    return [
        t for t in _TOKEN.findall(dobrar_acentos(texto).lower())
        if len(t) > 1 and t not in STOPWORDS
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Índice — em memória, uma vez por estratégia, por run
# ─────────────────────────────────────────────────────────────────────────────

# D-016 justifica o índice em processo pelo corpus ser pequeno e ESTÁTICO: 177 chunks,
# reconstruir custa milissegundos. Persistir em disco seria complexidade sem ganho, e ainda
# criaria a pergunta "o índice está atualizado com o banco?" — que hoje não existe.
_INDICES: dict[str, tuple[bm25s.BM25, list[Passagem]]] = {}

SQL_CORPUS = """
SELECT id, tecnologia, texto, texto_indexado, caminho_secao, documento_url
FROM chunks_nvidia WHERE estrategia = %(estrategia)s ORDER BY id
"""


def _indice(estrategia: str) -> tuple[bm25s.BM25, list[Passagem]]:
    if estrategia in _INDICES:
        return _INDICES[estrategia]

    with conectar() as cx, cx.cursor() as cur:
        cur.execute(SQL_CORPUS, {"estrategia": estrategia})
        linhas = cur.fetchall()

    passagens = [
        Passagem(
            chunk_id=l["id"],
            tecnologia=l["tecnologia"],
            texto=l["texto"],
            texto_indexado=l["texto_indexado"],
            caminho_secao=l["caminho_secao"],
            documento_url=l["documento_url"],
        )
        for l in linhas
    ]
    # Indexa `texto_indexado`, o MESMO campo que foi embedado. Isso não é detalhe: é o que faz o
    # breadcrumb de D-025 servir aos dois motores. Sem ele, uma busca lexical por "TensorRT-LLM"
    # não acharia a bullet de quantização que a janela fixa separou da palavra.
    corpus = [tokenizar(p.texto_indexado) for p in passagens]

    retriever = bm25s.BM25(k1=K1, b=B, method=METODO)
    retriever.index(corpus, show_progress=False)
    _INDICES[estrategia] = (retriever, passagens)
    return _INDICES[estrategia]


def invalidar_indice() -> None:
    """Só para teste e para depois de re-ingerir o corpus."""
    _INDICES.clear()


def buscar_lexical_bruto(
    consulta: str, k: int = 10, estrategia: str = ESTRATEGIA_PADRAO
) -> list[tuple[Passagem, float]]:
    """Os k chunks com maior score BM25. Mesma assinatura de `buscar_denso_bruto`."""
    retriever, passagens = _indice(estrategia)
    tokens = tokenizar(consulta)
    if not tokens:
        return []

    indices, scores = retriever.retrieve([tokens], k=min(k, len(passagens)), show_progress=False)
    # Score 0 significa "nenhum termo da consulta ocorre neste chunk" — é ausência de evidência
    # lexical, não evidência fraca. Deixar entrar poluiria o pool da fusão com ruído ranqueado.
    return [
        (passagens[int(i)], float(s))
        for i, s in zip(indices[0], scores[0])
        if s > 0
    ]


def buscar_lexical(
    consulta: str, k: int = 10, estrategia: str = ESTRATEGIA_PADRAO
) -> list[CitacaoRAG]:
    """Mesma assinatura de `buscar_denso` — é o que deixa o harness trocar de motor."""
    return [para_citacao(p, lexical=s) for p, s in buscar_lexical_bruto(consulta, k, estrategia)]
