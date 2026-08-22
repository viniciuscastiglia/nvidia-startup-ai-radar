"""Briefing — relatório final para o gerente de Startups & VCs da NVIDIA.

STUB DA SESSÃO 01 na redação (formata, não gera texto com LLM), mas o FILTRO DE ELEGIBILIDADE
do Inception já é real — ver `elegibilidade()` abaixo. Ele é candidato a Diferencial segundo
`contexto/05` §4.6, e a razão é específica: um sistema que RECUSA recomendar o Inception para
uma consultoria de IA, e explica por quê, demonstra regra de negócio; um que recomenda para
todo mundo demonstra template.

A DISCIPLINA QUE VALE NOTAR: `motivos_exclusao` e `requisitos_nao_verificados` são campos
SEPARADOS. "A base prova que é consultoria" exclui. "A base não prova que tem developer" NÃO
exclui — vira pendência a verificar na conversa. É a mesma regra 4 do Evidence Validator
(ausência de sinal != sinal negativo) aplicada a uma regra de negócio.
"""

from __future__ import annotations

from datetime import date

from src.state import AnaliseStartup, Elegibilidade, EstadoAnalise, EstadoRadar

# Exclusões explícitas do programa (contexto/03 §2).
EXCLUSOES = {
    "consultoria": ["consultoria", "consulting", "desenvolvimento terceirizado", "fábrica de software",
                    "body shop", "outsourcing de ti"],
    "cripto": ["criptomoeda", "cryptocurrency", "blockchain", "token", "web3", "bitcoin"],
    "cloud provider": ["cloud service provider", "provedor de nuvem", "datacenter próprio"],
    "revenda": ["revenda", "distribuidor", "reseller"],
    "capital aberto": ["capital aberto", "listada na b3", "publicly traded", "ipo concluído"],
}
IDADE_MAXIMA = 10   # o programa exige menos de 10 anos de existência


def elegibilidade(analise_startup, perfil) -> Elegibilidade:
    motivos: list[str] = []
    pendentes: list[str] = []
    evidencias = []

    texto = " ".join(
        e.trecho.lower() for a in (perfil.afirmacoes if perfil else []) for e in a.evidencias
    )
    for rotulo, termos in EXCLUSOES.items():
        for termo in termos:
            if termo in texto:
                motivos.append(f"exclusão por '{rotulo}': o termo {termo!r} aparece nos documentos")
                break

    if analise_startup.ano_fundacao:
        idade = date.today().year - analise_startup.ano_fundacao
        if idade >= IDADE_MAXIMA:
            motivos.append(
                f"exclusão por idade: fundada em {analise_startup.ano_fundacao}, {idade} anos "
                f"(o programa exige menos de {IDADE_MAXIMA})"
            )
    else:
        pendentes.append("ano de fundação não consta na base — verificar se tem menos de 10 anos")

    # Requisitos que a base não tem como provar. NÃO excluem — viram pauta da conversa.
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


ROTULO_QUADRANTE = {
    "sweet-spot": "SWEET SPOT — AI-native com stack imatura: melhor prospect",
    "prospect-de-evolucao": "PROSPECT DE EVOLUÇÃO — a conversa é sair do wrapper",
    "ja-otimizada": "JÁ OTIMIZADA — provavelmente já é membro ou já usa NVIDIA",
    "fora-do-funil": "FORA DO FUNIL — não é prospect",
}


def _secao(a: AnaliseStartup) -> list[str]:
    L = [f"\n{'─' * 78}", f"  {a.nome.upper()}", f"{'─' * 78}"]
    if a.erros:
        L.append(f"  [análise incompleta] {'; '.join(a.erros)}")
    if a.diagnostico:
        d = a.diagnostico
        L += [
            f"  Classificação : {d.classe}   (confiança {d.confianca})",
            f"  Stack técnica : maturidade {d.maturidade_stack}",
            f"  Quadrante     : {ROTULO_QUADRANTE.get(d.quadrante, d.quadrante)}",
            f"  Base          : {d.justificativa}",
        ]
    if a.elegibilidade:
        e = a.elegibilidade
        L.append(f"\n  NVIDIA Inception: {'ELEGÍVEL' if e.elegivel else 'NÃO ELEGÍVEL'}")
        for m in e.motivos_exclusao:
            L.append(f"    x {m}")
        for p in e.requisitos_nao_verificados:
            L.append(f"    ? {p}")

    L.append(f"\n  Recomendações ({len(a.recomendacoes)}):")
    if not a.recomendacoes:
        L.append("    nenhuma — sem evidência validada que sustente uma recomendação")
    for i, r in enumerate(a.recomendacoes, 1):
        L += [
            f"\n    {i}. {', '.join(r.tecnologias)}",
            f"       prioridade {r.prioridade} · complexidade {r.complexidade}",
            f"       dores      : {', '.join(r.dores_enderecadas)}",
            f"       técnica    : {r.justificativa_tecnica[:150]}",
            f"       negócio    : {r.justificativa_negocio[:150]}",
            f"       ação       : {r.proxima_acao}",
            f"       evidências : {len(r.evidencias)} trecho(s) com fonte",
        ]
        for ev in r.evidencias[:2]:
            L.append(f"          [{ev.tipo_documento}] {ev.url_fonte}")
            L.append(f"             \"{ev.trecho[:130]}...\"")
        for c in r.citacoes_rag:
            L.append(f"          [base NVIDIA] {c.tecnologia} — {c.url_fonte}")
    return L


def node(state: EstadoRadar) -> dict:
    """Roda no grafo PAI, com `defer=True`: só executa depois de todas as branches."""
    analises = state.get("analises") or []
    ordem = {"alta": 0, "media": 1, "baixa": 2}

    def chave(a: AnaliseStartup):
        pri = min((ordem[r.prioridade] for r in a.recomendacoes), default=3)
        return (pri, a.nome)

    L = [
        "=" * 78,
        "  NVIDIA STARTUP AI RADAR — BRIEFING EXECUTIVO",
        "=" * 78,
        f"  Consulta : {state['consulta']}",
        f"  Data     : {date.today().strftime('%d/%m/%Y')}",
        f"  Empresas : {len(analises)} analisada(s)",
    ]
    if plano := state.get("plano"):
        L.append(f"  Critérios: setores={plano.setores or '—'} · "
                 f"palavras-chave={plano.palavras_chave[:6]}")
    for a in sorted(analises, key=chave):
        L += _secao(a)
    L += ["", "=" * 78,
          "  Toda conclusão acima aponta para o documento que a sustenta.",
          "=" * 78]
    return {"briefing": "\n".join(L)}
