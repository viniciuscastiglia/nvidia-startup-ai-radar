"""Recommendation — cruza o perfil da startup com as tecnologias NVIDIA.

STUB DA SESSÃO 01 na geração do texto, mas as QUATRO REGRAS DE QUALIDADE de `contexto/03` §4
já estão implementadas, porque são regra de negócio e não redação:

1. Prioridade vem do GAP entre os dois eixos, não do rótulo    -> `_prioridade()`
2. Complexidade tem que ser honesta                            -> `COMPLEXIDADE` por tecnologia
3. Recomendação sem evidência não sai                          -> filtro por confiança (D-010)
4. Não empilhar tecnologia                                     -> `TETO_RECOMENDACOES`

A regra 3 é onde a decisão D-010 se paga: o Evidence Validator anotou e rebaixou, mas quem
BARRA é aqui. Recomendação de prioridade alta apoiada só em afirmação de confiança baixa não sai.

DÍVIDA DE D-020 PAGA EM 27/08 (D-063)
--------------------------------------
O filtro de dores tinha uma condição inócua: `any(c.tecnologia == citacao.tecnologia for c in
citacoes)` é SEMPRE verdadeira, porque `citacao` está em `citacoes`. Na prática
`dores_enderecadas` listava TODAS as dores validadas em toda recomendação — as 7 da Axenya
apareciam igualzinhas sob cada tecnologia, impressas no briefing.

A correção não era a linha óbvia. Trocar a condição por `d.dor == citacao.dor_origem` de uma vez
faria `evidencias`, derivada da MESMA lista, estreitar junto — e recomendação cuja dor de origem
não passou pelo Evidence Validator cairia no `if not evidencias: continue` e sumiria, mudando o que
`test_toda_recomendacao_tem_evidencia` mede.

O que entrou foi a separação que o próprio comentário apontava como a reescrita: **"de quais dores
tiro EVIDÊNCIA" e "quais dores DECLARO endereçadas" viraram duas listas.** O lastro continua vindo
de todas as dores validadas, então nenhuma recomendação some; a declaração passa a ser só a dor que
puxou aquela citação, que é o que `dor_origem` sabe desde D-043.
"""

from __future__ import annotations

from src.agents.justificativa import melhor_trecho
from src.state import (
    CitacaoRAG,
    Complexidade,
    EstadoAnalise,
    Prioridade,
    Recomendacao,
)

TETO_RECOMENDACOES = 3   # regra 4: recomendar 8 produtos para uma seed é ruído

# Regra 2: honestidade sobre o custo de adoção. `cudf.pandas` é zero-code-change;
# migrar para Triton com TensorRT-LLM é projeto de semanas. Tratar como iguais denuncia
# motor raso.
COMPLEXIDADE: dict[str, Complexidade] = {
    "NVIDIA NIM": "baixa",              # trocar base_url
    "NeMo Guardrails": "media",
    "NVIDIA NeMo": "media",
    "Triton Inference Server": "alta",
    "TensorRT-LLM": "alta",
}

# Texto curado para as 5 tecnologias que o stub da sessão 01 conhecia. NÃO cobre as 16 da base —
# e depois que `nvidia_rag` passou a consultar o RAG de verdade (24/08), chegam aqui tecnologias
# fora desta tabela. O fallback abaixo é derivado das DORES observadas, que o nó já tem em mãos:
# formulaico e visivelmente de stub, mas nunca vazio — `justificativa_negocio` é um dos 7 campos
# obrigatórios do TAPI, e um briefing que chega ao usuário com esse campo vazio não é "quase lá":
# é uma recomendação que ele não consegue levar para dentro da conversa com a startup.
# Escrever as outras 11 à mão seria curadoria; na M4 este texto sai do LLM com o perfil na frente.
NEGOCIO = {
    "NVIDIA NIM": ("Reduz o custo por token e tira a empresa da dependência de um fornecedor "
                   "externo, com migração sem reescrever código — o que preserva o roadmap."),
    "TensorRT-LLM": ("Latência menor melhora a experiência do usuário final e permite atender "
                     "mais requisições no mesmo orçamento de GPU."),
    "Triton Inference Server": ("Melhor utilização de GPU baixa o COGS, que na contabilidade de "
                                "AI-native services é o que separa margem de software de margem "
                                "de serviço."),
    "NeMo Guardrails": ("Governança sobre o comportamento do agente é pré-requisito de venda "
                        "para cliente corporativo e setor regulado."),
    "NVIDIA NeMo": ("Sem processo de avaliação não há como provar melhoria de qualidade ao "
                    "cliente — é o gap mais comum e mais invisível."),
}


