"""Startup Classifier — AI-native | AI-enabled | non-AI, mais o eixo de maturidade de stack.

STUB DA SESSÃO 01: pontuação a partir dos sinais que o Extractor achou. O LLM vai substituir a
heurística, mas NÃO a estrutura: os dois eixos continuam separados, e o rótulo continua saindo
com as evidências que o sustentam.

POR QUE DOIS EIXOS (contexto/02 §4): classificar AI-native não é a mesma coisa que qualificar
como prospect. Uma AI-native com stack madura provavelmente já é membro do Inception; uma
AI-native com stack imatura é o melhor prospect que existe. O rótulo do TAPI continua sendo
emitido — a priorização vem do gap.
"""

from __future__ import annotations

from src.state import (
    ClasseStartup,
    Diagnostico,
    Evidencia,
    EstadoAnalise,
    MaturidadeStack,
    derivar_quadrante,
)


def node(state: EstadoAnalise) -> dict:
    perfil = state.get("perfil")
    if perfil is None:
        return {"erros": ["Classifier chamado sem perfil"]}

    evidencias: list[Evidencia] = []
    razoes: list[str] = []

    # ── Eixo 1: AI-native vs AI-enabled vs non-AI ────────────────────────────
    pontos = 0
    if perfil.modelo_entrega and "autopilot" in perfil.modelo_entrega.texto.lower():
        pontos += 2
        evidencias += perfil.modelo_entrega.evidencias
        razoes.append("vende resultado (autopilot), não ferramenta")
    elif perfil.modelo_entrega:
        razoes.append("posicionamento de copilot: vende a ferramenta")

    if perfil.sinais_dado_proprietario:
        pontos += 2
        evidencias += perfil.sinais_dado_proprietario[0].evidencias
        razoes.append("indício de dado proprietário alimentando o sistema")

    if perfil.sinais_otimizacao_tecnica:
        pontos += 1
        evidencias += perfil.sinais_otimizacao_tecnica[0].evidencias
        razoes.append("vocabulário técnico de IA presente nos documentos")

    classe: ClasseStartup = "AI-native" if pontos >= 4 else "AI-enabled" if pontos >= 1 else "non-AI"

    # ── Eixo 2: maturidade da stack técnica ──────────────────────────────────
    # Só conta profundidade de INFRAESTRUTURA — self-hosting, quantização, serving, avaliação.
    # Dizer "usamos machine learning" não é maturidade de stack; é uso de IA, que é o eixo 1.
    PROFUNDOS = ["cuda", "gpu", "tensorrt", "triton", "vllm", "quantiz", "self-hosted",
                 "on-premise", "inferência", "latência", "throughput", "mlops", "observabilidade"]
    texto_tecnico = " ".join(
        e.trecho.lower() for a in perfil.sinais_otimizacao_tecnica for e in a.evidencias
    )
    achados = sum(1 for p in PROFUNDOS if p in texto_tecnico)
    maturidade: MaturidadeStack = "alta" if achados >= 3 else "media" if achados >= 1 else "baixa"
    razoes.append(f"{achados} marcador(es) de profundidade de infraestrutura nos documentos")

    return {
        "diagnostico": Diagnostico(
            classe=classe,
            maturidade_stack=maturidade,
            quadrante=derivar_quadrante(classe, maturidade),
            confianca="media",          # provisória: o Evidence Validator decide a definitiva
            justificativa="; ".join(razoes),
            evidencias=evidencias,
        )
    }
