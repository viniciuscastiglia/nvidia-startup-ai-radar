"""Recommendation — cruza o perfil da startup com as tecnologias NVIDIA.

O TEXTO É DETERMINÍSTICO POR DECISÃO MEDIDA, NÃO POR TRABALHO INACABADO
------------------------------------------------------------------------
Este módulo se declarou "STUB DA SESSÃO 01 na geração do texto" até 06/09, e o rótulo ficou
falso quando os dois campos que ele gera passaram a ter régua:

  · `justificativa_tecnica` — D-086. O seletor de span bate a linha trivial (15/21 contra 12/21
    sobre 30 chunks rotulados ANTES do seletor existir), e num run real as justificativas que
    servem foram de 1/6 para 4/6. Ele continua sendo CITAÇÃO LITERAL da documentação, com
    `url_fonte`: não é prosa gerada, e segue conferível por quem lê.
  · `justificativa_negocio` — D-104. O defeito não era falta de texto, era ÍNDICE: `NEGOCIO`
    era chaveado só pela tecnologia enquanto a dor vivia em `citacao.dor_origem`. Corrigido,
    foi de 2 de 15 recomendações coerentes com a dor declarada para 15 de 15.

A opção de o LLM redigir (`plano.md` §5, alternativa (b)) continua ABERTA e registrada, e a
régua para decidi-la é a de D-084 — latência que o gerente sente ao clicar, e fornecedor único
no campo que ele lê primeiro. Não é "falta fazer": é uma escolha com o custo escrito.

AS QUATRO REGRAS DE QUALIDADE de `contexto/03` §4 estão implementadas, porque são regra de
negócio e não redação:

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

# OS CINCO TEXTOS CURADOS, cada um escrito para uma DOR e não para uma tecnologia — é o que o
# índice de `NEGOCIO` perdia. Ver D-104 e a tabela de `contexto/03` §4.
_NIM = ("Reduz o custo por token e tira a empresa da dependência de um fornecedor "
        "externo, com migração sem reescrever código — o que preserva o roadmap.")
_TENSORRT = ("Latência menor melhora a experiência do usuário final e permite atender "
             "mais requisições no mesmo orçamento de GPU.")
_TRITON = ("Melhor utilização de GPU baixa o COGS, que na contabilidade de "
           "AI-native services é o que separa margem de software de margem de serviço.")
_GUARDRAILS = ("Governança sobre o comportamento do agente é pré-requisito de venda "
               "para cliente corporativo e setor regulado.")
_NEMO = ("Sem processo de avaliação não há como provar melhoria de qualidade ao "
         "cliente — é o gap mais comum e mais invisível.")

# O ÍNDICE ERA O DEFEITO, NÃO O TEXTO — P-22, D-104.
# ------------------------------------------------------------------------------------------
# Estes cinco textos SEMPRE foram escritos para um par (tecnologia, dor): o do NIM fala de custo
# e de dependência de fornecedor; o do NeMo fala de avaliação. O dicionário, porém, era indexado
# só pela TECNOLOGIA, e a dor pela qual a citação entrou vive em `citacao.dor_origem`. O
# resultado chegava à tela do gerente assim, num run real de 05/09 com o rerank ligado:
#
#     NVIDIA NIM   dores: latencia   -> "Reduz o custo por token..."
#     NVIDIA NeMo  dores: custo      -> "Sem processo de avaliação..."
#
# A linha `dores:` e a justificativa de negócio, uma embaixo da outra, falando de coisas
# diferentes. É a família de D-100 nº 1 — texto que afirma o que não é o caso — no campo 3 dos 7
# obrigatórios do TAPI, e o vizinho do campo que D-086 consertou.
#
# A FONTE É `contexto/03` §4 — a tabela *dor observável -> tecnologia*, escrita em 22/08 a partir
# das fontes que o próprio TAPI lista, ANTES de qualquer medição deste projeto. Reatribuir cada
# texto ao seu par é leitura de documento, não calibração contra resultado.
NEGOCIO: dict[tuple[str, str], str] = {
    ("NVIDIA NIM", "custo"): _NIM,
    ("NVIDIA NIM", "dependencia_fornecedor"): _NIM,
    ("TensorRT-LLM", "latencia"): _TENSORRT,
    ("TensorRT-LLM", "escalabilidade"): _TENSORRT,
    ("Triton Inference Server", "custo"): _TRITON,
    ("Triton Inference Server", "escalabilidade"): _TRITON,
    ("NeMo Guardrails", "governanca"): _GUARDRAILS,
    ("NeMo Guardrails", "privacidade"): _GUARDRAILS,
    ("NVIDIA NeMo", "avaliacao"): _NEMO,
}

# O QUE MATA O FALLBACK FORMULAICO — 8 frases em vez de 16 x 8 células.
# ------------------------------------------------------------------------------------------
# `NEGOCIO` cobre 9 das 128 combinações possíveis. As outras caíam num fallback que o próprio
# comentário chamava de stub e adiava "para a M4" — fase que não existe em arquivo vivo nenhum
# (D-088). Curar as 11 tecnologias restantes POR TECNOLOGIA seria repetir o defeito de índice
# num denominador maior; o que o campo precisa dizer é o que RESOLVER AQUELA DOR compra para o
# negócio, e isso é propriedade da dor, não da tecnologia. Daí 8 frases.
#
# Cada uma NOMEIA a tecnologia recebida, e isso não é enfeite: sem o nome, duas tecnologias
# recomendadas pela mesma dor trariam justificativa byte a byte idêntica, e
# `test_justificativa_negocio_fala_da_tecnologia_recomendada` (D-063) voltaria a ser satisfeito
# por construção — a falha detectável que um fallback tornou indetectável.
#
# Cada frase diz o que a dor CUSTA ao negócio, sem afirmar nada sobre a startup específica:
# afirmação sobre a empresa exige `list[Evidencia]`, e é por isso que a frase "São gargalos que
# hoje limitam margem ou velocidade de entrega" saiu do fallback na revisão da sessão 03.
#
# O TAMANHO É RESTRIÇÃO MEDIDA, NÃO ESTILO: `briefing` corta em 150 com `…` (D-100), e o nome
# de tecnologia mais longo da base — `RAPIDS / CUDA-X Data Science`, 28 caracteres — entra na
# conta. A primeira redação destas oito frases estourava em SETE delas, e teriam chegado ao
# gerente cortadas: o defeito que D-100 acabou de tirar da tela, de volta por outra porta.
# `test_justificativa_negocio_cabe_no_briefing` é a rede.
NEGOCIO_POR_DOR: dict[str, str] = {
    "custo": ("{tecnologia} ataca o custo unitário da inferência, que é o que separa margem de "
              "software de margem de serviço."),
    "latencia": ("{tecnologia} reduz a latência de resposta: melhor experiência para o usuário "
                 "final e mais requisições por GPU."),
    "escalabilidade": ("{tecnologia} sustenta mais carga sem infraestrutura proporcional — evita "
                       "o custo subir na curva da receita."),
    "governanca": ("{tecnologia} dá controle auditável do comportamento do sistema, "
                   "pré-requisito de venda a cliente corporativo e regulado."),
    "privacidade": ("{tecnologia} mantém o dado sensível sob controle da empresa, que é o que "
                    "destrava cliente de setor regulado."),
    "avaliacao": ("{tecnologia} torna mensurável a qualidade entregue — sem avaliação não há "
                  "como provar melhoria ao cliente."),
    "observabilidade": ("{tecnologia} mostra quando o comportamento regride em produção, antes "
                        "de o cliente ser quem avisa."),
    "dependencia_fornecedor": ("{tecnologia} reduz a dependência de um fornecedor externo de "
                               "modelo — o risco de quem só empacota API de terceiro."),
}


def justificativa_negocio(citacao: CitacaoRAG, nome: str) -> str:
    """O campo 3 dos 7 obrigatórios, resolvido em três degraus (D-104).

    1. par curado `(tecnologia, dor)` — os cinco textos que sempre foram escritos para um par;
    2. frase por DOR, nomeando a tecnologia — cobre as 128 combinações com 8 frases curadas;
    3. `_negocio_de_fallback`, e só quando `dor_origem` é `None`.

    O DEGRAU 3 NÃO MORREU, E O MOTIVO É UM CAMINHO REAL: `dor_origem` é `None` quando a citação
    não veio de uma consulta por dor — o caminho da interface, onde quem pergunta é um humano
    (ver `CitacaoRAG.dor_origem`). Sem dor não há frase por dor, e o fallback é o que sobra.
    Ele deixa de atender 11 das 16 tecnologias e passa a atender um caso, que é o que ele
    sempre deveria ter sido.

    Função e não expressão inline porque é o que a torna testável sem montar um `EstadoAnalise`
    inteiro — `test_justificativa_negocio_fala_da_dor_declarada` chama daqui.
    """
    dor = citacao.dor_origem
    if dor is None:
        return _negocio_de_fallback(citacao, nome)
    if texto := NEGOCIO.get((citacao.tecnologia, dor)):
        return texto
    if modelo := NEGOCIO_POR_DOR.get(dor):
        return modelo.format(tecnologia=citacao.tecnologia)
    # Dor fora das oito de `state.Dor`: não deveria acontecer, e se acontecer o fallback diz a
    # verdade (nomeia a dor que entrou) em vez de esta função inventar uma frase.
    return _negocio_de_fallback(citacao, nome)


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
            justificativa_negocio=justificativa_negocio(citacao, perfil.nome),
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
