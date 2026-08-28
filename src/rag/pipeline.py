"""Composição dos passos 6, 7 e 8 do pipeline RAG do TAPI — a porta de entrada do RAG.

`responder()` é a única função que o resto do sistema precisa conhecer.

POR QUE ESTE MÓDULO EXISTE, E NÃO É MAIS UM "PASSO"
-----------------------------------------------------
A convenção do repositório é **um passo do pipeline = um módulo em `src/rag/`**: `limpeza` (2),
`chunking` (3), `busca` (6a denso), `lexical` (6a léxico), `fusao` (6b), `rerank` (7),
`geracao` (8). Este aqui não é um passo — é a **composição** deles, e ele existe por uma razão
concreta: pôr a orquestração dentro de `busca.py` criaria ciclo de import, porque `lexical`,
`fusao` e `rerank` todos importam `Passagem` de `busca`.

A alternativa seria import tardio dentro das funções para quebrar o ciclo. Um módulo de
composição com nome óbvio é mais honesto que um `import` escondido no meio de uma função.

O QUE É CONFIGURÁVEL AQUI E POR QUÊ
------------------------------------
Todos os parâmetros de fusão são argumentos com default, e os defaults saíram da varredura
medida em D-037 — não de intuição. `peso_lexical=0.0` reduz a híbrida ao denso puro exatamente,
que é a linha de base de D-032: é o botão de desligar o braço lexical sem tocar em código.
"""

from __future__ import annotations

from src.config import RERANK
from src.rag.busca import ESTRATEGIA_PADRAO, Passagem, buscar_denso_bruto, para_citacao
from src.rag.fusao import fundir_rrf, fundir_soma
from src.rag.geracao import gerar
from src.rag.lexical import buscar_lexical_bruto
from src.rag.rerank import reranquear
from src.state import CitacaoRAG, RespostaRAG

# Quantos candidatos cada braço traz antes da fusão. Não é o k da resposta: é o tamanho do funil
# que o cross-encoder vai reordenar. 20 por braço dá uma união de **20 a 39** nas 24 consultas do
# gabarito, média 29,1 — e 20 exatos em três delas (q02, q11, q18), onde o braço lexical vem curto
# ou vazio. Medido, não estimado: quanto mais os dois braços discordam, maior a união e mais o
# passo 7 custa. É o preço real do braço lexical.
# (A faixa escrita aqui até 24/08 era "28 a 34", de uma estimativa; a contagem real é esta.)
POOL_PADRAO = 20

# Defaults medidos em D-037. K=10 e não os 60 da literatura porque com pool curto o K=60 achata
# a diferença entre posições e o RRF degenera em "aparece nas duas listas?".
K_RRF_PADRAO = 10
PESO_DENSO_PADRAO = 1.0
PESO_LEXICAL_PADRAO = 0.3


def recuperar(
    consulta: str,
    pool: int = POOL_PADRAO,
    estrategia: str = ESTRATEGIA_PADRAO,
    *,
    k_rrf: int = K_RRF_PADRAO,
    peso_denso: float = PESO_DENSO_PADRAO,
    peso_lexical: float = PESO_LEXICAL_PADRAO,
    fusao: str = "rrf",
    norm: str = "minmax",
) -> tuple[list[tuple[Passagem, float]], dict[int, float], dict[int, float]]:
    """Passo 6 cru: devolve (ranking fundido, scores densos, scores lexicais) por `chunk_id`.

    Os dois dicionários voltam para que os TRÊS scores de `CitacaoRAG` possam ser preenchidos
    depois do rerank — guardá-los separados é o que permite mostrar o reranker mudando a ordem.
    """
    denso = buscar_denso_bruto(consulta, k=pool, estrategia=estrategia)
    lexical = (
        buscar_lexical_bruto(consulta, k=pool, estrategia=estrategia)
        if peso_lexical > 0
        else []
    )
    scores_denso = {p.chunk_id: s for p, s in denso}
    scores_lexical = {p.chunk_id: s for p, s in lexical}

    pesos = {"denso": peso_denso, "lexical": peso_lexical}
    listas = {"denso": denso, "lexical": lexical}
    fundido = (fundir_rrf(listas, pesos, k_rrf) if fusao == "rrf"
               else fundir_soma(listas, pesos, norm))
    return fundido, scores_denso, scores_lexical


