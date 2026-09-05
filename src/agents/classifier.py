"""Startup Classifier — AI-native | AI-enabled | non-AI, mais o eixo de maturidade de stack.

POR QUE DOIS EIXOS (contexto/02 §4): classificar AI-native não é a mesma coisa que qualificar
como prospect. Uma AI-native com stack madura provavelmente já é membro do Inception; uma
AI-native com stack imatura é o melhor prospect que existe. O rótulo do TAPI continua sendo
emitido — a priorização vem do gap.

A ARITMÉTICA DE PONTOS SAIU, E O MOTIVO ESTÁ MEDIDO (D-060)
------------------------------------------------------------
Até 27/08 o eixo 1 era `pontos = 2·autopilot + 2·dado_proprietário + 1·técnica`, com `>= 4` para
`AI-native`. Três problemas, e o terceiro é o que a régua tornou visível:

  1. **Os pesos 2/2/1 não vinham da rubrica.** `contexto/02` §4 lista os sinais de AI-native como
     um conjunto, sem hierarquia. A aritmética foi inventada no stub da sessão 01 e nunca decidida.
  2. **Profundidade técnica sozinha valia 1 e nunca alcançava 4.** Na prática o limiar exigia
     autopilot E dado proprietário. Por isso a Maritaca — quantização QAT, MoE, prefill/decode,
     MFU em B200 — saía `AI-enabled`.
  3. **Os 4 erros de `classe` na régua apontavam todos para o mesmo lado**: Axenya, Doutor-AI,
     Laura Networks e Maritaca são `AI-native` no gabarito e saíam `AI-enabled`. Nenhum erro no
     sentido contrário. Isso é limiar alto demais, não classificador ruim.

O QUE ENTROU: TRÊS DEGRAUS DECLARADOS, SEM ARITMÉTICA

    1. nenhum sinal de IA no caminho crítico                      -> non-AI
    2. a empresa OPERA a própria IA — basta UM dos dois:
       a. profundidade técnica própria (>= 3 marcadores distintos
          de PROFUNDOS, sobre os DOCUMENTOS INTEIROS)
       b. autopilot + dado proprietário                           -> AI-native
    3. resto                                                      -> AI-enabled

`2b` é EXATAMENTE o que a aritmética já deixava passar (2+2=4), então nada que era `AI-native`
deixa de ser: a mudança é aditiva do lado `AI-native` e o raio de regressão fica limitado às três
fixtures que o casador acertava (Deal, RD Station, SunnyHUB).

**O DEGRAU 1 NÃO mantém a semântica de `pontos == 0`, e a primeira redação disto era falsa.** Ele
pergunta *"há ALGUM sinal de IA?"* e inclui `n_profundos >= 1`, enquanto o degrau `2a` exige `>= 3`.
Consequência nomeada pelo achado nº 2 do code review de 27/08: uma startup com 1 ou 2 marcadores de
infraestrutura e nenhum outro sinal era `non-AI` e passa a `AI-enabled` — o que a tira de
`fora-do-funil` e faz o `nvidia_rag` gastar API por dor. Nenhuma das 8 fixtures cai nesse caso, e é
por o placar NÃO medir isso que precisa estar escrito. A largura é deliberada (um marcador de
infraestrutura é sinal de IA no produto), mas o raio de regressão da frase acima não a cobria.

O `>= 3` de `2a` NÃO é parâmetro novo: é o número que o eixo 2 já declara para `maturidade alta`,
logo abaixo. "Profundidade técnica própria" passa a significar operacionalmente o que este mesmo
arquivo já chamava de stack madura — zero grau de liberdade introduzido, e portanto nada para
calibrar contra o gabarito de 8 fixtures.

O argumento de `2a` é a pergunta norteadora do case: uma empresa que quantiza o próprio modelo não
é wrapper de LLM, por definição.

A DETECÇÃO FALHA DEIXA DE VIRAR AFIRMAÇÃO — 04/09 (D-101)
----------------------------------------------------------
A rubrica define `non-AI` por uma propriedade POSITIVA (`contexto/02` §4): *"o produto não
depende de IA... sem IA no caminho crítico da entrega de valor"*. Isso é constatação sobre a
empresa, e constatação exige evidência. Este módulo emitia esse rótulo quando `pontos == 0` —
ou seja, quando **não encontrou sinal**. A rubrica pede *"constatamos que não há IA"*; o código
entregava *"não achei sinal de IA"*.

**E o repositório já tinha decidido o contrário, no dia 2.** A regra 4 do Evidence Validator diz
*"ausência de sinal != sinal negativo → nada é DELETADO, só rebaixado"*, e `Elegibilidade` a
aplica há semanas: `motivos_exclusao` (a base PROVA que é consultoria) versus
`requisitos_nao_verificados` (a base NÃO PROVA que tem developer), e só o primeiro exclui.
`classe` não tinha esse par.

MEDIDO NA BASE DE 30, em 04/09 (`scripts/varrer_classes.py`): `AI-native` 1 · `AI-enabled` 20 ·
`non-AI` **9** — e as nove com ZERO detector, todas com **2 a 7 dores de IA** extraídas com
evidência pelo mesmo Extractor. Elas iam para `fora-do-funil` e recebiam zero recomendação. Na
tela, a linha `Base` chegava a dizer *"posicionamento de copilot: vende a ferramenta"* — uma
constatação sobre o modelo de entrega — logo abaixo de `Classificação: non-AI`.

O QUE ENTROU: `sinal_verificado`, e o RÓTULO NÃO MUDA.
`non-AI` continua sendo emitido — o TAPI nomeia três classes, e uma quarta no output seria
desvio de especificação. O que muda é a CONSEQUÊNCIA: `derivar_quadrante` só manda para
`fora-do-funil` quem foi constatado, e o briefing imprime `? sinal de IA não verificado` no
mesmo idioma que a elegibilidade já usa.

ALTERNATIVA DESCARTADA — `indeterminado` como quarta classe. É semanticamente mais limpa e
custa duas coisas. A medida (`varrer_classes.py --custo-desenhos`): `classe` cai de **3/7 para
2/7**, porque a SunnyHUB também tem zero detector e passaria a divergir de um gabarito que diz
`non-AI`. A não medida, e maior: o desvio das três classes do TAPI. O desenho que entrou custa
`3/7 → 3/7` — medido, não suposto.

POR QUE ISTO NÃO É CALIBRAR CONTRA O GABARITO, que é o que D-062 existe para impedir e a razão
pela qual a P-24 estava ACEITA: **nenhum grau de liberdade novo foi introduzido.** É a mesma
regra `pontos == 0`, com outro destino. Não há limiar, peso nem lista de termos para ajustar —
e por isso a régua não se move, o que era previsível antes de rodar.

O PREÇO, DECLARADO: as nove entram no funil, e uma delas — a SunnyHUB, energia solar — é
`non-AI` de verdade. É o mesmo preço que `Elegibilidade` já paga e reporta na Solinftec, que
sai ELEGÍVEL com *"requisito não verificado"* porque o documento diz "há 18 anos" e não um ano.
Troca um falso negativo SILENCIOSO por um falso positivo ANOTADO — a direção que D-052 e D-057
já escolheram por escrito.

POR QUE O EIXO 1 TEM CONTADOR PRÓPRIO, E O EIXO 2 NÃO MUDOU UMA VÍRGULA
------------------------------------------------------------------------
`extractor.frases` recorta uma frase POR DOCUMENTO (o `break` em `_casar`), então
`sinais_otimizacao_tecnica` guarda no máximo 3 frases — e o eixo 2 conta os marcadores só dentro
delas. O post inteiro da Maritaca chega assim como UMA frase.

Os dois eixos fazem perguntas diferentes, e por isso merecem corpus diferentes:

  · **"quão madura é a stack"** é um JUÍZO DE GRAU, e ele se apoia em evidência que o sistema vai
    CITAR. Capar em 3 trechos citáveis é defensável, e o eixo 2 continua exatamente como estava —
    6/7 na régua, e serve de CONTROLE: se ele se mover, esta mudança vazou para onde não devia.
  · **"a empresa opera a própria IA"** é pergunta de EXISTÊNCIA. O corpus certo é tudo que os
    documentos dizem, e uma frase por documento subconta por construção.

ALTERNATIVA DESCARTADA, e ela é o motivo de o contador morar AQUI e não no Extractor: alargar
`sinais_otimizacao_tecnica` faria o filtro do Inception ver mais texto — `briefing.elegibilidade`
varre `perfil.afirmacoes`, não `diagnostico.evidencias`. Mais evidência técnica viraria mais
superfície para exclusão espúria, acoplando esta mudança ao defeito de exclusão por menção que
D-052 nomeou. Com contador próprio, `perfil.afirmacoes` não muda e os dois problemas ficam
independentes.

LIMITAÇÃO CONHECIDA DO CONTADOR (achado nº 4 do code review de 27/08): `profundidade_tecnica` lê
os documentos CRUS e não passa pelo juiz de D-053. Com `--juiz` ligado, evidência que o juiz
REPROVOU — sujeito errado, termo dentro de outra palavra — volta pela porta do eixo 1 e pode levar
a `AI-native`, com `ev_profundos` entrando em `diagnostico.evidencias` sem auditoria. É contradição
real com *"ele gera, e o modelo julga"*, e não foi paga porque a rubrica está REPROVADA e
desligada. Se algum dia for promovida, o candidato tem que passar pelo juiz antes.

OUTRA DESCARTADA: LLM com structured output neste nó. O motivo é medido, não estético — D-056
mostrou o `llama-3.1-8b` RECITANDO a rubrica quando ela é enumerada no prompt (22% de precisão, a
regra nº 2 devolvida como justificativa). A rubrica de classe tem mais categorias e mais modos de
falha que o julgamento de dor, então é o pior caso conhecido para este modelo; e a variação entre
execuções (50–62% em 3 runs) é veneno numa demo ao vivo.
"""

