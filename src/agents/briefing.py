"""Briefing — relatório final para o gerente de Startups & VCs da NVIDIA.

ELE FORMATA E NÃO GERA COM LLM, E ISSO É DECISÃO — a mesma de `recommendation.py`, pelas mesmas
três razões medidas: latência que o gerente sente, robustez (o grafo roda com ZERO chamada de LLM
em produção, e foi isso que o fez sobreviver ao 4º EOL do catálogo — D-087), e o fato de que
**todo texto aqui é composição de campos que já carregam evidência**. Um LLM redigindo este
relatório reescreveria afirmações que `list[Evidencia]` sustenta, e a rastreabilidade que o
rodapé promete deixaria de ser verificável por código. Onde a redação estava ruim, o conserto
foi medição e não geração: D-100 tirou três defeitos do texto que chega ao gerente, D-103
consertou a largura das linhas, e D-104 o campo 3 dos 7.

O FILTRO DE ELEGIBILIDADE do Inception é real — ver `elegibilidade()` abaixo. Ele é candidato a
Diferencial segundo
`contexto/05` §4.6, e a razão é específica: um sistema que RECUSA recomendar o Inception para
uma consultoria de IA, e explica por quê, demonstra regra de negócio; um que recomenda para
todo mundo demonstra template.

A DISCIPLINA QUE VALE NOTAR: `motivos_exclusao` e `requisitos_nao_verificados` são campos
SEPARADOS. "A base prova que é consultoria" exclui. "A base não prova que tem developer" NÃO
exclui — vira pendência a verificar na conversa. É a mesma regra 4 do Evidence Validator
(ausência de sinal != sinal negativo) aplicada a uma regra de negócio.
"""

from __future__ import annotations

import re
import textwrap
from datetime import date

from src.state import (
    AnaliseStartup,
    Elegibilidade,
    Evidencia,
    EstadoAnalise,
    EstadoRadar,
)

