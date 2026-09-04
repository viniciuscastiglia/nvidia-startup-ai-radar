"""Evidence Validator — as afirmações têm evidência e fonte suficientes?

NÃO É STUB. As cinco regras de `contexto/02` §6 são lógica pura — contam tipos de documento e
olham data de publicação. Não precisam de LLM, e implementá-las de verdade hoje custa 40 linhas.

AS REGRAS, E ONDE CADA UMA ESTÁ NO CÓDIGO
------------------------------------------
1. Toda conclusão aponta para ao menos um documento          -> `sem evidência -> validada=False`
2. Corroboração entre TIPOS diferentes vale mais que repetir
   o mesmo tipo                                              -> `len(tipos_de_fonte)`
3. Documento antigo vale menos                               -> `_recente()`, janela de 24 meses
4. Ausência de sinal != sinal negativo                       -> nada é DELETADO, só rebaixado
5. O output carrega a confiança, não só o rótulo             -> `confianca` em toda `Afirmacao`,
                                                                e `confianca` + `motivo_confianca`
                                                                no `Diagnostico` (D-059)

A regra 4 é a que separa este agente de um filtro. Ver D-010: quem barra é o Recommendation.
"""

from __future__ import annotations

from datetime import date
from time import perf_counter as _perf

from src.state import Afirmacao, Confianca, DorObservada, EstadoAnalise

JANELA_MESES = 24

# O DEFAULT É `False`, E ISSO É RESULTADO DE MEDIÇÃO (D-059) — mesmo destino de `USAR_JUIZ_LLM`.
#
# D-058 fixou o alvo ANTES de medir: a confiança do diagnóstico precisava bater o classificador
# TRIVIAL, que responde "alta" para todo mundo e faz 3/8 (37,5%). O piso escrito era >= 4 acertos
# absolutos e taxa >= 50%.
#
# Medido em 27/08 sobre as 8 fixtures: **2/6, ou 33%**. Sobe de 0/6 — o defeito estrutural some,
# `alta` volta a ser alcançável e a Axenya e a RD Station passam a acertar — mas **continua
# perdendo de uma constante**. Pela regra, não entra em produção.
#
# O QUE A MEDIÇÃO MOSTROU, e é mais útil que o número: os erros que sobram não são do validator.
# A Doutor-AI recebe `baixa` porque o Classifier lhe anexou UMA evidência, vinda de um `release`
# sem data; a SunnyHUB recebe `baixa` porque não lhe anexou nenhuma. O validator está relatando
# fielmente a espessura da evidência que o Classifier produziu. O gargalo mudou de lugar.
#
# `avaliar_agentes.py --confianca-diagnostico` liga.
CONFIANCA_DA_EVIDENCIA_DO_DIAGNOSTICO = False


# JULGAMENTO DE SUSTENTAÇÃO — o critério está em D-074, fixado ANTES deste código.
#
# O DEFEITO, medido em 31/08 e não suposto: as cinco regras acima medem a ESPESSURA da evidência
# — quantos tipos de documento corroboram, quão recente. Nenhuma olha o salto da evidência para a
# conclusão. Resultado: das 10 dores que o gabarito PROÍBE, este agente barrava **zero**, e a
# confiança de uma dor errada era indistinguível da de uma certa (erradas: 4 baixa/4 media/2 alta;
# certas: 4/5/3). A frase "monitoramento do sistema fotovoltaico" é fonte impecável — real,
# literal, datada — para a conclusão errada de que uma empresa de energia solar tem dor de
# observabilidade DE IA.
#
# NÃO CONTRADIZER NÃO É SUSTENTAR. As 10 erradas não são CONTRADITAS pela evidência: são NEUTRAS
# em relação a ela. Uma checagem de contradição pegaria zero. A que funciona pergunta o oposto —
# "a evidência SUSTENTA?" —, e é o irmão de D-035: lá, relevância não era responsibilidade.
#
# POR QUE AQUI E NÃO NO EXTRACTOR, onde o mesmo julgamento já existe como `USAR_JUIZ_LLM`:
#   1. `validada` era estruturalmente `True` — o único caminho para `False` era "nenhuma
#      evidência", e o Extractor nunca cria dor sem evidência. 34 de 34 passavam. O portão
#      `if d.validada` do `recommendation.py` nunca fechou.
#   2. Põe o desenho de D-010 para operar pela primeira vez: "o Validator anota e rebaixa, quem
#      barra é o Recommendation".
#   3. O juiz do Extractor DELETA o candidato — e D-010 diz, com todas as letras: "ausência de
#      sinal != sinal negativo. Nada é DELETADO, só rebaixado." Julgar aqui é mais coerente com o
#      projeto do que a solução que já estava escrita.
#
# O PROMPT É O DO JUIZ, LITERALMENTE, E ISSO É DECISÃO DE MÉTODO. D-074 passo 2 compara esta
# colocação com a do Extractor (D-072). Se o prompt mudasse, a diferença medida confundiria
# COLOCAÇÃO com PROMPT, e nenhuma das duas ficaria atribuída. Reusar carrega junto as lições
# caras de D-056: critério positivo primeiro, sem "na dúvida reprove", e o motivo tem que citar
# a frase julgada.
#
# `confianca` e `validada` continuam ORTOGONAIS de propósito: a fonte pode ser excelente (`alta`)
# e mesmo assim não sustentar a afirmação (`validada=False`). Fundir as duas apagaria justamente
# a distinção que motivou esta decisão.
#
# `avaliar_agentes.py --sustentacao` liga.
JULGAR_SUSTENTACAO = False


