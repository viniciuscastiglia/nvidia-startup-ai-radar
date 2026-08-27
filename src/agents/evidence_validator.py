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

from src.state import Afirmacao, Confianca, EstadoAnalise

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


def node(state: EstadoAnalise) -> dict:
    perfil = state.get("perfil")
    diagnostico = state.get("diagnostico")
    if perfil is None:
        return {"erros": ["Evidence Validator chamado sem perfil"]}

    for afirmacao in perfil.afirmacoes:
        conf, ok, motivo = avaliar(afirmacao)
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
            diagnostico.motivo_confianca = (
                f"mínimo sobre as {len(confs)} afirmações do perfil, incluindo "
                f"{len(perfil.dores_observadas)} dor(es) observada(s) — ver D-059 para por que "
                f"este agregado é o defeito que a régua mede em 0/6"
                if confs else "nenhuma afirmação do perfil carrega confiança"
            )

    return {"perfil": perfil, "diagnostico": diagnostico}