# Exclusões explícitas do programa (contexto/03 §2).
#
# POR QUE O CASAMENTO É POR FRONTEIRA DE PALAVRA, E NÃO POR SUBSTRING (D-048)
# ----------------------------------------------------------------------------
# Até 25/08 esta lista continha `"token"` e era casada com `if termo in texto`. Como
# `SINAIS_TECNICOS` do Extractor inclui `"tokens por segundo"`, uma frase sobre custo de
# inferência virava evidência técnica e disparava *"exclusão por 'cripto'"* — QUALQUER startup
# que falasse em "custo por token" era reportada NÃO ELEGÍVEL ao Inception, pelo motivo errado,
# no filtro que o projeto chama de Diferencial.
#
# Duas correções, e elas são independentes:
#   1. `"token"` SAIU. Ele é ambíguo entre dois domínios (cripto e inferência de LLM) e o
#      contexto que os separa não cabe numa lista de termos. Os substitutos abaixo só existem
#      em contexto cripto, e `criptomoeda`/`blockchain`/`web3`/`bitcoin` já cobriam o resto —
#      medido: o caso de teste de tokenização continua excluído por `blockchain`.
#   2. O casamento passou a exigir fronteira de palavra NO INÍCIO DO TERMO, e só no início.
#      `"consultoria"` casa em "consultoria(s)" — plural é a forma comum em texto institucional —
#      e `"revend"` casa em "revendedores". Ancorar TAMBÉM no fim desliga os dois (D-057).
#      É a mesma correção que D-039 exigiu no gabarito do RAG, onde `ILIKE '%SLA%'` casava
#      dentro de "tran(sla)tion".
#
#      CORREÇÃO DE 31/08: este comentário justificava a fronteira dizendo que `"ipo"` deixava de
#      casar dentro de "equ(ipo)" e "princ(ípio)". **O termo desta lista SEMPRE foi `"ipo
#      concluído"`** — verificado no primeiro commit que o criou —, e "ipo concluído" nunca casou
#      dentro de "equipo", com âncora ou sem. O exemplo era ficção: a mudança está certa pelos
#      dois motivos reais acima, mas um dos argumentos que a sustentavam nunca foi verificado.
#      Quarta ocorrência do mesmo padrão no projeto (D-057 nº 1, D-061, D-066 nº 3).
#
#   3. `"revenda"` virou o PREFIXO `"revend"` (D-071), e o efeito medido é um TRADE-OFF, não uma
#      melhora dos dois lados: falso negativo 6/7 -> **7/7**, falso positivo 3/7 -> **2/7**.
#      Conserta um vazamento silencioso — *"Somos revendedores autorizados"* passava pelo filtro,
#      porque "revenda" não é prefixo de "revendedor" — e cria um falso positivo visível em
#      *"Nossos clientes revendem os relatórios"*.
#      O que autoriza a troca é a ASSIMETRIA de D-057, não o placar: o falso positivo aparece no
#      briefing e alguém o corrige; o falso negativo não aparece em lugar nenhum — a startup
#      inelegível entra na recomendação e ninguém fica sabendo. Somar os dois lados num número só
#      esconderia exatamente isto, que é a razão de `--exclusoes` nunca os somar.
#      O vazamento só foi achado quando a régua passou a exercitar `revenda` (D-061): ele
#      sobreviveu à auditoria que D-057 fez de D-048 porque não havia caso que o exercitasse.
#
#      ANCORAR OS DOIS LADOS FOI TENTADO E ESTÁ ERRADO: `\bconsultoria\b` NÃO casa
#      "prestamos consultorias de dados", e uma empresa que se descreve no plural passa pelo
#      filtro. O code review de 25/08 mediu isso; o teste `test_plural_continua_excluindo` é a
#      rede. Ressalva conhecida: a comparação é sensível a acento — `"ipo concluído"` não casa
#      "ipo concluido".
EXCLUSOES = {
    "consultoria": ["consultoria", "consulting", "desenvolvimento terceirizado", "fábrica de software",
                    "body shop", "outsourcing de ti"],
    # `blockchain` SAIU EM 03/09 (D-090), e é a repetição exata de D-048.
    # D-048 tirou "token" da lista porque o termo é ambíguo entre cripto e inferência de LLM, e
    # "custo por token" derrubava qualquer startup de infraestrutura. `blockchain` tem a MESMA
    # forma: é nome de TECNOLOGIA, não de IDENTIDADE. A base de 03/09 trouxe o caso real — a
    # Ecotrace rastreia boi e soja com blockchain e saía `NÃO ELEGÍVEL` por 'cripto', numa
    # ferramenta cujo trabalho é achar startups para o Inception.
    #
    # POR QUE O VETO DE TERCEIRO (D-085) NÃO ALCANÇAVA ISTO: ele responde "de quem a frase
    # fala?" — e aqui a frase fala mesmo da própria empresa. A pergunta que faltava é outra:
    # "ser isto DEFINE a empresa?". Usar blockchain não define ninguém como cripto, do mesmo
    # jeito que pagar por token não define ninguém como cripto.
    #
    # A rede que garante que a remoção não abre a porta: a Liqi, que é cripto de verdade,
    # continua excluída por `tokenização de ativos` — medido em `--exclusoes`, os dois lados.
    # `stablecoin` e `ativos virtuais` ENTRARAM em 03/09, na mesma sessão em que `blockchain`
    # saiu — e o par não é coincidência: a lista estava errada nas DUAS direções. Tinha um termo
    # de tecnologia excluindo quem não é cripto, e não tinha os termos que nomeiam quem é.
    # `ativos virtuais` é o termo LEGAL brasileiro (Lei 14.478, SPSVAs), e aparece literal nos
    # documentos. Emitir stablecoin é identidade, não uso.
    "cripto": ["criptomoeda", "cryptocurrency", "web3", "bitcoin", "stablecoin",
               "ativos virtuais", "tokenização de ativos", "security token", "utility token",
               "token não fungível", "nft"],
    "cloud provider": ["cloud service provider", "provedor de nuvem", "datacenter próprio"],
    "revenda": ["revend", "distribuidor", "reseller"],   # prefixo: cobre revenda E revendedor (D-071)
    # A LISTA ERA B3-CÊNTRICA, E ISSO ERA O CASO MAIS COMUM, NÃO O EXÓTICO (03/09, D-094).
    # Tinha "listada na b3" e "ipo concluído", e a Zenvia — listada na NASDAQ desde 2021 — saía
    # ELEGÍVEL. Metade das brasileiras que abrem capital lista fora do Brasil: Nubank, VTEX e
    # PagSeguro na NYSE, StoneCo, XP e Zenvia na Nasdaq. O conceito estava certo; o vocabulário
    # cobria uma bolsa só.
    #
    # POR QUE NÃO `"listada na"` GENÉRICO: casaria "listada na Forbes", "listada na pesquisa".
    # O veto de terceiro de D-085 não ajuda aí — ele responde de QUEM a frase fala, não o que a
    # frase significa. Então a lista nomeia as bolsas e as formas legais, e paga o preço de ser
    # lista: só cobre o que já se viu. `companhia aberta` é o termo do direito societário
    # brasileiro e vale mais que qualquer nome de bolsa.
    "capital aberto": ["capital aberto", "companhia aberta", "abriu capital",
                       "listada na b3", "listada na nasdaq", "listada na nyse",
                       "listada em bolsa", "listada na bolsa",
                       "publicly traded", "ipo concluído"],
}
IDADE_MAXIMA = 10   # o programa exige menos de 10 anos de existência