def _recente(quando: date | None, hoje: date | None = None) -> bool:
    """Sem data conta como não-recente: não dá para afirmar frescor que não se conhece."""
    if quando is None:
        return False
    hoje = hoje or date.today()
    return (hoje.year - quando.year) * 12 + (hoje.month - quando.month) < JANELA_MESES


def avaliar(afirmacao: Afirmacao) -> tuple[Confianca, bool, str]:
    if not afirmacao.evidencias:
        return "baixa", False, "regra 1: nenhuma evidência aponta para um documento da base"

    tipos = afirmacao.tipos_de_fonte
    n_recentes = sum(1 for e in afirmacao.evidencias if _recente(e.data_publicacao))

    if len(tipos) >= 2 and n_recentes >= 1:
        return "alta", True, (
            f"regra 2: corroborada por {len(tipos)} tipos de documento ({', '.join(sorted(tipos))}), "
            f"{n_recentes} recente(s)"
        )
    if len(tipos) >= 2:
        return "media", True, (
            f"regra 2 atendida ({len(tipos)} tipos), mas regra 3 rebaixa: "
            f"nenhum documento dentro da janela de {JANELA_MESES} meses"
        )
    if n_recentes >= 1:
        return "media", True, (
            f"documento recente, mas de um tipo só ({', '.join(tipos)}) — sem corroboração cruzada"
        )
    return "baixa", True, (
        f"fonte única do tipo {', '.join(tipos)} e fora da janela de {JANELA_MESES} meses"
    )


def sustenta(afirmacao: Afirmacao, empresa: str) -> tuple[bool, str]:
    """A evidência sustenta a afirmação? Ver D-074 e o bloco de `JULGAR_SUSTENTACAO`.

    Escopo: `DorObservada`. É onde o defeito foi medido e é o que D-074 orçou (~34 chamadas por
    execução). As demais afirmações passam sem julgamento, e isso está declarado em vez de
    escondido — ampliar o escopo é decisão nova, com custo novo.
    """
    from src.agents.extractor import CRITERIO_DOR, INSTRUCAO, Julgamento  # sem ciclo: o Extractor
    from src.llm import estruturado                                       # não importa este módulo

    if not isinstance(afirmacao, DorObservada) or not afirmacao.evidencias:
        return True, ""

    numeradas = "\n".join(f"[{i}] {e.trecho}" for i, e in enumerate(afirmacao.evidencias))
    prompt = (f"{INSTRUCAO.format(criterio=CRITERIO_DOR[afirmacao.dor], empresa=empresa)}"
              f"\n\nFRASES:\n{numeradas}")
    # Progresso em tempo real: este braço é SERIAL por construção (uma chamada por dor) e a
    # primeira execução levou ~14 min sem imprimir nada, porque o harness só imprime no fim.
    # Sem isto não há como distinguir "lento" de "pendurado" — e a diferença decide se o
    # problema é orçamento de tempo ou bug. `flush=True` porque a saída é lida ao vivo.
    print(f"    · {empresa[:18]:18s} {afirmacao.dor:24s} "
          f"{len(afirmacao.evidencias)} ev · {len(prompt)} chars ... ", end="", flush=True)
    t0 = _perf()
    try:
        r = estruturado(Julgamento, temperatura=0.0).invoke(prompt)
        print(f"{_perf() - t0:5.1f}s", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"{_perf() - t0:5.1f}s FALHOU {type(exc).__name__}", flush=True)
        # Degradação declarada, igual à do juiz: sem API a afirmação passa e diz que não foi
        # auditada. Invalidar por falha de rede transformaria indisponibilidade em veredito.
        return True, f"sustentação não julgada ({type(exc).__name__})"
    aprovadas = [i for i in dict.fromkeys(r.indices_aprovados) if 0 <= i < len(afirmacao.evidencias)]
    if aprovadas:
        return True, ""
    return False, f"regra 6 (D-074): nenhuma evidência sustenta `{afirmacao.dor}` — {r.motivo}"


