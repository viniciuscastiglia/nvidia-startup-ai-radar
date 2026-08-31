"""Passo 6b do pipeline RAG do TAPI: a fusão dos dois braços da busca híbrida. Ver D-037.

DUAS FUNÇÕES, E A SEGUNDA É BRAÇO DE CONTROLE — NÃO CÓDIGO MORTO
------------------------------------------------------------------
`fundir_rrf` é o motor de produção. `fundir_soma` é a alternativa descartada, implementada e
medida no mesmo gabarito — o mesmo padrão de D-027, onde `fixo-800` existe para que "escolhi
chunking estrutural" vire um número em vez de uma afirmação. Custa ~20 linhas porque as duas
consomem exatamente as mesmas duas listas.

NENHUMA DAS DUAS FAZ I/O, E ISSO É A DECISÃO DE DESENHO QUE MAIS RENDE
-----------------------------------------------------------------------
Elas recebem listas já recuperadas. Como são funções puras dessas listas, a varredura
`K × peso × alfa` do harness custa **zero chamada de API** depois da primeira passada — o mesmo
truque que D-029 usou para o sweep de dimensão. A escolha do peso deixa de ser "chuta e torce" e
vira grade cheia.

POR QUE RRF É O DE PRODUÇÃO
----------------------------
O argumento não é "é o default do Elastic e do Qdrant" (embora seja, e isso resolva a pergunta na
banca em uma frase). O argumento é medido e é nosso: **D-033 provou que a magnitude do score denso
não é calibrada.** A q20, que não tem resposta na base, recuperou com 0,4813 — mais alto que o
pior acerto verdadeiro do gabarito, 0,2934. Uma fusão que consome magnitude consome um sinal que
já sabemos ser não confiável. RRF só olha posição, e é invariante a isso.

Some-se que os dois braços vivem em escalas sem unidade comum: a cosseno densa fica comprimida
entre 0,29 e 0,55, e o BM25 não tem máximo teórico.

O DEFEITO REAL DO RRF, QUE É POR ISSO QUE `K` É PARÂMETRO E NÃO A CONSTANTE 60
-------------------------------------------------------------------------------
Com `K=60` e listas de 20 — que é o `POOL_PADRAO` real deste sistema —, as contribuições vão de
1/61 a 1/80: **31% de amplitude**. O RRF degenera em "aparece nas duas listas?" e a informação de
ranking evapora. Em corpus grande isso não aparece porque as listas são longas; no nosso, aparece.
Com `K=10` a amplitude entre o 1º e o 10º vira ~2x, e o ranking volta a pesar. `K` é escolhido medindo, pelo mesmo
argumento que D-016 usa para `k1` e `b`.

A GARANTIA QUE PROTEGE O CASO CROSSLINGUAL
-------------------------------------------
Um documento que é 1º no braço denso e ausente do lexical soma `w_denso/(K+1)`. Um que é 1º no
lexical e ausente do denso soma `w_lexical/(K+1)`. Logo, **com `w_denso >= w_lexical`, o léxico
nunca desloca o 1º colocado do denso.** Isso importa porque a q05 pergunta em português sobre a
palavra "Portuguese" numa página em inglês: o braço lexical é mudo ali, e o caminho principal do
sistema real é justamente o crosslingual.

A soma ponderada com min-max tem uma garantia análoga no extremo (`alfa > 0,5`), então não vendo
essa como vantagem exclusiva. A diferença está no MEIO da lista, onde o min-max é dominado pelo
espalhamento dos scores daquela consulta e não pela relevância.
"""

from __future__ import annotations

from src.rag.busca import Passagem

Resultado = list[tuple[Passagem, float]]
Listas = dict[str, Resultado]
Pesos = dict[str, float]

# Constante da literatura (Cormack, Clarke & Buettcher, 2009). Está aqui como referência, NÃO
# como default do sistema — ver o defeito descrito no docstring.
K_RRF_LITERATURA = 60


