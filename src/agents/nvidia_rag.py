"""NVIDIA RAG — consulta a base de conhecimento das tecnologias NVIDIA.

O STUB DA SESSÃO 01 SAIU DAQUI EM 24/08. Este nó agora chama o pipeline real: busca híbrida
(passo 6), reranking (passo 7) e citação com os três scores preenchidos.

A CONSULTA É MONTADA DO RÓTULO DA DOR + DAS EVIDÊNCIAS + DA STACK, E ISSO É DECISÃO (D-042, D-043)
----------------------------------------------------------------------------------------------------
`contexto/03` §4 diz que a dor é a chave de junção com a tabela de tecnologias, e o stub
implementava isso literalmente: um `dict` de oito dores para oito tecnologias. O problema do
dicionário não é ser simples — é que ele **não usa a base de conhecimento**. Com ele, as 16
páginas ingeridas, chunkadas e indexadas não mudariam uma vírgula da recomendação, e o critério 2
do barema viraria decorativo.

**A primeira versão de D-042 trocou o dicionário por uma constante disfarçada, e a revisão da
sessão 03 mediu isso.** Ela usava `DorObservada.texto`, que o Extractor preenche com um template
fixo — `f"Sinal de dor em {dor} encontrado nos documentos"`. Consequência medida em 24/08 sobre
três startups reais: as três receberam **as mesmas seis tecnologias, na mesma ordem**, e o braço
lexical devolveu **zero** resultado nas oito consultas possíveis. Era o `BASE_PROVISORIA` de volta,
pagando embedding e rerank por dor.

A consulta agora tem três partes, e cada uma está aqui por um motivo diferente:

1. **O rótulo da dor** (`custo`, `latencia`) — a âncora tópica. É o único sinal que existia dentro
   do template; o resto daquela frase (`"Sinal de dor em … encontrado nos documentos"`) são
   palavras de alta frequência que só diluem o vetor da consulta.
2. **Os trechos de `dor.evidencias`** — a frase LITERAL do documento da startup, que é o que
   `Evidencia.trecho` guarda desde D-018. É aqui que a startup descreve o próprio problema com as
   palavras dela, e é o que faz duas startups com a mesma dor recuperarem coisas diferentes.
3. **A stack declarada**, quando existir.

E É AQUI QUE O BRAÇO LEXICAL PASSA A TER O QUE FAZER
------------------------------------------------------
D-037 mediu que o BM25 é mudo em consulta conceitual em português e forte em nome literal de
produto — `colang`, `vllm`, `pytorch`, `scikit`. O rótulo da dor não tem nome literal nenhum; os
trechos de evidência têm, porque o gatilho `dependencia_fornecedor` casa exatamente em `"gpt-4"`,
`"api da openai"`, `"chatgpt"`. **A hipótese de D-037 continua não medida numa régua**, mas deixou
de ser inverificável: antes o braço lexical não votava, agora ele vota.

**Ressalva honesta:** `perfil.stack_declarada` NÃO é preenchida por nenhum produtor hoje —
`extractor.node` monta o `PerfilStartup` sem ela. O parâmetro fica porque o custo é zero e o
contrato é o certo, mas a parte (3) é inalcançável até o Extractor da M4. Quem ler este arquivo
precisa saber disso; era o que faltava na primeira versão.

O QUE ESTE NÓ NÃO FAZ: GERAR TEXTO
-----------------------------------
`pipeline.responder()` existe e faz o passo 8, mas quem consome este nó é o Recommendation Agent,
que precisa dos TRECHOS com scores para cruzar com o perfil — não de um parágrafo já redigido.
Redigir aqui e reinterpretar lá seria perder a evidência no meio do caminho. A geração com
citação é para quando um humano faz a pergunta; ela entra pela interface, não por este nó.
"""

from __future__ import annotations

from itertools import zip_longest

from src.rag.pipeline import buscar_com_rerank
from src.state import CitacaoRAG, DorObservada, EstadoAnalise

# Quantos trechos por dor. Baixo de propósito: o Recommendation Agent recebe isto multiplicado
# pelo número de dores, e a regra 4 de `contexto/03` §4 é "não empilhar tecnologia" — recomendar
# 8 produtos para uma seed é ruído. Um funil largo aqui vira ruído lá.
TRECHOS_POR_DOR = 3


def consulta_da_dor(dor: DorObservada, stack: list[str]) -> str:
    """Rótulo da dor + a linguagem literal da startup + a stack. Ver o docstring do módulo."""
    partes = [dor.dor.replace("_", " ")]
    partes += [e.trecho for e in dor.evidencias]
    if stack:
        partes.append(f"stack atual: {', '.join(stack)}")
    return " ".join(p.strip() for p in partes if p and p.strip())


def node(state: EstadoAnalise) -> dict:
    perfil = state.get("perfil")
    if perfil is None:
        return {"citacoes_rag": []}

    stack = [a.texto for a in perfil.stack_declarada]

    # UMA LISTA POR DOR, E A INTERCALAÇÃO DEPOIS — não uma lista concatenada.
    # O Recommendation Agent corta esta lista em `TETO_RECOMENDACOES = 3` (regra 4 de
    # `contexto/03` §4). Se ela chegar lá concatenada dor a dor, o corte é POR DOR: as três
    # recomendações saem todas da primeira dor e as outras somem em silêncio. Intercalando,
    # o corte pega o 1º colocado das três primeiras dores — que é o que "não empilhar
    # tecnologia" quer dizer. Medido em 24/08: sem isto, três startups distintas recebiam
    # `[Inception, Morpheus, CUDA Toolkit]` idênticos.
    por_dor: list[list[CitacaoRAG]] = []
    for dor in perfil.dores_observadas:
        consulta = consulta_da_dor(dor, stack)
        # Consulta vazia não vai para o embedder: ele responde HTTP 400 e derruba o nó. Uma dor
        # sem rótulo e sem evidência não deveria existir, mas o custo da guarda é uma linha.
        if not consulta:
            continue
        # `dor_origem` é carimbado aqui e não dentro do RAG: `src/rag/` não conhece "dor".
        por_dor.append([
            c.model_copy(update={"dor_origem": dor.dor})
            for c in buscar_com_rerank(consulta, k=TRECHOS_POR_DOR)
        ])

    citacoes: list[CitacaoRAG] = []
    vistos: set[str] = set()
    for rodada in zip_longest(*por_dor):
        for citacao in rodada:
            # Deduplica por URL: duas dores diferentes recuperando a mesma página é comum e
            # esperado (custo e latência levam as duas ao NIM). Repetir a citação inflaria a
            # aparência de evidência sem acrescentar fonte nenhuma.
            if citacao is None or citacao.url_fonte in vistos:
                continue
            vistos.add(citacao.url_fonte)
            citacoes.append(citacao)

    return {"citacoes_rag": citacoes}