from __future__ import annotations

from src.agents.extractor import frases
from src.state import (
    ClasseStartup,
    Diagnostico,
    DocumentoRef,
    Evidencia,
    EstadoAnalise,
    MaturidadeStack,
    derivar_quadrante,
)

# Só profundidade de INFRAESTRUTURA — self-hosting, quantização, serving, avaliação.
# Dizer "usamos machine learning" não é maturidade de stack; é uso de IA, que é o eixo 1.
PROFUNDOS = ["cuda", "gpu", "tensorrt", "triton", "vllm", "quantiz", "self-hosted",
             "on-premise", "inferência", "latência", "throughput", "mlops", "observabilidade"]

# A HIPÓTESE 2 DE D-060, SOB PROTOCOLO ANTI-CONTAMINAÇÃO — D-106.
#
# D-060 deixou duas hipóteses para o teto de `classe`. A 1 (os documentos não têm o sinal) foi
# REFUTADA em 03/09 (D-095). A 2 é esta: a lista acima não cobre como uma empresa que não é de
# infraestrutura descreve a própria stack. Oito dos 13 termos são nome de produto NVIDIA ou
# vocabulário de serving — ela mede quem fala como fornecedor de infra.
#
# A LISTA FOI DERIVADA E COMMITADA ANTES DE QUALQUER MEDIÇÃO, de dois documentos escritos em
# 22/08: `contexto/02` §4 linha 148 e a coluna de justificativa técnica de `contexto/03` §4.
# A origem de cada termo está em `data/avaliacao/profundos-candidato.yaml`, e
# `test_profundos_candidato_bate_com_o_yaml` impede as duas de divergirem. É o que separa isto
# da tentativa de 04/09, escrita conhecendo o gabarito — o erro que D-091 já custou uma sessão.
#
# O ACHADO ESTAVA NA DERIVAÇÃO, ANTES DO NÚMERO: a rubrica nomeia CINCO formas de otimização
# técnica própria — "self-hosting, quantização, avaliação, guardrails, MLOps real" — e produção
# cobre TRÊS. `avaliação` e `guardrails` nunca tiveram marcador, e são justamente as duas que
# não exigem falar de GPU.
PROFUNDOS_CANDIDATO = [
    # os cinco que a rubrica nomeia (contexto/02 §4:148)
    "self-host", "quantiz", "avaliaç", "guardrail", "mlops",
    # os de produção que sobrevivem
    "cuda", "gpu", "tensorrt", "triton", "vllm", "inferência", "latência", "throughput",
    "on-premise", "observabilidade",
    # a coluna de justificativa técnica de contexto/03 §4
    "fine-tun", "benchmark", "batching", "kv cache", "fp8", "fp4", "int4", "decoding",
    "kernel", "profiling", "embedding", "rerank", "sim-to-real", "dado sintétic",
]

