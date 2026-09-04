"""Seleção do trecho que vira `justificativa_tecnica` — P-10 (D-086).

POR QUE ESTE MÓDULO EXISTE, E POR QUE NÃO É UM AGENTE NEM UM PASSO DO RAG
--------------------------------------------------------------------------
Ele é chamado por DOIS nós — `nvidia_rag` (para escolher QUAL passagem de uma mesma página vira
citação) e `recommendation` (para escolher QUAL trecho DENTRO dela vira o campo). Pôr o código em
um dos dois criaria dependência do nó anterior para o posterior; pôr em `src/rag/` violaria D-041,
que mantém o pipeline de recuperação ignorante do domínio — e "justificativa" é vocabulário de
`Recomendacao`, não de recuperação. Fica na camada de agentes, ao lado de quem o usa, sem `node`.

O DEFEITO QUE ELE CONSERTA, MEDIDO EM 02/09
--------------------------------------------
`justificativa_tecnica = citacao.trecho` entregava **o chunk inteiro** — mediana de 803 caracteres —
e o briefing imprimia os 150 primeiros. Logo o que o gerente lia era *o começo do chunk*, que na
estrutura deste corpus é quase sempre um TÍTULO. Das 6 justificativas de um run real, **1 servia**:
as outras foram um case da Writer, um CTA (*"Join our ecosystem…"*), um menu (*"Learn More /
- Documentation / - FAQs"*), um índice de links e prosa institucional.

Isso são DOIS defeitos empilhados, e cada um pede um nível:

  1. **A página escolhida pode ser inteiramente vitrine.** O chunk 81 (NVIDIA NeMo) são quatro
     linhas de case — Writer e Arize — e nenhum recorte interno o salva. Como a deduplicação de
     `nvidia_rag` é por URL e todos os chunks de NeMo compartilham a URL, quem sobrevivia era
     simplesmente o primeiro do reranker. -> nível de PASSAGEM.
  2. **Mesmo na página certa, o campo era o chunk inteiro.** O chunk 127 abre em
     *"Learn More / - Documentation / - FAQs"* e só depois traz o parágrafo real sobre telemetria.
     -> nível de SPAN.

O QUE ESTE MÓDULO NÃO FAZ: DECIDIR RELEVÂNCIA
----------------------------------------------
Quem decide QUAL tecnologia é relevante continua sendo o cross-encoder, que tem régua (`e@k`,
D-068). Esta heurística só decide **qual texto serve de justificativa** — a pergunta que ela sabe
julgar. Trocar um motor medido por uma heurística sem régua seria regressão disfarçada de melhoria.

A RÉGUA VEM ANTES: `data/avaliacao/justificativas.yaml`, 30 chunks de amostra semeada, rotulados
**antes** deste arquivo existir e commitados em separado. A linha trivial é *"os 150 primeiros
caracteres"*, que é o que produção fazia — e ela não é fraca (D-051).
"""

from __future__ import annotations

import re

# Orçamento do span: 2-3 frases. É o tamanho de uma justificativa que alguém lê antes de uma
# reunião — contra os 842 caracteres medianos que o campo carregava. E é maior que os 150 que o
# briefing imprime, de propósito: o campo é o contrato (o TAPI pede o campo), o corte é da vista.
ORCAMENTO = 320
# Abaixo disto não é justificativa, é rótulo. Sem este piso a densidade premia "CUDA | Docker",
# que é tecnicamente denso e não afirma nada.
MINIMO = 80

# MARCADORES TÉCNICOS — nome próprio de produto/biblioteca e termo de engenharia, os dois
# OBSERVADOS no corpus. Termo genérico de todo texto de marketing ("model", "solution",
# "platform", "library") ficou de fora de propósito: ele não separa nada, e uma lista que casa
# em tudo mede o comprimento do texto em vez do conteúdo.
TECNICOS = (
    # produtos e bibliotecas
    "cuda", "tensorrt", "trt-llm", "triton", "pytorch", "jax", "onnx", "vllm", "deepspeed",
    "nim", "nemo", "colang", "monai", "holoscan", "parabricks", "bionemo", "rapids", "cudf",
    "cuml", "cumotion", "morpheus", "riva", "omniverse", "isaac", "dynamo", "nsight", "jetson",
    "blackwell", "hopper", "llama", "nemotron", "deepseek", "hugging face", "bwa-mem", "gatk",
    "deepvariant", "openusd", "cosmos",
    # engenharia
    "docker", "container", "kubernetes", "helm", "conda", "github", "jupyter", "notebook",
    "microservice", "runtime", "inference", "latency", "throughput", "quantiz", "deployment",
    "serving", "benchmark", "checkpoint", "fine-tun", "open-source", "open source", "self-host",
    "on-premises", "kv cache", "dtype", "parallelism", "speculative decoding", "apache license",
    "sdk", "api", "gpu", "asr", "rag", "telemetry",
)