# O VETO DE TERCEIRO — P-13, ABERTA DESDE 25/08 (D-052 achado 3), FECHADA EM 02/09 (D-085)
# -----------------------------------------------------------------------------------------
# O filtro acima excluía por MENÇÃO, não por identidade: bastava o termo aparecer em qualquer
# evidência. Medido, o estrago era de 5 em 7 — e rodando o grafo em 02/09 a **Axenya**, o prospect
# de maior prioridade da base, saía `NÃO ELEGÍVEL` porque a home dela diz *"Integramos consultoria,
# dados e operação clínica"*. Numa ferramenta cujo trabalho é achar startups para o Inception.
#
# O SINAL QUE SEPARA OS CASOS JÁ ESTAVA ESCRITO — pelo curador, nas notas de `exclusoes.yaml`:
# *"o sujeito é um PARCEIRO"*, *"a empresa é CLIENTE de consultoria"*, *"quem revende é o CLIENTE"*,
# *"USO, não identidade"*. É sempre a mesma pergunta: **de quem a frase está falando.**
#
# O QUE FAZ ISTO GENERALIZAR NÃO É A LISTA DE PALAVRAS — É O ESCOPO DE FRASE.
# O veto vale só dentro da frase em que o termo ocorre. É o que separa
#     "Somos uma consultoria. Nossos clientes são bancos."   -> EXCLUI (duas frases)
# de
#     "Contratamos uma consultoria externa."                 -> passa  (uma frase)
# Um veto global sobre o trecho inteiro erraria o primeiro caso, e trecho de evidência é
# parágrafo, não sentença. `tests/test_elegibilidade.py` guarda exatamente esse par.
#
# POR QUE VETO E NÃO ÂNCORA DE IDENTIDADE (`somos|é uma <termo>`): a própria régua chama a âncora
# de *"armadilha do desenho recomendado"* e planta o contra-exemplo — *"Como **nossa consultoria**
# de IA para empresas gera resultados"*, identidade por possessivo, que a âncora perde. E há uma
# razão estrutural, que é a assimetria de D-057: um veto só **remove** exclusão, então o lado do
# falso NEGATIVO — o silencioso, o que não aparece em lugar nenhum — não pode regredir por
# construção. Uma âncora reescreve os dois lados de uma vez.
#
# `terceirizad` NÃO ESTÁ NA LISTA, DE PROPÓSITO: `EXCLUSOES["consultoria"]` contém
# `"desenvolvimento terceirizado"`, e o marcador anularia o próprio termo que ele deveria deixar
# passar. Foi a única colisão entre as duas listas, e está verificada uma a uma.
MARCADORES_DE_TERCEIRO = [
    # (1) o SUJEITO da frase é outra empresa
    "nossos clientes", "seus clientes", "entre os clientes", "dos clientes",
    # `parceria entre` ENTROU em 03/09 (D-092), e o episódio é sobre a natureza desta lista.
    # D-085 previu o caso — "o termo está no NOME de uma parceira" — e escreveu `parceria com`.
    # A frase real do site da Automni diz *"a parceria ENTRE a Davinci - Consulting & Tech e a
    # Automni"*. O ESCOPO DE FRASE, que é o que faz o veto generalizar, estava certo; o que
    # faltou foi a variante da preposição. Não é falha do desenho, é o custo declarado dele:
    # lista de marcadores OBSERVADOS paga o preço de só cobrir o que já se viu.
    "parceria com", "parceria entre", "parceiro", "parceira",
    # (2) a empresa é CONSUMIDORA do que o termo nomeia
    "contrata",            # contratamos, contratou, contratada — prefixo, como `revend` (D-071)
    "integramos", "integrou",
    # (3) o que o termo nomeia é declaradamente DE FORA
    "externa", "externo", "de terceiros",
    # (4) O TERMO NOMEIA UM MERCADO, NÃO A EMPRESA — categoria nova em 03/09 (D-094).
    # Ela nasceu de um falso positivo que ESTA MESMA SESSÃO criou: ao pôr `stablecoin` na lista
    # de cripto, a Iniciador — infraestrutura de Open Finance e Pix — passou a ser recusada por
    # *"disputada por gigantes de cartões e pelo mercado de stablecoins"*. Não é "outra empresa"
    # (categoria 1) nem "somos consumidores" (categoria 2): é contexto competitivo.
    #
    # POR QUE `"mercado de stablecoin"` E NÃO `"mercado de"` GENÉRICO: *"atuamos no mercado de
    # criptomoedas"* É declaração de identidade, e um marcador genérico a vetaria — trocando um
    # falso positivo visível por um falso NEGATIVO silencioso, que D-052 nomeou como o pior dos
    # dois. Marcador observado, escopo estreito, preço declarado: só cobre o que já se viu.
    "mercado de stablecoin",
]