# O DEFAULT É `False`, e a promoção é um segundo ato (D-078). `avaliar_agentes.py --profundos`
# liga. Ver o critério fixado em D-106, antes de medir.
USAR_PROFUNDOS_CANDIDATO = False


def marcadores() -> list[str]:
    """A lista que os DOIS eixos leem — e ser uma só é o que D-060 protege.

    D-060 deixou `profundidade_tecnica()` compartilhado justamente para que mexer na lista para
    consertar `classe` mexesse na `maturidade_stack` no mesmo movimento: **a calibração fica
    VISÍVEL em vez de silenciosa**. O acoplamento não é a função, é a LISTA — o eixo 2 faz o
    próprio `sum(...)` sobre os trechos de evidência.

    POR ISSO A FLAG TROCA A LISTA NOS DOIS EIXOS, e não só no eixo 1. O plano de 04/09 pedia o
    contrário — "constante separada, para não mover a `maturidade_stack`" —, e isso inverte a
    razão de D-060: um candidato que não alcança o eixo 2 faz o critério *"sem derrubar
    maturidade_stack abaixo de 6/7"* passar POR CONSTRUÇÃO. Um teste satisfeito pelo desenho
    não é teste, é a armadilha que D-103 apanhou em `varrer_classes.py`.

    `PROFUNDOS` continua intocado: é a lista de PRODUÇÃO, e nenhuma medição a edita.
    """
    return PROFUNDOS_CANDIDATO if USAR_PROFUNDOS_CANDIDATO else PROFUNDOS