def node(state: EstadoAnalise) -> dict:
    perfil = state.get("perfil")
    diagnostico = state.get("diagnostico")
    if perfil is None:
        return {"erros": ["Evidence Validator chamado sem perfil"]}

    for afirmacao in perfil.afirmacoes:
        conf, ok, motivo = avaliar(afirmacao)
        if ok and JULGAR_SUSTENTACAO:
            # A ORDEM IMPORTA: as 5 regras primeiro. Quem já falhou a regra 1 (sem evidência) não
            # tem o que julgar, e gastar chamada nele seria pagar para confirmar o óbvio.
            ok_sust, motivo_sust = sustenta(afirmacao, perfil.nome)
            if not ok_sust:
                ok, motivo = False, motivo_sust
        afirmacao.confianca, afirmacao.validada, afirmacao.motivo_validacao = conf, ok, motivo

    if diagnostico is not None:
        # A CONFIANÇA DO DIAGNÓSTICO SAI DA EVIDÊNCIA DO DIAGNÓSTICO (D-059).
        #
        # Até 27/08 esta linha era `min()` sobre `perfil.afirmacoes` — e essa property inclui
        # TODAS as `dores_observadas`. Com 7 dores na Axenya e 6 na Maritaca, sempre existe um elo
        # fraco, e `alta` era ESTRUTURALMENTE inalcançável: a régua media 0/6, contra 3/8 de um
        # classificador que responde sempre "alta". Pior que impreciso, era constante.
        #
        # E a consequência era perversa na direção errada: um Extractor que achasse MAIS dores
        # reais BAIXAVA a confiança do diagnóstico. A métrica de um agente se movia contra a
        # melhoria de outro.
        #
        # O conjunto certo já estava materializado ao lado: `diagnostico.evidencias` são os trechos
        # que o Classifier anexou porque sustentam o rótulo. A regra 2 de `contexto/02` §6 fala de
        # corroboração entre TIPOS de documento DA CONCLUSÃO; a regra 5 fala do OUTPUT carregar a
        # confiança. As duas falam da evidência da conclusão — nunca de sinais de dor não
        # relacionados. O `min()` sobre o perfil inteiro era uma terceira coisa, herdada do stub da
        # sessão 01 e que ninguém decidiu.
        #
        # `avaliar()` fica intacta e é reusada como está: mesmas 5 regras, mesmo vocabulário, mesmo
        # motivo em texto. O que muda é o CONJUNTO sobre o qual ela é aplicada, não o julgamento.
        if CONFIANCA_DA_EVIDENCIA_DO_DIAGNOSTICO:
            sintetica = Afirmacao(texto=diagnostico.justificativa,
                                  evidencias=diagnostico.evidencias)
            conf, _, motivo = avaliar(sintetica)
            diagnostico.confianca, diagnostico.motivo_confianca = conf, motivo
        else:
            # O comportamento de produção, com o defeito NOMEADO em vez de escondido: `min()` sobre
            # um conjunto que cresce converge para "baixa" por construção, e a régua mede 0/6.
            ordem = {"baixa": 0, "media": 1, "alta": 2}
            confs = [a.confianca for a in perfil.afirmacoes if a.confianca]
            diagnostico.confianca = min(confs, key=lambda c: ordem[c]) if confs else "baixa"
            # O MOTIVO É PREENCHIDO NOS DOIS BRAÇOS, e a primeira versão de D-059 só o preenchia
            # no braço da flag — que é `False` por default. Consequência: o campo novo e a linha
            # nova do briefing eram CÓDIGO MORTO na configuração que roda, e D-059 afirmava
            # "fica em produção, porque não é métrica" sobre algo que não estava em produção.
            # Achado nº 5 do code review de 27/08.
            # O PONTEIRO `ver D-059` SAIU DO TEXTO DO USUÁRIO EM 04/09 (D-100).
            # Ele entrou em 27/08 de propósito, para tornar o defeito visível em vez de
            # escondido — a intenção estava certa e a SUPERFÍCIE estava errada. `motivo_confianca`
            # é impresso no briefing executivo, uma vez por empresa: o gerente de Startups & VCs
            # lia uma referência a uma decisão interna deste repositório, e o vídeo mostrava isso.
            # A regra 5 de `contexto/02` §6 pede que o output carregue a confiança e o motivo
            # dela; ela não pede o número da decisão que discute o motivo. O defeito continua
            # NOMEADO — no bloco de `CONFIANCA_DA_EVIDENCIA_DO_DIAGNOSTICO` acima, que é onde
            # quem mexe no código olha, e em D-059.
            diagnostico.motivo_confianca = (
                f"mínimo sobre as {len(confs)} afirmações do perfil, incluindo "
                f"{len(perfil.dores_observadas)} dor(es) observada(s) — o elo mais fraco decide"
                if confs else "nenhuma afirmação do perfil carrega confiança"
            )

    return {"perfil": perfil, "diagnostico": diagnostico}
