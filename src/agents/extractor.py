"""Extractor — texto não estruturado -> perfil estruturado.

O CASADOR DE SUBSTRING FOI REBAIXADO DE DECISOR A GERADOR DE CANDIDATOS (D-053)
--------------------------------------------------------------------------------
Até 25/08 este arquivo era o stub da sessão 01: as listas `SINAIS_*` e `GATILHOS_DOR` casavam
vocabulário de `contexto/02` §5 contra as frases dos documentos, e o que casava virava afirmação.
Elas continuam aqui, e continuam fazendo exatamente o mesmo trabalho — mas o que elas produzem
agora é uma LISTA DE CANDIDATOS, e quem decide é o LLM.

A razão dessa divisão está medida, não argumentada (D-052 e D-053):

  · o casador tem TETO DE RECALL DE 100% no gabarito das 8 fixtures — toda dor esperada tem ao
    menos uma frase candidata. Não há recall a comprar trocando-o por um modelo;
  · e tem PRECISÃO DE 49% — emite dores que o gabarito proíbe em 10 ocasiões, incluindo `custo`
    para uma empresa de energia solar e `dependencia_fornecedor` para a Maritaca AI, esta última
    porque o título da matéria diz "no estilo do ChatGPT".

Recall alto e precisão baixa é a assinatura exata de um bom gerador de candidatos e de um péssimo
decisor. Então ele gera, e o modelo julga.

POR QUE O LLM VÊ AS FRASES E NUNCA OS DOCUMENTOS
--------------------------------------------------
É o que torna impossível inventar citação. `Evidencia.trecho` continua saindo de um recorte por
`str` sobre o documento real; o modelo devolve ÍNDICES das frases que aprova, não texto. É a mesma
disciplina de `indices_citados` em `RespostaRAG` (D-040): *"fazer o modelo devolver índices em vez
de escrever a fonte no texto é o que torna a citação verificável por código"*. Um índice fora da
faixa é erro detectável; uma paráfrase não é.

O efeito colateral é de custo e de qualidade ao mesmo tempo: o contexto por chamada são algumas
frases, e não três páginas — que é o regime em que um modelo de 8b decide bem (D-034 mediu o
julgamento cair por diluição no reranker).

ALTERNATIVAS DESCARTADAS: ver D-053. A curta é: um schema largo que devolvesse o `PerfilStartup`
inteiro viola D-045 e convida paráfrase no campo que sustenta a rastreabilidade do projeto todo.

DEGRADAÇÃO: se a chamada falhar, o candidato é ACEITO e a afirmação registra que não foi julgada.
O catálogo do build.nvidia.com já aposentou modelo duas vezes em três meses; o comportamento sem
API é o de 24/08, que é ruim e conhecido, e não uma exceção que derruba o nó.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from src.llm import estruturado
from src.state import (
    Afirmacao,
    DocumentoRef,
    DorObservada,
    Evidencia,
    EstadoAnalise,
    PerfilStartup,
)

# O DEFAULT É `False`, E ISSO É O RESULTADO DE UMA MEDIÇÃO, NÃO UM ESQUECIMENTO (D-056).
# O critério de empate de D-055 foi escrito ANTES de medir: o juiz precisava bater a precisão de
# dor do casador (49%) por margem >= 0,15 — ou seja, 64%. A faixa em TRÊS execuções é 50–62%, e
# NEM O MELHOR CASO alcança. Pela regra, o juiz não entra em produção. Ele fica ligável, medido e
# defensável; o que ele não tem é o direito de rodar por default sem ter pago o que custa.
# `--juiz` no harness liga.
#
# A FAIXA VEM DE n=3 PORQUE A PRIMEIRA REDAÇÃO DESTE COMENTÁRIO PUBLICOU 58% COM n=1 — o número
# de uma execução só, num projeto cuja própria regra diz que número de geração se reporta em três
# execuções ou não se reporta (D-039, D-040). A instabilidade entre execuções é, ela mesma,
# argumento contra pôr o juiz numa demo ao vivo.
USAR_JUIZ_LLM = False

# Vocabulário de contexto/02 §5. NÃO é mais o decisor: é o gerador de candidatos.
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

# O que cada dor SIGNIFICA para este sistema. Vira prompt, e é o que separa "a palavra apareceu"
# de "a empresa tem esse problema" — a distinção que a régua mediu faltando (D-052).
CRITERIO_DOR: dict[str, str] = {
    "custo": "custo de COMPUTAÇÃO ou de inferência de IA pesando na operação da empresa",
    "latencia": "tempo de resposta de um SISTEMA DE IA sendo um problema para a empresa",
    "escalabilidade": "volume de processamento de IA que a infraestrutura da empresa precisa suportar",
    "governanca": "exigência de compliance, auditoria ou regulação sobre o COMPORTAMENTO DA IA",
    "privacidade": "dado sensível que a empresa processa e que restringe onde a IA pode rodar",
    "avaliacao": "dificuldade de MEDIR a qualidade dos modelos ou agentes da empresa",
    "observabilidade": "falta de instrumentação sobre o SISTEMA DE IA da empresa em produção",
    "dependencia_fornecedor": "a empresa depende de modelo de terceiro (OpenAI, ChatGPT, GPT-4) "
                              "para entregar o próprio produto",
}


class Julgamento(BaseModel):
    """Quais frases sustentam a afirmação, e por quê."""

    indices_aprovados: list[int] = Field(default_factory=list)
    motivo: str = ""


INSTRUCAO = """Você audita frases extraídas do material público da empresa {empresa}.