# Número COM unidade ou escala. É o sinal mais forte da amostra — "2.4x more throughput",
# "Over 100x faster", "24,000 tokens per second", "FP8", "180B" — e o que separa afirmação
# verificável de adjetivo. Número solto (um ano, uma contagem de item de menu) não conta.
NUMERO = re.compile(
    r"\b\d[\d.,]*\s*(?:x\b|%|percent\b|gb\b|tb\b|ms\b|tok\b|tokens?\b|tok/sec|gb/s)"
    r"|\b(?:fp|int)\d+\b|\b\d+[bB]\b",
    re.IGNORECASE,
)

# VITRINE — o sujeito é outra empresa. É o defeito nomeado em D-082, e ele tem duas formas no
# corpus: o rótulo explícito ("Success Story") e a forma `Empresa / Título`, que é como as páginas
# da NVIDIA abrem cada case ("Writer / Startup Pens…", "CrowdStrike / Shaping the Future…").
VITRINE = ("success story", "spotlight", "showcase", "customer story", "case study",
           "member story", "success stories")
CABECALHO_DE_CASE = re.compile(r"^[A-Z][\w.&-]*(?: [A-Z][\w.&-]*)? / [A-Z]")

# CONVITE — chamada para ação e rótulo de navegação. Não afirmam nada sobre a tecnologia.
CONVITE = ("learn more", "get started", "getting started", "contact us", "sign up", "join our",
           "join the", "activate your", "apply for", "apply now", "purchase", "watch video",
           "watch on-demand", "read the", "read how", "download the", "explore the", "explore ",
           "see how", "try the", "request a", "talk to", "meet the", "connect with",
           "documentation |", "- documentation", "- examples", "- faqs", "jump-start",
           # ACRESCENTADOS NA ÚNICA REVISÃO DE D-086, e o critério da revisão foi este: só entra
           # marcador que é convite/navegação POR CATEGORIA — não âncora que faria um caso do
           # gabarito passar. Os três vieram de falhas reais: "Learn how to add real-time speech…"
           # (Riva), "Visit Omniverse Legacy Tools…" (Omniverse, e a ferramenta é DEPRECIADA),
           # "Watch NVIDIA Director…" (Morpheus). Alargar as âncoras em vez disto seria ajustar
           # ao gabarito, e as três âncoras que ficaram estreitas continuam contando como erro.
           "learn how", "visit ", "watch ", "for more details",
           # ACRESCENTADOS EM 03/09 (D-097), pelo MESMO critério da revisão de D-086: só entra
           # marcador que é convite/navegação POR CATEGORIA. Os quatro vieram de mobília que saiu
           # IMPRESSA num briefing real — não de casos do gabarito que eu quisesse fazer passar.
           # "feel free to post in the RAPIDS Slack workspace" (cuDF) e "please file an issue on
           # the GitHub issue tracker" são convite de COMUNIDADE, categoria que faltava; e
           # "Quick-Start Guide"/"Download Examples Documentation" são navegação, a mesma
           # categoria de "- documentation", que a lista já tinha.
           "feel free to", "file an issue", "quick-start guide", "download examples")