def buscar_hibrido(
    consulta: str, k: int = 10, estrategia: str = ESTRATEGIA_PADRAO, **kwargs
) -> list[CitacaoRAG]:
    """Passo 6 completo. **Mesma assinatura de `buscar_denso`** — é o que deixa trocar de motor.

    Sem reranking: os `k` primeiros da ordem fundida, com `score_denso` e `score_lexical`
    preenchidos e `score_rerank` em `None` ("este motor não votou").
    """
    fundido, sd, sl = recuperar(consulta, estrategia=estrategia, **kwargs)
    return [
        para_citacao(p, denso=sd.get(p.chunk_id), lexical=sl.get(p.chunk_id))
        for p, _ in fundido[:k]
    ]


def buscar_com_rerank(
    consulta: str, k: int = 5, estrategia: str = ESTRATEGIA_PADRAO, **kwargs
) -> list[CitacaoRAG]:
    """Passos 6 + 7: recuperação híbrida seguida de reranking. É o caminho de produção.

    O RERANKER RECEBE A UNIÃO INTEIRA, não os `k` primeiros da fusão. A ordem que a fusão produz
    é descartada pelo passo 7 de qualquer jeito — o que ela decidiria, se truncássemos antes, é
    QUEM chega ao cross-encoder, e essa é uma decisão que a fusão mede pior que ele (D-037).
    Custo, contado e não estimado: uma união acima de `LOTE` (32) gasta duas chamadas de rerank,
    e isso acontece em **9 das 24** consultas do gabarito — ~37,5% mais chamadas que truncar.

    O QUE ESSE PREÇO COMPRA MUDOU COM A TROCA DE STACK DE 25/08 (D-046)
    - stack antiga (1B): comprava ZERO. União inteira e top-20 davam os seis números idênticos.
    - stack atual (`rerank-qa-mistral-4b`): compra **e@5 de 95% -> 100%**. Medido em 25/08 com
      `--truncar-pool` como braço de controle: truncando, os dois motores voltam a empatar em 95%.
      A diferença é UMA pergunta, a q17, cuja âncora (`Evaluator`) o braço denso não recupera de
      jeito nenhum — ela entra só pelo BM25 e o cross-encoder a promove a 4º. Ver D-037,
      Atualização 2, para o tamanho honesto disso: uma pergunta em 19, e só em e@5.

    `avaliar_rag.py --truncar-pool` é o braço de controle que mantém isso medível — foi ele que
    separou "ganho do pool maior" de "ganho da fusão".
    """
    # SEM PROVEDOR DE RERANK, O CAMINHO DE PRODUÇÃO É A HÍBRIDA (D-068).
    # Poderia cair em `reranquear` e receber 0,0 para todo mundo — a ordem sairia igual —, mas
    # aí `score_rerank` viria preenchido com um número que nenhum reranker produziu. `None` é a
    # convenção do projeto para "este motor não votou", e é diferente de "votou zero".
    # É isto que faz o repositório rodar para quem clona sem chave nenhuma, em vez de explodir:
    # a híbrida sozinha faz 95% r@1 e 100% r@3 (D-046).
    if RERANK.provedor == "nenhum":
        return buscar_hibrido(consulta, k=k, estrategia=estrategia, **kwargs)

    fundido, sd, sl = recuperar(consulta, estrategia=estrategia, **kwargs)
    if not fundido:
        return []
    return [
        para_citacao(p, denso=sd.get(p.chunk_id), lexical=sl.get(p.chunk_id), rerank=logit)
        for p, logit in reranquear(consulta, [p for p, _ in fundido], top_n=k)
    ]


def responder(
    consulta: str, k: int = 5, estrategia: str = ESTRATEGIA_PADRAO, **kwargs
) -> RespostaRAG:
    """Passos 6 + 7 + 8: híbrida -> rerank -> geração com citação e abstenção.

    É a porta de entrada do RAG para o resto do sistema. `k` é quantos trechos o gerador LÊ —
    não quantos ele cita. Citar menos do que leu é comportamento correto e esperado; é o que
    `indices_citados` registra.
    """
    citacoes = buscar_com_rerank(consulta, k=k, estrategia=estrategia, **kwargs)
    return gerar(consulta, citacoes)