# UM número, usado nos DOIS eixos, e é isso que impede que ele seja calibrado contra o gabarito:
# mexer nele para consertar a classe mexeria na maturidade no mesmo movimento, e a maturidade é a
# guarda desta sessão (6/7). Ver o docstring, "o `>= 3` de 2a não é parâmetro novo".
MARCADORES_PARA_PROFUNDIDADE = 3

# O DEFAULT É `False`, E ISSO É RESULTADO DE MEDIÇÃO (D-060) — mesmo destino de `USAR_JUIZ_LLM`.
#
# D-058 fixou o alvo ANTES de medir: >= 5/7 em `classe`, sem perder Deal, RD Station nem SunnyHUB.
# A barra é 5 e não 4 porque a linha de CONTROLE — a mesma aritmética com `pontos >= 3`, uma
# correção de um caractere — já faz **4/7**, que é também o placar do classificador trivial.
#
# Medido em 27/08: a rubrica em degraus faz **4/7**. Recupera a Maritaca e não perde nenhuma das
# três que a aritmética acertava. Mas empata com o trivial E com o `>= 3`, ou seja: não compra nada
# que um caractere não compre. Pela regra, não entra.
#
# O TETO EXPLICA O EMPATE, e ele era calculável antes: `profundidade_tecnica` devolve **0** em sete
# das oito fixtures — só a Maritaca tem vocabulário de infraestrutura nos documentos. O degrau `2a`
# nunca poderia mover mais de UMA fixture, e Axenya, Doutor-AI e Laura Networks são `AI-native` por
# outros sinais, dependendo do `2b`, que é idêntico à aritmética antiga. O harness passou a
# calcular esse teto (`--validar`) para que a próxima barra seja fixada sabendo o que é alcançável.
#
# `avaliar_agentes.py --rubrica` liga.
RUBRICA_EM_DEGRAUS = False