def _prioridade(
    quadrante: str,
    confianca: str,
    sinal_verificado: bool = True,
) -> Prioridade:
    """Regra 1: a prioridade sai do GAP entre maturidade AI-native e maturidade de stack.

    Regra 3 aplicada junto: confiança baixa nunca vira prioridade alta. A evidência não
    sustenta a urgência, então afirmar urgência seria inventar.

    `sinal_verificado=False` (D-101) É A MESMA REGRA 3, NUM EIXO NOVO: o rótulo veio do silêncio
    da extração, não de constatação, e afirmar urgência sobre classificação não constatada é o
    mesmo erro que afirmar urgência sobre evidência fraca.

    O REBAIXAMENTO POR NÃO-ELEGIBILIDADE ENTROU EM 04/09 E SAIU NO MESMO DIA (D-103). No papel
    fazia sentido — "a recusada não disputa a fila". Medido, fazia outra coisa: **15 das 30 caíam
    para `baixa`, e a JetBov empatava com a SunnyHUB.** A JetBov é o único `sweet-spot` da base;
    a SunnyHUB é energia solar. Achatar as duas no piso destrói exatamente o que a regra 1 existe
    para produzir — *"a prioridade sai do GAP, não do rótulo"*. E a informação não se perde: o
    banner `!! FORA DO INCEPTION` já grita a recusa. Codificá-la duas vezes custava o único eixo
    que o campo ainda discriminava.

    CONTEXTO QUE FALTAVA: antes de 04/09 o campo era **`media` para as 30** — constante,
    informação zero, porque `confianca` é `baixa` em todo mundo (o defeito 0/6) e isso já
    rebaixava todo `alta`. Com só o eixo de verificação ele vai a 21 `media` e 9 `baixa`. Ele só
    volta a medir o GAP quando `confianca` sair do 0/6 — P-11, que depende de `coletar.py`
    capturar data (P-25).
    """
    base: Prioridade = {
        "sweet-spot": "alta",            # AI-native com stack imatura: dor real e iminente
        "prospect-de-evolucao": "media",  # a conversa é sair do wrapper primeiro
        "ja-otimizada": "baixa",          # provavelmente já usa NVIDIA ou já é membro
        "fora-do-funil": "baixa",
    }.get(quadrante, "baixa")
    if not sinal_verificado:
        return "baixa"
    if confianca == "baixa" and base == "alta":
        return "media"
    return base


def _negocio_de_fallback(citacao: CitacaoRAG, nome: str) -> str:
    """Usado quando `NEGOCIO` não tem texto curado para a tecnologia. Ver a dívida abaixo.

    DUAS CORREÇÕES DA REVISÃO DA SESSÃO 03, §4, E AS DUAS SÃO SOBRE HONESTIDADE DO CAMPO:

    1. **O texto NOMEIA a tecnologia.** A primeira versão não nomeava, então recomendar Morpheus,
       CUDA Toolkit ou Riva para a mesma startup produzia `justificativa_negocio` byte a byte
       idêntica — e `assert getattr(rec, campo)` do teste dos 7 campos, que só vê verdade
       booleana, era satisfeito por construção. Uma falha detectável tinha virado indetectável.
       `test_justificativa_negocio_fala_da_tecnologia_recomendada` é a rede nova.
    2. **A frase "São gargalos que hoje limitam margem ou velocidade de entrega" SAIU.** Ela
       afirmava um fato de negócio sem nenhuma fonte, contra a convenção do repositório de que
       nada é afirmado sem `list[Evidencia]`.

    O que sobra é verificável: a dor por onde a tecnologia entrou (`dor_origem`, carimbado por
    `nvidia_rag` na consulta que a recuperou) e o fato de a ligação vir da base de conhecimento.
    Continua sendo texto de stub, e visivelmente — na M4 ele sai do LLM com o perfil na frente.
    """
    origem = (
        f"pela dor de {citacao.dor_origem.replace('_', ' ')} observada na comunicação pública "
        f"da {nome}"
        if citacao.dor_origem
        else f"pelas dores observadas na comunicação pública da {nome}"
    )
    return (
        f"{citacao.tecnologia} entrou {origem}, e a ligação entre as duas coisas é a passagem "
        f"citada da documentação da tecnologia, não uma inferência deste sistema."
    )


