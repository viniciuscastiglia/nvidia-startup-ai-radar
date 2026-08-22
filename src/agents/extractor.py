"""Extractor — texto não estruturado -> perfil estruturado.

STUB DA SESSÃO 01: em vez de LLM, casa o vocabulário de sinal de `contexto/02` §5 contra as
frases dos documentos. É proposital que o stub produza EVIDÊNCIA REAL — trecho literal do
documento real — porque o que precisa ser provado hoje é que a rastreabilidade sobrevive aos
cinco saltos até o Briefing. Um stub que devolvesse texto inventado não provaria nada.
"""

from __future__ import annotations

import re

from src.state import (
    Afirmacao,
    DocumentoRef,
    DorObservada,
    Evidencia,
    EstadoAnalise,
    PerfilStartup,
)

# Vocabulário de contexto/02 §5. Vira prompt quando o LLM entrar; hoje é o casador.
SINAIS_AUTOPILOT = ["entregamos", "resultado", "assumimos a operação", "força de trabalho",
                    "sla", "por processo", "bpo", "funcionários robôs", "ponta a ponta"]
SINAIS_COPILOT = ["plataforma permite", "ferramenta", "assistente", "por usuário",
                  "por assento", "aumente a produtividade", "nossa plataforma"]
SINAIS_DADO_PROPRIO = ["base própria", "dados exclusivos", "modelo treinado", "nosso dataset",
                       "aprende com cada", "dado proprietário", "tecnologia própria",
                       "modelos próprios", "modelos preditivos"]
SINAIS_TECNICOS = ["cuda", "gpu", "inferência", "latência", "quantização", "fine-tuning",
                   "embedding", "vector database", "rag", "self-hosted", "on-premise",
                   "throughput", "tokens por segundo", "vllm", "tensorrt", "triton", "lora",
                   "mlops", "observabilidade", "eval", "machine learning", "aprendizado de máquina"]

# Cada dor com os termos que a denunciam. É a chave de junção com contexto/03 §4.
GATILHOS_DOR: dict[str, list[str]] = {
    "custo": ["custo", "economia", "reduzir gasto", "sinistralidade", "caro"],
    "latencia": ["latência", "tempo real", "tempo de resposta", "em segundos"],
    "escalabilidade": ["escala", "escalar", "milhões de", "volume", "crescimento"],
    "governanca": ["governança", "compliance", "auditoria", "regulament"],
    "privacidade": ["privacidade", "lgpd", "dados sensíveis", "sigilo", "prontuário"],
    "avaliacao": ["acurácia", "precisão", "validação", "estudo clínico", "evidência científica"],
    "observabilidade": ["monitoramento", "dashboard", "métricas", "observabilidade"],
    "dependencia_fornecedor": ["api da openai", "gpt-4", "chatgpt", "powered by", "integração com"],
}


def _frases(doc: DocumentoRef) -> list[str]:
    return [f.strip() for f in re.split(r"(?<=[.!?])\s+|\n+", doc.conteudo_texto) if len(f.strip()) > 40]


def _casar(docs: list[DocumentoRef], termos: list[str], teto: int = 3) -> list[Evidencia]:
    """Devolve evidências cujo TRECHO é a frase literal que contém o termo."""
    achados: list[Evidencia] = []
    for doc in docs:
        for frase in _frases(doc):
            baixa = frase.lower()
            if any(t in baixa for t in termos):
                achados.append(Evidencia.de_documento(doc, frase[:400]))
                break          # uma evidência por documento: corroboração vem de docs distintos
    return achados[:teto]


def node(state: EstadoAnalise) -> dict:
    startup = state["startup"]
    docs = startup.documentos

    def afirmar(texto: str, termos: list[str]) -> Afirmacao | None:
        ev = _casar(docs, termos)
        return Afirmacao(texto=texto, evidencias=ev) if ev else None

    ev_auto = _casar(docs, SINAIS_AUTOPILOT)
    ev_copi = _casar(docs, SINAIS_COPILOT)
    if ev_auto or ev_copi:
        vende_trabalho = len(ev_auto) >= len(ev_copi)
        modelo_entrega = Afirmacao(
            texto=("Posicionamento de autopilot: vende o resultado/trabalho executado"
                   if vende_trabalho else
                   "Posicionamento de copilot: vende a ferramenta que o profissional opera"),
            evidencias=(ev_auto if vende_trabalho else ev_copi),
        )
    else:
        modelo_entrega = None

    dores: list[DorObservada] = []
    for dor, termos in GATILHOS_DOR.items():
        ev = _casar(docs, termos, teto=2)
        if ev:
            dores.append(DorObservada(
                dor=dor,
                texto=f"Sinal de dor em {dor.replace('_', ' ')} encontrado nos documentos",
                evidencias=ev,
            ))

    perfil = PerfilStartup(
        startup_id=startup.startup_id,
        nome=startup.nome,
        proposta_valor=(
            Afirmacao(
                texto=startup.descricao_curta or "",
                evidencias=[Evidencia.de_documento(docs[0], docs[0].conteudo_texto[:400])],
            ) if startup.descricao_curta and docs else None
        ),
        modelo_entrega=modelo_entrega,
        sinais_dado_proprietario=[a for a in [
            afirmar("Indício de dado proprietário alimentando o sistema", SINAIS_DADO_PROPRIO)
        ] if a],
        sinais_otimizacao_tecnica=[a for a in [
            afirmar("Indício de profundidade técnica própria na stack de IA", SINAIS_TECNICOS)
        ] if a],
        dores_observadas=dores,
    )
    return {"perfil": perfil}