# `;` entra junto de `.!?` porque em texto institucional a enumeração com ponto e vírgula separa
# sujeitos tanto quanto o ponto final. Quebra de linha também: o texto vem de página HTML limpa,
# onde cada item de lista é uma linha e cada linha é uma afirmação independente.
_FIM_DE_FRASE = re.compile(r"[.!?;\n]+")


def _ocorre(termo: str, texto: str) -> bool:
    """Fronteira de palavra NO INÍCIO do termo. Ver o comentário de `EXCLUSOES`."""
    return re.search(rf"\b{re.escape(termo)}", texto) is not None


def _fala_de_terceiro(termo: str, texto: str) -> bool:
    """A ocorrência do termo está numa frase que fala de OUTRA empresa? Ver `MARCADORES_DE_TERCEIRO`.

    Devolve `True` quando TODA ocorrência do termo cai em frase com marcador de terceiro. Basta uma
    ocorrência limpa para o veto não valer: uma consultoria que também menciona parceiros continua
    sendo excluída pela frase em que ela se descreve.
    """
    frases = [f for f in _FIM_DE_FRASE.split(texto) if _ocorre(termo, f)]
    return bool(frases) and all(
        any(_ocorre(m, f) for m in MARCADORES_DE_TERCEIRO) for f in frases
    )


def elegibilidade(analise_startup, perfil) -> Elegibilidade:
    motivos: list[str] = []
    pendentes: list[str] = []
    evidencias: list[Evidencia] = []

    # PERCORRE EVIDÊNCIA A EVIDÊNCIA, E NÃO O TEXTO CONCATENADO (D-049).
    # A versão anterior juntava todos os trechos numa string só, o que tornava impossível dizer
    # DE ONDE veio o termo — e `Elegibilidade.evidencias` nascia `[]` e nunca era preenchida,
    # enquanto o motivo afirmava "o termo X aparece nos documentos" sob o rodapé "Toda conclusão
    # acima aponta para o documento que a sustenta". Era a única conclusão do sistema sem
    # `list[Evidencia]`, contra a invariante do repositório.
    todas = [e for a in (perfil.afirmacoes if perfil else []) for e in a.evidencias]
    for rotulo, termos in EXCLUSOES.items():
        # O VETO DE TERCEIRO ENTRA AQUI, E NÃO DENTRO DE `_ocorre` (D-085): `_ocorre` responde
        # "o termo está no texto?", que é pergunta lexical e é usada também pelo veto. Quem
        # responde "e a frase fala da própria empresa?" é `_fala_de_terceiro`, e são duas
        # perguntas. Juntá-las numa função só faria o veto se aplicar a si mesmo.
        achou = next(
            ((termo, ev) for termo in termos for ev in todas
             if _ocorre(termo, ev.trecho.lower())
             and not _fala_de_terceiro(termo, ev.trecho.lower())),
            None,
        )
        if achou:
            termo, ev = achou
            motivos.append(
                f"exclusão por '{rotulo}': o termo {termo!r} aparece nos documentos "
                f"falando da própria empresa"
            )
            evidencias.append(ev)

    # A BORDA DA IDADE — P-20, ABERTA POR D-082, FECHADA EM 02/09 (D-085)
    # `date.today().year - ano_fundacao` tem precisão de ANO, e o programa exige "menos de 10
    # anos". Com ano só, a idade real cai numa faixa de 12 meses — a Laura Networks, fundada em
    # 2016, tem hoje entre 9,7 e 10,7 anos — e essa faixa cruza o limite EXATAMENTE quando
    # `idade == IDADE_MAXIMA`. Decidir exclusão ali é fingir uma precisão que o dado não tem, e o
    # custo é assimétrico: exclui-se do funil uma empresa que pode ser elegível, em silêncio.
    #
    # Fora da borda não há dúvida nenhuma: `idade > 10` significa real >= 10,x (exclui com certeza)
    # e `idade < 10` significa real <= 9,x (passa com certeza). Só o empate é indeterminado, e ele
    # vira PENDENTE — o mesmo idioma que o gabarito já usa (`elegivel: [true, false]`): sai do
    # denominador em vez de premiar ou punir uma precisão inexistente.
    #
    # Alternativa descartada — guardar o MÊS de fundação: resolveria de verdade, mas o mês não
    # consta nos documentos de 6 das 8 fixtures. Preenchê-lo por inferência é exatamente o que
    # D-021 barrou nas fixtures do seed.
    if analise_startup.ano_fundacao:
        idade = date.today().year - analise_startup.ano_fundacao
        if idade > IDADE_MAXIMA:
            motivos.append(
                f"exclusão por idade: fundada em {analise_startup.ano_fundacao}, {idade} anos "
                f"(o programa exige menos de {IDADE_MAXIMA})"
            )
        elif idade == IDADE_MAXIMA:
            pendentes.append(
                f"idade na borda: fundada em {analise_startup.ano_fundacao}, entre "
                f"{IDADE_MAXIMA - 1} e {IDADE_MAXIMA} anos — o documento dá o ano, não o mês. "
                f"Confirmar a data exata antes de descartar (o programa exige menos de "
                f"{IDADE_MAXIMA})"
            )

    # Requisitos que a base não tem como provar. NÃO excluem — viram pauta da conversa.
    if not analise_startup.ano_fundacao:
        pendentes.append("ano de fundação não consta na base — verificar se tem menos de 10 anos")
    if not analise_startup.site:
        pendentes.append("site ativo não confirmado na base")
    if not (perfil and perfil.sinais_otimizacao_tecnica):
        pendentes.append("presença de ao menos um developer empregado não confirmada na base")
    pendentes.append("incorporação formal da empresa não verificável pelos documentos públicos")

    return Elegibilidade(
        elegivel=not motivos,
        motivos_exclusao=motivos,
        requisitos_nao_verificados=pendentes,
        evidencias=evidencias,
    )