def profundidade_tecnica(docs: list[DocumentoRef]) -> tuple[int, list[Evidencia]]:
    """Quantos marcadores DISTINTOS de `marcadores()` os documentos inteiros contêm, e as frases.

    Distintos, e não ocorrências: uma página que repete "latência" oito vezes tem um sinal, não
    oito. É a mesma leitura que o eixo 2 já fazia (`sum(1 for p in PROFUNDOS if p in texto)`).

    A evidência devolvida é UMA FRASE POR DOCUMENTO, e isso não é um teto novo: é a regra que
    `extractor._casar` já declara — *"uma evidência por documento: corroboração vem de docs
    distintos"*. A CONTAGEM varre tudo; o que se anexa ao diagnóstico é o que se pode citar. Como
    `evidence_validator.avaliar` decide por TIPOS de fonte e por data, e não por volume, restringir
    o que se anexa não altera a confiança — só evita inflar a aparência de evidência.
    """
    marcadores: set[str] = set()
    evidencias: list[Evidencia] = []
    for doc in docs:
        primeira_do_doc = True
        for frase in frases(doc):
            baixa = frase.lower()
            if casados := [m for m in marcadores() if m in baixa]:
                marcadores.update(casados)
                if primeira_do_doc:
                    evidencias.append(Evidencia.de_documento(doc, frase[:400]))
                    primeira_do_doc = False
    return len(marcadores), evidencias


