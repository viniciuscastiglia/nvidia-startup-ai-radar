"""NVIDIA RAG — consulta a base de conhecimento das tecnologias NVIDIA.

O STUB DA SESSÃO 01 SAIU DAQUI EM 24/08. Este nó agora chama o pipeline real: busca híbrida
(passo 6), reranking (passo 7) e citação com os três scores preenchidos.

A CONSULTA É MONTADA DO RÓTULO DA DOR + DAS EVIDÊNCIAS + DA STACK, E ISSO É DECISÃO (D-042, D-043)
----------------------------------------------------------------------------------------------------
`contexto/03` §4 diz que a dor é a chave de junção com a tabela de tecnologias, e o stub
implementava isso literalmente: um `dict` de oito dores para oito tecnologias. O problema do
dicionário não é ser simples — é que ele **não usa a base de conhecimento**. Com ele, as 16
páginas ingeridas, chunkadas e indexadas não mudariam uma vírgula da recomendação: o RAG inteiro
seria enfeite, e a recomendação continuaria sendo um mapeamento fixo escrito à mão.

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

from src.agents.justificativa import pontuar
from src.rag.pipeline import buscar_com_rerank
from src.state import CitacaoRAG, DorObservada, EstadoAnalise

# Quantos trechos por dor. Baixo de propósito: o Recommendation Agent recebe isto multiplicado
# pelo número de dores, e a regra 4 de `contexto/03` §4 é "não empilhar tecnologia" — recomendar
# 8 produtos para uma seed é ruído. Um funil largo aqui vira ruído lá.
# SUBIU DE 3 PARA 8 EM D-086, E O CUSTO É ZERO CHAMADA DE API: `reranquear` pontua a UNIÃO
# INTEIRA e só depois fatia por `top_n` (`src/rag/rerank.py`). O que 8 compra é candidato: com 3,
# quase nunca havia duas passagens da mesma página para escolher entre elas. Não muda quantas
# recomendações saem — `melhor_da_pagina` colapsa a lista por URL logo abaixo, como antes.
TRECHOS_POR_DOR = 8

# O QUE ESTÁ NA BASE DE CONHECIMENTO MAS NÃO É COISA PARA A STARTUP ADOTAR (D-082).
#
# O Inception é o PROGRAMA que o gerente está vendendo — o objetivo da conversa, não uma
# tecnologia que resolve uma dor. Sem esta lista ele saía como recomendação de verdade:
#
#     1. NVIDIA Inception · prioridade media · complexidade media · dores: custo
#        ação: "Agendar conversa técnica sobre NVIDIA Inception com o time de engenharia"
#
# ...enquanto o mesmo briefing já traz a seção `NVIDIA Inception: ELEGÍVEL` logo acima. E como
# a página é landing de marketing, os trechos que ela oferecia como `justificativa_tecnica` eram
# *Member Spotlight Stories* — cases de OUTRAS empresas. Medido em 02/09: a justificativa técnica
# para recomendar Inception à Doutor-AI e à Laura Networks era um case da Iguazio.
#
# POR QUE FILTRAR AQUI E NÃO TIRAR DO CORPUS: o corpus precisa dele. Quatro das 24 perguntas do
# gabarito dependem dessa página — q10 ("10 years", que é a regra de elegibilidade da M4), q11
# ("free program"), e as duas provas de ausência q21 e q24. Tirar a fonte consertaria o briefing
# e quebraria a régua. A distinção é de PAPEL: fonte de conhecimento, sim; produto a recomendar,
# não. Por isso a lista mora no nó que produz recomendação, não em `fontes.yaml`.
NAO_SAO_TECNOLOGIA = {"NVIDIA Inception"}


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

    # DEDUPLICAR POR URL PASSA A SER **ESCOLHER**, E NÃO "FICAR COM O PRIMEIRO" (D-086).
    # Todos os chunks de uma tecnologia compartilham a URL da página, então a deduplicação
    # decidia qual TEXTO representa aquela tecnologia — e decidia por posição do reranker, que
    # ordena por relevância à consulta, não por servir de justificativa. Medido em 02/09: para a
    # dor de observabilidade da Axenya, o vencedor era o chunk 81 do NeMo, quatro linhas de case
    # da Writer e do Arize, enquanto o chunk 58 da MESMA página diz o que o NeMo faz.
    #
    # A escolha acontece DENTRO da lista de uma dor, nunca entre dores: `dor_origem` é o que liga
    # a citação à evidência lá no `recommendation`, e trocar de dor aqui quebraria essa ligação
    # em silêncio. A POSIÇÃO do grupo também é preservada — quem decide qual tecnologia entra
    # continua sendo o reranker, que tem régua (D-068). Só o texto muda.
    # OS SCORES ACOMPANHAM O TEXTO ESCOLHIDO, e não o primeiro colocado do grupo. A tentação era
    # preservar os scores do melhor ranqueado para "explicar" a posição — e isso faria a citação
    # mentir sobre si mesma: `CitacaoRAG` existe para mostrar o reranker mudando a ordem, e um
    # score que descreve um chunk que ninguém vê não descreve nada. A POSIÇÃO do grupo já vem do
    # primeiro colocado, porque `dict` preserva a ordem de INSERÇÃO — substituir o valor não move
    # a chave. Ordem do reranker preservada, score honesto.
    def melhor_da_pagina(lista: list[CitacaoRAG]) -> list[CitacaoRAG]:
        grupos: dict[str, CitacaoRAG] = {}
        for c in lista:
            atual = grupos.get(c.url_fonte)
            if atual is None or pontuar(c.trecho) > pontuar(atual.trecho):
                grupos[c.url_fonte] = c
        return list(grupos.values())

    por_dor = [melhor_da_pagina(lista) for lista in por_dor]

    citacoes: list[CitacaoRAG] = []
    vistos: set[str] = set()
    for rodada in zip_longest(*por_dor):
        for citacao in rodada:
            # Deduplica por URL: duas dores diferentes recuperando a mesma página é comum e
            # esperado (custo e latência levam as duas ao NIM). Repetir a citação inflaria a
            # aparência de evidência sem acrescentar fonte nenhuma.
            if citacao is None or citacao.url_fonte in vistos:
                continue
            if citacao.tecnologia in NAO_SAO_TECNOLOGIA:
                continue
            vistos.add(citacao.url_fonte)
            citacoes.append(citacao)

    return {"citacoes_rag": citacoes}