def node_analise(state: EstadoAnalise) -> dict:
    """Roda DENTRO do subgrafo: a elegibilidade é por empresa."""
    return {"elegibilidade": elegibilidade(state["startup"], state.get("perfil"))}


# D-103: o quadrante NÃO é `fora-do-funil` para quem tem sinal não verificado (D-101), mas
# `PROSPECT DE EVOLUÇÃO — a conversa é sair do wrapper` também não serve: a SunnyHUB é energia
# solar e NÃO TEM WRAPPER NENHUM. É a mesma família do "sem evidência validada" que D-100
# removeu — rótulo cujo texto explicativo não vale para o caso.
#
# POR QUE TEXTO VARIANTE E NÃO UM QUINTO VALOR DE `Quadrante`: a matriz de `contexto/02` §4 é
# publicada com QUATRO células, e o que muda aqui não é a célula — é o que se pode DIZER sobre
# ela quando o rótulo que a produziu não foi constatado. Um quinto valor seria mais uma coisa
# a defender na arguição, e o tipo passaria a misturar "onde a empresa está" com "quanto eu
# sei disso" — que é a ortogonalidade que `sinal_verificado` existe para preservar.
# 50 colunas + as 18 do prefixo `  Quadrante     : ` = 68, dentro das 78 do relatório. O detalhe
# — quantos detectores, quantas dores — está na linha `?` logo abaixo; repeti-lo aqui estouraria
# a largura pela terceira vez no mesmo dia.
ROTULO_SEM_SINAL = "A VERIFICAR — nenhum sinal de IA encontrado na base"

ROTULO_QUADRANTE = {
    "sweet-spot": "SWEET SPOT — AI-native com stack imatura: melhor prospect",
    "prospect-de-evolucao": "PROSPECT DE EVOLUÇÃO — a conversa é sair do wrapper",
    "ja-otimizada": "JÁ OTIMIZADA — provavelmente já é membro ou já usa NVIDIA",
    "fora-do-funil": "FORA DO FUNIL — não é prospect",
}


def rotulo_do_quadrante(diagnostico) -> str:
    """O rótulo que o gerente lê, com a ressalva de D-101 na frente quando ela vale.

    Extraída de `_secao` em 06/09 pelo mesmo motivo de `ordenar_analises`: a interface precisa
    do MESMO rótulo. Se a tela recalculasse a regra, `sinal_verificado=False` poderia aparecer
    como `PROSPECT DE EVOLUÇÃO` na tela e como `A VERIFICAR` no briefing exportado do mesmo run —
    e a tela estaria afirmando ao gerente exatamente o que D-101 existe para não afirmar.
    """
    if not diagnostico.sinal_verificado:
        return ROTULO_SEM_SINAL
    return ROTULO_QUADRANTE.get(diagnostico.quadrante, diagnostico.quadrante)