def node(state: EstadoAnalise) -> dict:
    perfil = state.get("perfil")
    if perfil is None:
        return {"erros": ["Classifier chamado sem perfil"]}
    startup = state.get("startup")
    docs = startup.documentos if startup else []

    evidencias: list[Evidencia] = []
    razoes: list[str] = []

    # ── Eixo 1: AI-native vs AI-enabled vs non-AI ────────────────────────────
    autopilot = bool(perfil.modelo_entrega
                     and "autopilot" in perfil.modelo_entrega.texto.lower())
    dado_proprio = bool(perfil.sinais_dado_proprietario)
    sinal_tecnico = bool(perfil.sinais_otimizacao_tecnica)
    # Só o braço da rubrica lê estes valores. Calcular sempre custa uma varredura de frases
    # e 13 marcadores por documento, descartada em produção. Achado nº 3 do review de 27/08.
    n_profundos, ev_profundos = profundidade_tecnica(docs) if RUBRICA_EM_DEGRAUS else (0, [])

    if autopilot:
        evidencias += perfil.modelo_entrega.evidencias
        razoes.append("vende resultado (autopilot), não ferramenta")
    elif perfil.modelo_entrega:
        razoes.append("posicionamento de copilot: vende a ferramenta")
    if dado_proprio:
        evidencias += perfil.sinais_dado_proprietario[0].evidencias
        razoes.append("indício de dado proprietário alimentando o sistema")
    if sinal_tecnico:
        evidencias += perfil.sinais_otimizacao_tecnica[0].evidencias
        razoes.append("vocabulário técnico de IA presente nos documentos")

    # `pontos == 0` E `non-AI` SÃO COISAS DIFERENTES, E ATÉ 04/09 ESTE MÓDULO AS CONFUNDIA.
    # Ver o bloco `A DETECÇÃO FALHA DEIXA DE VIRAR AFIRMAÇÃO` no docstring, e D-101.
    # A variável é calculada aqui, uma vez, porque os DOIS braços fazem a mesma pergunta —
    # "algum detector disparou?" — e ela é independente de qual rubrica está ligada.
    algum_sinal = bool(autopilot or dado_proprio or sinal_tecnico or n_profundos)
    if not algum_sinal:
        # A razão diz só O QUE ACONTECEU. Quem tira a CONCLUSÃO — "o rótulo não é constatação" —
        # é a linha `?` do briefing, que tem o número de dores em mãos e é onde o gerente lê.
        # Dizer as duas coisas nos dois lugares fazia a linha `Base` repetir a linha de baixo, e
        # a primeira redação ainda dizia "o rótulo abaixo" sobre um rótulo que é impresso acima.
        # A CLÁUSULA VEM PRIMEIRO, E O TEXTO DIZ POR QUE O COPILOT NÃO CONTA (D-103).
        # A linha `Base` do briefing saía como "posicionamento de copilot: vende a ferramenta;
        # nenhum detector de IA disparou" — o Extractor LEU o modelo de entrega, e a cláusula
        # seguinte dizia que nada foi encontrado. Lidas em sequência, as duas se contradizem;
        # lidas com a rubrica na mão, não: `copilot` é sinal NEGATIVO em `contexto/02` §4, não
        # ausência de leitura. O texto passa a dizer isso, em vez de deixar o leitor concluir.
        # Curta de propósito: `justificativa` é um `join` de todas as razões e já é a linha mais
        # larga do briefing (~180 col). A versão longa desta cláusula somava mais 100 — piorava
        # o mesmo defeito de largura que D-103 estava corrigindo em outras três linhas.
        razoes.insert(0, "nenhum dos 3 detectores do eixo 1 disparou — o que segue foi lido, "
                         "não é sinal de IA operada")

    if RUBRICA_EM_DEGRAUS:
        # Degrau 2a e 2b. `opera_propria_ia` é a pergunta do eixo 1 em uma linha.
        profundidade_propria = n_profundos >= MARCADORES_PARA_PROFUNDIDADE
        opera_propria_ia = profundidade_propria or (autopilot and dado_proprio)
        if profundidade_propria:
            evidencias += ev_profundos
            razoes.append(f"profundidade técnica própria: {n_profundos} marcadores distintos de "
                          f"infraestrutura de IA nos documentos")
        classe: ClasseStartup = (
            "non-AI" if not algum_sinal
            else "AI-native" if opera_propria_ia
            else "AI-enabled"
        )
    else:
        # A ARITMÉTICA DE PRODUÇÃO, com o defeito NOMEADO em vez de escondido: os pesos 2/2/1 não
        # vêm da rubrica, e `>= 4` exige na prática autopilot E dado proprietário — profundidade
        # técnica sozinha vale 1 e nunca alcança. A régua mede 3/7, contra 4/7 do trivial.
        pontos = 2 * autopilot + 2 * dado_proprio + 1 * sinal_tecnico
        classe = "AI-native" if pontos >= 4 else "AI-enabled" if pontos >= 1 else "non-AI"

    # ── Eixo 2: maturidade da stack técnica ──────────────────────────────────
    # INTOCADO de propósito (D-060). Continua lendo só as <=3 frases que o Extractor recortou, e
    # continua sendo a GUARDA desta mudança: 6/7 na régua. Se este número se mexer, o contador do
    # eixo 1 vazou para onde não devia.
    texto_tecnico = " ".join(
        e.trecho.lower() for a in perfil.sinais_otimizacao_tecnica for e in a.evidencias
    )
    achados = sum(1 for p in marcadores() if p in texto_tecnico)
    maturidade: MaturidadeStack = (
        "alta" if achados >= MARCADORES_PARA_PROFUNDIDADE else "media" if achados >= 1 else "baixa"
    )
    razoes.append(f"{achados} marcador(es) de profundidade de infraestrutura nos documentos")

    return {
        "diagnostico": Diagnostico(
            classe=classe,
            maturidade_stack=maturidade,
            sinal_verificado=algum_sinal,
            quadrante=derivar_quadrante(classe, maturidade, sinal_verificado=algum_sinal),
            confianca="media",          # provisória: o Evidence Validator decide a definitiva
            justificativa="; ".join(razoes),
            evidencias=evidencias,
        )
    }