def node(state: EstadoAnalise) -> dict:
    perfil, diagnostico = state.get("perfil"), state.get("diagnostico")
    citacoes = state.get("citacoes_rag") or []
    if perfil is None or diagnostico is None:
        return {"recomendacoes": [],
                "motivo_sem_recomendacao": "análise incompleta: sem perfil ou sem diagnóstico"}

    # A CAUSA DE "ZERO RECOMENDAÇÕES" VIAJA NO ESTADO — D-100.
    # O briefing imprimia a frase fixa "sem evidência validada que sustente uma recomendação"
    # para TODA lista vazia. Medido em 04/09: Conta Simples, Core AI e Iniciador têm 3, 5 e 7
    # dores VALIDADAS e recebiam essa frase; a causa real era o corte de funil daqui. Um
    # relatório que afirma a causa errada é pior que um que não afirma nenhuma, porque o
    # gerente age sobre ela — e o rodapé da página promete o contrário.
    #
    # O TESTE É O QUADRANTE, NÃO A CLASSE (D-101): `derivar_quadrante` é o único lugar que
    # decide quem está fora do funil, e perguntar `classe == "non-AI"` aqui duplicaria a decisão.
    #
    # E ESTE RAMO É INALCANÇÁVEL VINDO DO GRAFO — D-103, provado por força bruta sobre o espaço
    # de detectores. `fora-do-funil` exige `non-AI` CONSTATADO, e o classificador não tem
    # detector positivo de `non-AI`: o único caminho para o rótulo é ausência de sinal. Fica
    # porque é a regra da rubrica e `node()` é invocável com um `Diagnostico` montado à mão — e
    # fica DECLARADO, porque guard morto que ninguém sabe que está morto é a mesma armadilha em
    # que `varrer_classes.py` caiu ao imprimir "D-101 verificado".
    if diagnostico.quadrante == "fora-do-funil":
        return {"recomendacoes": [],
                "motivo_sem_recomendacao": (
                    f"empresa classificada `{diagnostico.classe}` com sinal verificado — "
                    f"fora do funil por `contexto/02` §4, não por falta de evidência")}

    # D-099: a recusa do Inception NÃO suprime a recomendação. A NVIDIA vende fora do programa,
    # e a JetBov — única `AI-native` e único `sweet-spot` da base — é recusada por idade;
    # suprimir apagaria da tela o melhor prospect que o sistema encontrou.
    #
    # QUEM ROTULA É O BRIEFING, LENDO `a.elegibilidade` (D-103). A primeira versão carimbava o
    # motivo num campo novo de `Recomendacao` — estado 100% derivável, copiado em até 3 objetos
    # por empresa, para um leitor que já tinha a fonte em mãos. `Recomendacao` modela UMA
    # tecnologia recomendada; a elegibilidade é fato da EMPRESA.
    recomendacoes: list[Recomendacao] = []
    for citacao in citacoes[:TETO_RECOMENDACOES]:
        # Regra 3: só as dores cuja afirmação passou pelo validator entram.
        validadas = [d for d in perfil.dores_observadas if d.validada]
        # DE ONDE SAI EVIDÊNCIA e QUAIS DORES SÃO DECLARADAS ENDEREÇADAS são duas perguntas
        # diferentes, e até 27/08 eram a mesma lista (D-063). A condição antiga —
        # `any(c.tecnologia == citacao.tecnologia for c in citacoes)` — era SEMPRE VERDADEIRA,
        # porque `citacao` pertence a `citacoes`: `dores_enderecadas` listava as 7 dores validadas
        # em TODA recomendação, e isso estava impresso no briefing.
        #
        # A correção de uma linha (`d.dor == citacao.dor_origem`) não podia entrar sozinha porque
        # `evidencias` derivava da MESMA lista: estreitá-la faria recomendações caírem no
        # `if not evidencias: continue` e sumirem, mudando o que
        # `test_toda_recomendacao_tem_evidencia` mede. Separando os dois usos, o lastro continua
        # largo — nenhuma recomendação some — e a declaração fica honesta.
        # `dor_origem` é carimbado por `nvidia_rag` na consulta que recuperou esta citação.
        dores = [d for d in validadas if d.dor == citacao.dor_origem]
        # O LASTRO SEGUE A DECLARAÇÃO — e a primeira versão de D-063 errou exatamente aqui.
        # Estreitar `dores_enderecadas` para a dor de origem e deixar `evidencias` saindo de TODAS
        # as dores validadas produzia recomendação que DECLARA `observabilidade` e CITA trechos
        # sobre custo, sob o rodapé "toda conclusão acima aponta para o documento que a sustenta".
        # Antes de D-063 as duas listas concordavam por construção; a correção tornou a divergência
        # possível e nada a impedia. Achado nº 1 do code review de 27/08.
        #
        # `dores or validadas` preserva o que D-063 comprou: sem `dor_origem` (o caminho da
        # interface) o lastro volta a ser o conjunto validado e NENHUMA recomendação some. E dor
        # validada SEMPRE tem evidência — `avaliar()` devolve `validada=False` quando não há —,
        # então `dores` não-vazia implica `evidencias` não-vazia.
        lastro = dores or validadas
        evidencias = [e for d in lastro for e in d.evidencias][:3]
        if not evidencias:
            continue

        recomendacoes.append(Recomendacao(
            tecnologias=[citacao.tecnologia],
            # NÃO É MAIS O CHUNK CRU (D-086). `citacao.trecho` é o chunk INTEIRO — mediana de
            # 803 caracteres —, e o briefing imprime os 150 primeiros: o que o gerente lia era o
            # COMEÇO do chunk, que neste corpus é quase sempre um título. `melhor_trecho` escolhe
            # o span de maior densidade técnica dentro dele. Continua sendo citação literal da
            # documentação, com `url_fonte` — não é prosa gerada, e segue verificável.
            justificativa_tecnica=melhor_trecho(citacao.trecho),
            justificativa_negocio=NEGOCIO.get(citacao.tecnologia) or _negocio_de_fallback(
                citacao, perfil.nome
            ),
            prioridade=_prioridade(
                diagnostico.quadrante,
                diagnostico.confianca,
                sinal_verificado=diagnostico.sinal_verificado,
            ),
            complexidade=COMPLEXIDADE.get(citacao.tecnologia, "media"),
            # Sem `dor_origem` a lista fica vazia — o caminho da interface, onde quem pergunta é
            # um humano e não uma dor. A frase precisa de outro fecho em vez de terminar em ": .".
            proxima_acao=(
                f"Agendar conversa técnica sobre {citacao.tecnologia} com o time de engenharia "
                f"da {perfil.nome}, partindo das dores observadas: "
                f"{', '.join(sorted({d.dor for d in dores}))}."
                if dores else
                f"Agendar conversa técnica sobre {citacao.tecnologia} com o time de engenharia "
                f"da {perfil.nome}."
            ),
            evidencias=evidencias,
            citacoes_rag=[citacao],
            dores_enderecadas=sorted({d.dor for d in dores}),
        ))
    # As duas causas restantes, e elas são DIFERENTES: não houve o que recuperar na base NVIDIA,
    # ou houve e nenhuma citação tinha dor validada por trás. A segunda é a frase que o briefing
    # imprimia para todo mundo; agora ela sai só quando é verdade.
    motivo = None
    if not recomendacoes:
        motivo = ("nenhuma citação recuperada da base NVIDIA para as dores desta empresa"
                  if not citacoes else
                  "sem evidência validada que sustente uma recomendação")
    return {"recomendacoes": recomendacoes, "motivo_sem_recomendacao": motivo}
