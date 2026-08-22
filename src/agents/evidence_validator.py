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
5. O output carrega a confiança, não só o rótulo             -> `confianca` em toda `Afirmacao`

A regra 4 é a que separa este agente de um filtro. Ver D-010: quem barra é o Recommendation.
"""

from __future__ import annotations

from datetime import date

from src.state import Afirmacao, Confianca, EstadoAnalise

JANELA_MESES = 24


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
        # A confiança do diagnóstico é a da afirmação MAIS FRACA que o sustenta: uma
        # classificação não pode ser mais confiável que o pior elo da sua evidência.
        ordem = {"baixa": 0, "media": 1, "alta": 2}
        confs = [a.confianca for a in perfil.afirmacoes if a.confianca]
        diagnostico.confianca = min(confs, key=lambda c: ordem[c]) if confs else "baixa"

    return {"perfil": perfil, "diagnostico": diagnostico}