Uma busca por palavra-chave selecionou as frases abaixo como possíveis evidências de:
  {criterio}

Decida, frase por frase, se ela sustenta isso SOBRE A PRÓPRIA {empresa}.

APROVE a frase quando ela, lida sozinha, afirma isso a respeito da {empresa} — mesmo que de
forma parcial, mesmo que sem detalhe técnico. Evidência parcial é evidência.

REPROVE quando o sujeito da frase for outro (um cliente, um parceiro, um concorrente, o mercado
em geral), quando a palavra-chave estiver ali em outro sentido ou dentro de outra palavra, ou
quando a frase for rótulo de menu, cabeçalho de seção ou título de matéria.

Em motivo, CITE as primeiras palavras de cada frase que você julgou e diga o que decidiu sobre
ela. Se o seu raciocínio reconhecer que uma frase sustenta a afirmação, ela tem que aparecer em
indices_aprovados — não reprove o que você acabou de justificar como válido.

Devolva em indices_aprovados os números das frases aprovadas."""


def frases(doc: DocumentoRef) -> list[str]:
    """Como um documento vira frases citáveis. PÚBLICA desde 27/08 (D-060).

    O Classifier passou a precisar do MESMO recorte para contar profundidade técnica sobre os
    documentos inteiros. Duplicar a regex nos dois módulos criaria duas definições de "trecho
    literal" que divergiriam na primeira vez que uma delas mudasse — e `Evidencia.trecho` só é
    verificável (`avaliar_agentes.py --validar`) enquanto houver uma definição só.
    """
    return [f.strip() for f in re.split(r"(?<=[.!?])\s+|\n+", doc.conteudo_texto) if len(f.strip()) > 40]


def _casar(docs: list[DocumentoRef], termos: list[str], teto: int = 3) -> list[Evidencia]:
    """Devolve CANDIDATOS cujo trecho é a frase literal que contém o termo."""
    achados: list[Evidencia] = []
    for doc in docs:
        for frase in frases(doc):
            baixa = frase.lower()
            if any(t in baixa for t in termos):
                achados.append(Evidencia.de_documento(doc, frase[:400]))
                break          # uma evidência por documento: corroboração vem de docs distintos
    return achados[:teto]


def _julgar(criterio: str, empresa: str, candidatos: list[Evidencia]) -> tuple[list[Evidencia], str]:
    """Filtra os candidatos pelo julgamento do LLM. Ver o docstring do módulo."""
    if not candidatos:
        return [], "nenhum candidato"
    if not USAR_JUIZ_LLM:
        return candidatos, ""

    numeradas = "\n".join(f"[{i}] {e.trecho}" for i, e in enumerate(candidatos))
    try:
        r = estruturado(Julgamento, temperatura=0.0).invoke(
            f"{INSTRUCAO.format(criterio=criterio, empresa=empresa)}\n\nFRASES:\n{numeradas}"
        )
    except Exception as exc:  # noqa: BLE001
        # Degradação declarada: sem API, aceita o candidato e diz que não foi julgado.
        return candidatos, f"não julgado ({type(exc).__name__}) — candidato aceito sem auditoria"
    # Índice fora da faixa é descartado: o modelo aponta, o código valida.
    aprovados = [candidatos[i] for i in dict.fromkeys(r.indices_aprovados) if 0 <= i < len(candidatos)]
    return aprovados, r.motivo


def node(state: EstadoAnalise) -> dict:
    startup = state["startup"]
    docs = startup.documentos
    nome = startup.nome

    def afirmar(texto: str, criterio: str, termos: list[str]) -> Afirmacao | None:
        ev, motivo = _julgar(criterio, nome, _casar(docs, termos))
        return Afirmacao(texto=f"{texto} ({motivo})" if motivo else texto,
                         evidencias=ev) if ev else None

    # ── Eixo copilot/autopilot: os dois lados são julgados antes de comparar ──────────
    # O desempate é `>` e não `>=`, e a razão é CONCEITUAL, não medida: empate não é evidência
    # de autopilot, é ausência de evidência, e o default de um empate não deveria ser o rótulo
    # mais favorável. Medido em 25/08 sobre as 8 fixtures: os dois operadores dão o MESMO placar
    # (classe 3/7, precisão 49%) — a mudança não compra métrica, e dizer o contrário seria
    # inventar um ganho. Muda o rótulo de Freedom AI, Laura Networks e Maritaca AI, que empatam
    # 1x1, 1x1 e 2x2. NÃO muda a RD Station, que é 3x1 e sai autopilot nos dois operadores.
    ev_auto, _ = _julgar("a empresa vende o TRABALHO EXECUTADO / o resultado pronto (autopilot), "
                         "assumindo a operação no lugar do cliente", nome,
                         _casar(docs, SINAIS_AUTOPILOT))
    ev_copi, _ = _julgar("a empresa vende uma FERRAMENTA que o profissional do cliente opera "
                         "(copilot), cobrando por usuário ou por assinatura da plataforma", nome,
                         _casar(docs, SINAIS_COPILOT))
    if ev_auto or ev_copi:
        vende_trabalho = len(ev_auto) > len(ev_copi)
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
        ev, motivo = _julgar(CRITERIO_DOR[dor], nome, _casar(docs, termos, teto=2))
        if ev:
            dores.append(DorObservada(
                dor=dor,
                texto=(f"Sinal de dor em {dor.replace('_', ' ')}"
                       + (f": {motivo}" if motivo else " encontrado nos documentos")),
                evidencias=ev,
            ))

    perfil = PerfilStartup(
        startup_id=startup.startup_id,
        nome=nome,
        proposta_valor=(
            Afirmacao(
                texto=startup.descricao_curta or "",
                evidencias=[Evidencia.de_documento(docs[0], docs[0].conteudo_texto[:400])],
            ) if startup.descricao_curta and docs else None
        ),
        modelo_entrega=modelo_entrega,
        sinais_dado_proprietario=[a for a in [
            afirmar("Indício de dado proprietário alimentando o sistema",
                    "a empresa tem DADO PRÓPRIO gerado pela operação dela, ou modelo treinado por "
                    "ela, alimentando o produto", SINAIS_DADO_PROPRIO)
        ] if a],
        sinais_otimizacao_tecnica=[a for a in [
            afirmar("Indício de profundidade técnica própria na stack de IA",
                    "profundidade TÉCNICA PRÓPRIA em infraestrutura de IA — self-hosting, "
                    "quantização, serving, otimização de inferência, avaliação de modelos",
                    SINAIS_TECNICOS)
        ] if a],
        dores_observadas=dores,
    )
    return {"perfil": perfil}
