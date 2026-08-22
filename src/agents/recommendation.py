"""Recommendation — cruza o perfil da startup com as tecnologias NVIDIA.

STUB DA SESSÃO 01 na geração do texto, mas as QUATRO REGRAS DE QUALIDADE de `contexto/03` §4
já estão implementadas, porque são regra de negócio e não redação:

1. Prioridade vem do GAP entre os dois eixos, não do rótulo    -> `_prioridade()`
2. Complexidade tem que ser honesta                            -> `COMPLEXIDADE` por tecnologia
3. Recomendação sem evidência não sai                          -> filtro por confiança (D-010)
4. Não empilhar tecnologia                                     -> `TETO_RECOMENDACOES`

A regra 3 é onde a decisão D-010 se paga: o Evidence Validator anotou e rebaixou, mas quem
BARRA é aqui. Recomendação de prioridade alta apoiada só em afirmação de confiança baixa não sai.
"""

from __future__ import annotations

from src.state import (
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


def _prioridade(quadrante: str, confianca: str) -> Prioridade:
    """Regra 1: a prioridade sai do GAP entre maturidade AI-native e maturidade de stack.

    Regra 3 aplicada junto: confiança baixa nunca vira prioridade alta. A evidência não
    sustenta a urgência, então afirmar urgência seria inventar.
    """
    base: Prioridade = {
        "sweet-spot": "alta",            # AI-native com stack imatura: dor real e iminente
        "prospect-de-evolucao": "media",  # a conversa é sair do wrapper primeiro
        "ja-otimizada": "baixa",          # provavelmente já usa NVIDIA ou já é membro
        "fora-do-funil": "baixa",
    }.get(quadrante, "baixa")
    if confianca == "baixa" and base == "alta":
        return "media"
    return base


def node(state: EstadoAnalise) -> dict:
    perfil, diagnostico = state.get("perfil"), state.get("diagnostico")
    citacoes = state.get("citacoes_rag") or []
    if perfil is None or diagnostico is None:
        return {"recomendacoes": []}

    if diagnostico.classe == "non-AI":
        return {"recomendacoes": []}     # regra 1: non-AI está fora do funil

    recomendacoes: list[Recomendacao] = []
    for citacao in citacoes[:TETO_RECOMENDACOES]:
        # Regra 3: só as dores cuja afirmação passou pelo validator entram.
        dores = [
            d for d in perfil.dores_observadas
            if d.validada and any(c.tecnologia == citacao.tecnologia for c in citacoes)
        ]
        evidencias = [e for d in dores for e in d.evidencias][:3]
        if not evidencias:
            continue

        recomendacoes.append(Recomendacao(
            tecnologias=[citacao.tecnologia],
            justificativa_tecnica=citacao.trecho,
            justificativa_negocio=NEGOCIO.get(citacao.tecnologia, ""),
            prioridade=_prioridade(diagnostico.quadrante, diagnostico.confianca),
            complexidade=COMPLEXIDADE.get(citacao.tecnologia, "media"),
            proxima_acao=(
                f"Agendar conversa técnica sobre {citacao.tecnologia} com o time de engenharia "
                f"da {perfil.nome}, partindo das dores observadas: "
                f"{', '.join(sorted({d.dor for d in dores}))}."
            ),
            evidencias=evidencias,
            citacoes_rag=[citacao],
            dores_enderecadas=sorted({d.dor for d in dores}),
        ))
    return {"recomendacoes": recomendacoes}