def _resumir(texto: str, limite: int) -> str:
    r"""Corta em fronteira de PALAVRA e anuncia o corte. Ver D-100.

    O que havia era `texto[:150]`, e na tela isso produzia `"...NVIDIA NIM™ microse"` e
    `"...é a passagem citada da documentaçã"` — dois dos SETE campos obrigatórios do TAPI,
    cortados no meio da palavra, sem sinal de que havia mais texto. Um leitor não distingue
    "o campo acabou assim" de "o campo foi truncado".

    O `\s+` colapsado resolve o segundo defeito da mesma linha: `justificativa_tecnica` sai de
    `melhor_trecho`, que devolve um span do chunk — e chunk de página web carrega quebra de
    linha no meio. Impresso cru, ele quebra o alinhamento da coluna e o parágrafo continua na
    margem esquerda, como se fosse outro campo.

    A reticência é `…` (U+2026) e não `...`: ela ocupa uma coluna, e o campo é impresso dentro
    de uma tabela de largura fixa.
    """
    limpo = re.sub(r"\s+", " ", texto).strip()
    # `limite <= 1` não tem saída válida: o `…` sozinho já ocupa uma coluna. Sem esta guarda,
    # `limite=0` produzia `limpo[:-1]` — uma fatia NEGATIVA que devolve quase o texto inteiro,
    # o oposto do contrato. Inalcançável pelos dois chamadores de hoje (130 e 150), e este é um
    # helper de uso geral: contrato que falha em silêncio na borda é contrato que não vale.
    if limite <= 1:
        return "…" if limpo else ""
    if len(limpo) <= limite:
        return limpo
    # `limite - 1` porque o `…` conta: a saída nunca é mais larga que o `limite` pedido, e a
    # coluna do briefing tem largura fixa.
    cabe = limpo[:limite - 1]
    # `rsplit` na última fronteira dentro do limite. Sem fronteira nenhuma — um "palavrão"
    # técnico maior que o limite, como uma URL — corta no limite mesmo: melhor um corte
    # anunciado que uma linha vazia.
    corte = cabe.rsplit(" ", 1)[0]
    return f"{corte or cabe}…"