def _por_id(listas: Listas) -> dict[int, Passagem]:
    """A fusão casa itens por `chunk_id` (D-041), não por texto."""
    return {p.chunk_id: p for lista in listas.values() for p, _ in lista}


def fundir_rrf(listas: Listas, pesos: Pesos, k: int) -> Resultado:
    """`s(d) = Σ_braço peso_braço / (k + posição_do_d_naquele_braço)`.

    Ausência de um braço contribui 0 — não é "score baixo", é "aquele braço não votou".

    `k` NÃO TEM DEFAULT, E ISSO É DE PROPÓSITO. Ele tinha um — 20 —, que não era nem o valor de
    produção (10, medido em D-037) nem a constante da literatura (60, logo acima). Um terceiro
    comportamento, não documentado e não medido, esperando um chamador distraído. Como o defeito
    do RRF descrito no docstring do módulo é justamente sobre a escolha de `k`, quem funde tem
    que dizer qual `k` está usando. Todos os chamadores já diziam.
    """
    passagens = _por_id(listas)
    acumulado: dict[int, float] = {cid: 0.0 for cid in passagens}

    for braco, lista in listas.items():
        peso = pesos.get(braco, 1.0)
        for posicao, (p, _) in enumerate(lista, start=1):
            acumulado[p.chunk_id] += peso / (k + posicao)

    ordenado = sorted(acumulado.items(), key=lambda x: -x[1])
    return [(passagens[cid], score) for cid, score in ordenado]


def _normalizar(scores: list[float], modo: str) -> list[float]:
    """Leva uma lista de scores para [0, 1]. Cada modo tem um jeito próprio de mentir."""
    if not scores:
        return []
    if modo == "minmax":
        lo, hi = min(scores), max(scores)
        # Faixa nula: todos iguais. Devolver 1.0 diria "todos perfeitos"; 0.0 diria "todos
        # inúteis". Meio-termo é a única leitura honesta de "não há informação de ordem aqui".
        if hi - lo < 1e-12:
            return [0.5] * len(scores)
        return [(s - lo) / (hi - lo) for s in scores]
    if modo == "soma":
        total = sum(scores)
        return [s / total for s in scores] if total else [0.0] * len(scores)
    raise ValueError(f"normalização desconhecida: {modo}")


def fundir_soma(listas: Listas, pesos: Pesos, norm: str = "minmax") -> Resultado:
    """Soma ponderada de scores normalizados. O BRAÇO DE CONTROLE de D-037.

    A NORMALIZAÇÃO É PARÂMETRO PORQUE ELA É A DECISÃO ESCONDIDA DENTRO DA DECISÃO — e todas as
    opções são ruins aqui:

    - `minmax` faz o 1º colocado valer 1,0 **por construção**, independentemente de ele ser bom.
      Na q20, que não tem resposta na base, os 0,4813 do denso viram 1,0 igualzinho a um acerto
      perfeito. Ela *fabrica* confiança exatamente onde o sistema precisa abster-se.
    - `soma` (dividir pelo total) não crava o topo em 1,0, mas continua dependendo da consulta:
      o mesmo score absoluto vale mais numa consulta com poucos candidatos fortes.

    Um documento ausente de um braço entra com 0 naquele braço — o que é assimétrico com o RRF,
    onde ausência é ausência de voto. Aqui ausência vira "medido e deu zero", que é diferente.
    É uma das razões de esta não ser a de produção.
    """
    passagens = _por_id(listas)
    acumulado: dict[int, float] = {cid: 0.0 for cid in passagens}

    for braco, lista in listas.items():
        peso = pesos.get(braco, 1.0)
        normalizados = _normalizar([s for _, s in lista], norm)
        for (p, _), valor in zip(lista, normalizados):
            acumulado[p.chunk_id] += peso * valor

    ordenado = sorted(acumulado.items(), key=lambda x: -x[1])
    return [(passagens[cid], score) for cid, score in ordenado]
