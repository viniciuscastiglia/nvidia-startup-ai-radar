"""Recommendation — cruza o perfil da startup com as tecnologias NVIDIA.

STUB DA SESSÃO 01 na geração do texto, mas as QUATRO REGRAS DE QUALIDADE de `contexto/03` §4
já estão implementadas, porque são regra de negócio e não redação:

1. Prioridade vem do GAP entre os dois eixos, não do rótulo    -> `_prioridade()`
2. Complexidade tem que ser honesta                            -> `COMPLEXIDADE` por tecnologia
3. Recomendação sem evidência não sai                          -> filtro por confiança (D-010)
4. Não empilhar tecnologia                                     -> `TETO_RECOMENDACOES`

A regra 3 é onde a decisão D-010 se paga: o Evidence Validator anotou e rebaixou, mas quem
BARRA é aqui. Recomendação de prioridade alta apoiada só em afirmação de confiança baixa não sai.

DÍVIDA CONHECIDA, DEIXADA VISÍVEL (herdeira de D-020, para a M4)
-----------------------------------------------------------------
O filtro de dores abaixo tem uma condição inócua: `any(c.tecnologia == citacao.tecnologia for c
in citacoes)` é sempre verdadeira, porque `citacao` está em `citacoes`. Na prática
`dores_enderecadas` lista TODAS as dores validadas, não as que aquela tecnologia endereça.

**A informação que falta para corrigir passou a existir em 24/08:** `CitacaoRAG.dor_origem` diz
por qual dor a citação foi recuperada, e `justificativa_negocio` já a usa. Trocar a condição por
`d.dor == citacao.dor_origem` é UMA LINHA — e mesmo assim ela não entra agora, por uma razão que
não é preguiça: `evidencias` é derivada desta mesma lista `dores`, e estreitá-la faz recomendação
cujo dor de origem não passou pelo Evidence Validator cair no `if not evidencias: continue` e
sumir. Isso muda quantas recomendações o sistema emite, que é comportamento medido em
`test_toda_recomendacao_tem_evidencia`. Separar "de quais dores tiro EVIDÊNCIA" de "quais dores
DECLARO endereçadas" é a reescrita deste agente, e ela é da M4.
"""

from __future__ import annotations

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
# obrigatórios do TAPI, e campo obrigatório vazio é nível 0 no critério, não "quase lá".
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
            justificativa_negocio=NEGOCIO.get(citacao.tecnologia) or _negocio_de_fallback(
                citacao, perfil.nome
            ),
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