def _secao(a: AnaliseStartup, exige_sinais_ia: bool = False) -> list[str]:
    L = [f"\n{'─' * 78}", f"  {a.nome.upper()}", f"{'─' * 78}"]
    if a.erros:
        L.append(f"  [análise incompleta] {'; '.join(a.erros)}")
    if a.diagnostico:
        d = a.diagnostico
        L += [
            f"  Classificação : {d.classe}   (confiança {d.confianca})",
            f"  Stack técnica : maturidade {d.maturidade_stack}",
            f"  Quadrante     : {rotulo_do_quadrante(d)}",
            f"  Base          : {d.justificativa}",
        ]
        # A regra 5 de contexto/02 §6 é "o output carrega a confiança, NÃO SÓ O RÓTULO". Imprimir
        # `(confiança baixa)` sem dizer qual regra a produziu deixa o rodapé desta página — "toda
        # conclusão acima aponta para o documento que a sustenta" — mentindo na linha mais lida do
        # briefing. É o mesmo defeito do achado nº 5 do code review de 25/08, onde D-049 guardava a
        # evidência da exclusão e `_secao` não a imprimia.
        if d.motivo_confianca:
            L.append(f"  Confiança     : {d.motivo_confianca}")
        # D-101: o rótulo não constatado se ANUNCIA, no mesmo idioma do `?` da elegibilidade.
        # Sem esta linha o desenho estaria pela metade: a empresa deixaria de ser cortada do
        # funil em silêncio e passaria a ser incluída em silêncio — e o gerente continuaria
        # sem saber que `non-AI`, ali, quer dizer "não achei sinal" e não "não tem IA".
        #
        # TRÊS LINHAS DE <= 78 COLUNAS, E ISSO FOI MEDIDO (D-103). A primeira versão dizia no
        # comentário que estava dividida "porque o relatório tem 78 colunas" e entregava 110 —
        # dividiu o estouro ao meio em vez de removê-lo, num texto impresso uma vez por empresa.
        #
        # E O TEXTO NÃO DIZ MAIS "dor(es) DE IA" (D-103): `extractor.GATILHOS_DOR` casa dor de
        # NEGÓCIO, sem nenhuma trava de IA — a dor de `custo` da Conta Simples se apoia em
        # "análise por centros de custos". Contar essas como prova de que o Extractor achou
        # sinal de IA que os detectores perderam é a mesma afirmação sem lastro que D-100
        # removeu do campo ao lado. O número é honesto; a etiqueta dele não era.
        if not d.sinal_verificado:
            n_dores = len(a.perfil.dores_observadas) if a.perfil else 0
            L += [
                "    ? sinal de IA NÃO VERIFICADO — nenhum dos 3 detectores do eixo 1",
                f"      disparou neste documento, e o Extractor achou {n_dores} dor(es)",
                "      observada(s) com evidência. O rótulo acima é o que a regra",
                "      produziu, não o que a base constatou",
            ]
            # `exige_sinais_ia` GANHOU LEITOR AQUI — P-14, D-112. O campo era calculado e
            # descartado. Ele responde a uma pergunta que só o gerente pode fazer: *esta
            # empresa entra no que EU pedi?* Quando a consulta pediu IA nominalmente e o sinal
            # não foi constatado, a lacuna deixa de ser uma nota técnica e vira o motivo de a
            # empresa merecer um olhar antes da abordagem.
            #
            # E ELE NÃO FILTRA, DE PROPÓSITO: filtrar seria ausência de sinal virando sinal
            # negativo, que é exatamente o que D-101 tirou deste sistema. O campo anota; a
            # decisão de abordar continua sendo de quem lê.
            if exige_sinais_ia:
                L.append("      — e a sua consulta pediu IA explicitamente: confirmar na "
                         "conversa")
    if a.elegibilidade:
        e = a.elegibilidade
        L.append(f"\n  NVIDIA Inception: {'ELEGÍVEL' if e.elegivel else 'NÃO ELEGÍVEL'}")
        # D-049 passou a GUARDAR a evidência de cada exclusão; se ela não for IMPRESSA, o
        # rodapé "toda conclusão aponta para o documento que a sustenta" continua mentindo
        # exatamente aqui. Achado nº 5 do code review de 25/08.
        for i, m in enumerate(e.motivos_exclusao):
            L.append(f"    x {m}")
            if i < len(e.evidencias):
                ev = e.evidencias[i]
                L.append(f"        [{ev.tipo_documento}] {ev.url_fonte}")
                L.append(f"           \"{_resumir(ev.trecho, 130)}\"")
        for p in e.requisitos_nao_verificados:
            L.append(f"    ? {p}")

    L.append(f"\n  Recomendações ({len(a.recomendacoes)}):")
    if not a.recomendacoes:
        # A CAUSA VEM DO ESTADO, NÃO DE UMA FRASE FIXA (D-100). A frase antiga — "sem evidência
        # validada que sustente uma recomendação" — era impressa para TODA lista vazia. Medido
        # em 04/09: Conta Simples, Core AI e Iniciador têm 3, 5 e 7 dores VALIDADAS e recebiam
        # essa frase; a causa real era o corte de funil. O `or` cobre a análise parcial, em que
        # `recommendation` nem chegou a rodar — e aí a única resposta honesta é dizer isso.
        L.append(f"    nenhuma — {a.motivo_sem_recomendacao or 'a análise não chegou ao motor de recomendação'}")
    # D-099: a recusa do Inception rotula as recomendações em vez de suprimi-las, e o rótulo
    # aparece UMA vez, acima da lista.
    #
    # LÊ `a.elegibilidade`, QUE JÁ ESTÁ EM MÃOS (D-103). A primeira versão lia um campo
    # `fora_do_inception` carimbado em cada `Recomendacao` — estado derivável, duplicado até 3
    # vezes por empresa. E ELA REPETIA O MOTIVO: a string byte a byte já saiu cinco linhas
    # acima, no `x` do bloco de elegibilidade, ali COM a evidência. O que é informação nova
    # aqui é só o enquadramento comercial; o motivo, o leitor acabou de ler.
    if a.recomendacoes and a.elegibilidade and not a.elegibilidade.elegivel:
        L.append("    !! FORA DO INCEPTION — abordagem comercial direta, não captação")
        L.append("       para o programa. O motivo da recusa está no bloco acima.")
    for i, r in enumerate(a.recomendacoes, 1):
        L += [
            f"\n    {i}. {', '.join(r.tecnologias)}",
            f"       prioridade {r.prioridade} · complexidade {r.complexidade}",
            # Lista vazia é alcançável desde D-063 (citação sem `dor_origem`, o caminho da
            # interface) e renderizava "dores      : " com nada depois dos dois-pontos, no
            # entregável que o vídeo mostra. Mesmo defeito que `proxima_acao` já guardava.
            f"       dores      : {', '.join(r.dores_enderecadas) or '— (citação não veio de uma dor)'}",
            f"       técnica    : {_resumir(r.justificativa_tecnica, 150)}",
            f"       negócio    : {_resumir(r.justificativa_negocio, 150)}",
            f"       ação       : {r.proxima_acao}",
            f"       evidências : {len(r.evidencias)} trecho(s) com fonte",
        ]
        for ev in r.evidencias[:2]:
            L.append(f"          [{ev.tipo_documento}] {ev.url_fonte}")
            L.append(f"             \"{_resumir(ev.trecho, 130)}\"")
        for c in r.citacoes_rag:
            L.append(f"          [base NVIDIA] {c.tecnologia} — {c.url_fonte}")
    return L