# FEED DE ANÚNCIOS DENTRO DO README (03/09, D-097)
# --------------------------------------------------
# O README do TensorRT-LLM abre com um mural de novidades — `* [2024/07/09] ✨ …➡️ link` — e ele
# é TECNICAMENTE DENSO: cita TensorRT, LLM, inference, quantization, speculative decoding. A
# densidade de `pontuar()` o premia justamente por isso, e num briefing real saiu
# `📗 DIY notebook: ➡️ link * [2024/05/28] ✨#TensorRT weight stripping` como argumento de venda.
#
# O reconhecimento é por FORMA e não por vocabulário, e essa é a decisão: penalizar as palavras
# do feed exigiria penalizar `inference` e `quantization`, que são o conteúdo que se quer. A
# forma `* [data]` e o emoji decorativo não aparecem em nenhuma prosa técnica deste corpus —
# são a assinatura do mural.
#
# ALTERNATIVA DESCARTADA: limpar o corpus e re-ingerir. Mudaria os 175 chunks e invalidaria o
# gabarito de 24 perguntas do RAG — o mesmo motivo pelo qual D-096 recusou mexer em
# `src/rag/limpeza.py`. Aqui a penalidade é local, reversível e não move um único vetor.
ENTRADA_DE_FEED = re.compile(r"^\*?\s*\[\d{1,4}[/\]]")
EMOJI_DECORATIVO = re.compile(
    "[\U0001F300-\U0001FAFF\u2190-\u21FF\u2600-\u27BF\uFE0F]"
)


def pontuar(texto: str) -> float:
    """Densidade de marcador técnico, por 100 caracteres, menos as penalidades.

    DENSIDADE E NÃO CONTAGEM: um parágrafo institucional longo acumula marcadores por tamanho.
    Dividir pelo comprimento faz uma frase curta e densa ganhar de uma página inteira morna —
    que é exatamente o que se quer de uma justificativa.
    """
    baixo = texto.lower()
    positivos = sum(1 for m in TECNICOS if m in baixo)
    positivos += 2 * len(NUMERO.findall(texto))    # número com unidade vale por dois
    negativos = sum(1 for m in VITRINE if m in baixo) * 3
    negativos += sum(1 for m in CONVITE if m in baixo)
    negativos += 3 * sum(1 for l in texto.split("\n") if CABECALHO_DE_CASE.match(l.strip()))
    # Feed pesa como vitrine (3): as duas são a mesma coisa — página falando de si, não da
    # tecnologia. O emoji pesa 1 por ocorrência, e não mais, porque é sinal e não prova.
    negativos += 3 * sum(1 for l in texto.split("\n") if ENTRADA_DE_FEED.match(l.strip()))
    # EMOJI PESA 2, E O NÚMERO SAI DE UMA CONTAGEM, NÃO DE CALIBRAGEM: dos 175 chunks de
    # produção, **11 têm emoji e os 11 são banner ou mural de README** — 10 do TensorRT-LLM e um
    # do NeMo Guardrails (`✨✨✨ 📌 The official documentation is available at…`). Nenhum é prosa
    # técnica. Peso 1 perdia para a densidade: `✅ Deploy the optimized models with Triton
    # Inference Server` soma 3 marcadores técnicos e é, ainda assim, um item de mural.
    negativos += 2 * len(EMOJI_DECORATIVO.findall(texto))
    return (positivos - negativos) / (len(texto) / 100)


def _spans(texto: str) -> list[str]:
    """Todo bloco de linhas consecutivas com `MINIMO <= tamanho <= ORCAMENTO`.

    A unidade é a LINHA e não a frase porque o corpus vem de HTML e de README limpos, onde cada
    linha já é uma unidade lógica — título, item de lista, parágrafo. Cortar por ponto final
    quebraria `conda create -n rapids-26.08 -c rapidsai` no meio e juntaria título com corpo de
    formas que não existem na página.
    """
    linhas = [l.strip() for l in texto.split("\n") if l.strip()]
    saida = []
    for i in range(len(linhas)):
        for j in range(i, len(linhas)):
            bloco = "\n".join(linhas[i:j + 1])
            if len(bloco) > ORCAMENTO:
                break
            if len(bloco) >= MINIMO:
                saida.append(bloco)
    return saida


def melhor_trecho(texto: str) -> str:
    """O span de maior pontuação. Cai para o texto inteiro truncado quando nada se qualifica.

    O fallback importa: `justificativa_tecnica` é campo obrigatório do TAPI, e um chunk curto
    demais para gerar span não pode produzir campo vazio — um briefing que chega ao gerente com
    esse campo em branco não é "quase lá", é uma recomendação que ele não consegue levar para a
    conversa. Mesmo princípio do fallback de `justificativa_negocio`.
    """
    candidatos = _spans(texto)
    if not candidatos:
        return texto.strip()[:ORCAMENTO]
    return max(candidatos, key=pontuar)