# EXTRAÍDA DO CLOSURE DE `node` EM 06/09, PARA QUE A INTERFACE REUSE A MESMA REGRA.
# A ordem em que as empresas aparecem é uma afirmação do sistema sobre qual prospect abordar
# primeiro. Se a tela ordenasse por conta própria, o gerente veria uma ordem na tela e outra no
# briefing que ele acabou de exportar do mesmo run — e nada na saída denunciaria a diferença.
# Duplicar quatro linhas custaria dois lugares para consertar; extrair não muda comportamento
# nenhum (é o mesmo código, movido) e passa a haver UMA definição de "quem vem primeiro".
def ordenar_analises(analises: list[AnaliseStartup]) -> list[AnaliseStartup]:
    """Prioridade máxima da empresa primeiro; empate desfeito pelo nome.

    `default=3` põe quem não tem recomendação nenhuma DEPOIS de quem tem prioridade baixa —
    a empresa sem recomendação é a que menos ajuda o gerente a decidir o próximo telefonema.
    """
    ordem = {"alta": 0, "media": 1, "baixa": 2}

    def chave(a: AnaliseStartup):
        pri = min((ordem[r.prioridade] for r in a.recomendacoes), default=3)
        return (pri, a.nome)

    return sorted(analises, key=chave)


def node(state: EstadoRadar) -> dict:
    """Roda no grafo PAI, com `defer=True`: só executa depois de todas as branches."""
    analises = state.get("analises") or []

    L = [
        "=" * 78,
        "  NVIDIA STARTUP AI RADAR — BRIEFING EXECUTIVO",
        "=" * 78,
        f"  Consulta : {state['consulta']}",
        f"  Data     : {date.today().strftime('%d/%m/%Y')}",
        f"  Empresas : {len(analises)} analisada(s)",
    ]
    plano = state.get("plano")
    if plano:
        L.append(f"  Critérios: setores={plano.setores or '—'} · "
                 f"palavras-chave={plano.palavras_chave[:6]}")
        # A ESTRATÉGIA DE ANÁLISE ERA CALCULADA E JOGADA FORA — P-14, D-112. Ela agora é
        # DERIVADA do que o subgrafo faz (`query_planner.descrever_estrategia`), então imprimi-la
        # é relatar a execução, não decorar o cabeçalho. Enquanto ela era uma constante, imprimir
        # era pior que a lacuna: afirmaria ao gerente que aquele texto governou a análise.
        # `textwrap` e não um corte com `…`: aqui o texto INTEIRO importa — ele descreve o que
        # o subgrafo fez, e uma estratégia truncada no meio é pior que nenhuma. O limite de 64
        # mantém a linha dentro das 78 colunas do relatório com o rótulo na frente.
        estrategia = textwrap.wrap(plano.estrategia_analise, 64) or ["—"]
        L.append(f"  Análise  : {estrategia[0]}")
        L += [f"             {linha}" for linha in estrategia[1:]]
        # D-081: o caso silencioso. `palavras-chave=[]` já estava impresso acima e não dizia
        # nada a ninguém — o relatório seguia idêntico ao de uma recuperação bem-sucedida.
        # Um resultado sem lastro tem de se anunciar na primeira tela, não no rodapé.
        if not plano.discrimina():
            L += ["",
                  "  *** ATENÇÃO: esta consulta não produziu NENHUM critério de busca. ***",
                  "  As empresas abaixo são uma fatia arbitrária da base — não um resultado",
                  "  de recuperação. Refaça a consulta nomeando setor, estágio ou tecnologia."]

    # Caso zero: o briefing é alcançado mesmo sem nenhum fan-out (D-023). Um relatório que
    # diz POR QUE não encontrou é resposta; terminar sem relatório é o sistema não responder.
    if not analises:
        L += ["", "  NENHUMA STARTUP CASOU OS CRITÉRIOS DESTA CONSULTA.", ""]
        for e in state.get("erros") or []:
            L.append(f"    - {e}")
        L.append("    Sugestão: alargar setor, remover filtro de estágio, ou revisar as "
                 "palavras-chave acima.")
    # `plano` já está ligado pelo `if` acima — inclusive a `None`, quando não houve plano.
    exige_ia = bool(plano and plano.exige_sinais_ia)
    for a in ordenar_analises(analises):
        L += _secao(a, exige_sinais_ia=exige_ia)
    L += ["", "=" * 78,
          "  Toda conclusão acima aponta para o documento que a sustenta.",
          "=" * 78]
    return {"briefing": "\n".join(L)}
