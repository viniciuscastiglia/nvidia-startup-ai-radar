"""Passo 2 do pipeline RAG do TAPI: limpeza e normalização do texto.

Módulo separado do chunking de propósito: são passos distintos do pipeline que o TAPI pede,
e separá-los deixa testar um sem o outro. A limpeza é a mesma para os dois formatos de fonte
declarados em `data/nvidia/fontes.yaml`, mas cada um tem um tipo de sujeira diferente:

- **HTML** carrega menu residual e call-to-action. O filtro de linhas curtas mata isso.
- **Markdown do GitHub** carrega badge de build, comentário HTML e tag solta no meio do
  texto. Não carrega menu — por isso o filtro de linhas curtas NÃO é aplicado nele: numa
  fonte já limpa, ele só destruiria linha de tabela e item curto de lista.

Aplicar a limpeza errada ao formato errado tira conteúdo, e conteúdo que sai aqui nunca mais
volta — o embedding não sabe o que não viu.
"""

from __future__ import annotations

import re

# Tags que não são conteúdo. Somem antes de qualquer extração.
RUIDO_HTML = ["script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg"]


# BOILERPLATE QUE SOBREVIVE AO FILTRO DE LINHAS CURTAS, PORQUE TEM FORMA DE PROSA (D-082).
#
# `limpar_linhas` mata menu residual por TAMANHO — funciona para "Get Started", "Products".
# Não alcança banner de consentimento, formulário de sessão e vazamento de widget de CMS, que
# vêm em frases longas e pontuadas. Achado rodando o grafo em 02/09: o chunk 324 (NVIDIA
# Healthcare) era 272 tokens de markup de um chatbot da Adobe, indexado e recuperável, e o
# chunk 15 (Inception) era formulário de manutenção. Isso chegava ao briefing como
# `justificativa_tecnica` — o primeiro campo que o gerente lê.
#
# É lista de marcadores, não regra geral, e isso é deliberado: cada entrada foi OBSERVADA no
# corpus real, como `RUIDO_HTML` e como a heurística de linhas curtas. Uma regra genérica que
# pegasse isto pegaria conteúdo junto — e o docstring do módulo avisa que conteúdo que sai aqui
# nunca mais volta.
RUIDO_FRASE = (
    # sessão e formulário (visto em Inception, AI Enterprise, Healthcare)
    "not you?", "clear form", "welcome back.", "log out", "wcm mode cookie",
    "your privacy choices", "please share your contact details",
    # vazamento de CMS/widget — instrução para quem MONTA a página, não para quem a lê
    # (visto em Healthcare: markup do assistente da Adobe embutido no HTML)
    "aem https", "inject web client", "fab button", "modal backdrop", "chat modal",
    "see console for details", "before bc initializes", "powered by adobe",
    "close button (external",
)


def descartar_boilerplate(texto: str) -> str:
    """Tira as linhas de `RUIDO_FRASE` e as réguas de `=` que separam blocos de widget.

    Opera por LINHA, nunca por chunk, e a razão é medida: dos 7 chunks que casavam
    "cookie|Sign In|Apply Now" em 02/09, só 3 eram entulho. Um filtro por chunk teria apagado
    o chunk 1 — *"Inception is a free program that guides AI startups…"* —, que é conteúdo bom
    e é fonte provável da q11 do gabarito. **A sujeira é a linha, não o chunk.**
    """
    saida = []
    for linha in texto.split("\n"):
        baixo = linha.strip().lower()
        if any(m in baixo for m in RUIDO_FRASE):
            continue
        # Régua de separação de bloco de widget: `====================`. RUN consecutivo, e não
        # contagem total — a primeira versão usava `count("=") >= 8` e pegava, por acidente, uma
        # URL cheia de parâmetros. Regra que acerta pelo motivo errado quebra na próxima página.
        if "=" * 8 in baixo:
            continue
        # Bloco de comentário de CSS/JS que vazou para o texto. Só no caminho HTML isto é seguro:
        # o extrator devolve `<li>` como texto sem bullet, então linha aberta por `*` não é lista
        # — é `* @author vpanapaku`, `* NV-breadcrumb component template.` (NVIDIA Healthcare).
        if baixo.startswith("*"):
            continue
        # Markup que sobreviveu à remoção de tags: no corpus real sobra CTA inteiro
        # (`<center><a href="…" class="cta--scnd">See All</a></center>`, CUDA Toolkit). Linha com
        # atributo de HTML é marcação, não conteúdo — o texto útil dela já foi extraído antes.
        if "<a href" in baixo or "<center" in baixo or 'class="' in baixo:
            continue
        saida.append(linha)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(saida)).strip()


def limpar_linhas(texto: str) -> str:
    """Descarta linha de uma ou duas palavras que não termina em pontuação.

    É a heurística de menu residual: depois de remover `nav` e `footer`, ainda sobram
    fragmentos como "Get Started", "Learn More", "Products" soltos entre parágrafos. Uma
    frase de conteúdo raramente tem duas palavras; um item de menu quase sempre tem.

    A exceção da pontuação existe para não comer frase curta legítima ("Deploy anywhere.").

    SÓ PARA HTML. Ver o docstring do módulo.
    """
    linhas = [ln.strip() for ln in texto.split("\n")]
    linhas = [ln for ln in linhas if len(ln.split()) > 2 or ln.endswith((".", "!", "?", ":"))]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(linhas)).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Markdown
# ─────────────────────────────────────────────────────────────────────────────

_COMENTARIO_HTML = re.compile(r"<!--.*?-->", re.DOTALL)
_TAG_HEADING = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.DOTALL | re.IGNORECASE)
_TAG_QUALQUER = re.compile(r"<[^>]+>")
_IMAGEM_LINK = re.compile(r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)")   # badge clicável
_IMAGEM = re.compile(r"!\[[^\]]*\]\([^)]*\)")                     # imagem solta
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")                      # [texto](url) -> texto


def normalizar_markdown(texto: str) -> str:
    """Tira do markdown o que não é conteúdo, preservando estrutura e código.

    O que sai e por quê, tudo observado no corpus real (README do TensorRT-LLM, do
    NeMo-Guardrails, do cuDF e do cuML):

    - **Badges** (`[![Documentation](...)](...)`) — são imagem, viram texto vazio ou ruído.
      O README do TensorRT-LLM abre com uma fileira deles.
    - **Comentário HTML** — invisível para o leitor, visível para o embedder.
    - **Tag HTML solta** — os READMEs da NVIDIA misturam `<div align="center">` e `<h4>` com
      markdown. As de heading viram ATX (senão a seção que elas abrem desaparece da árvore);
      as demais somem, preservando o texto de dentro.
    - **URL de link** — `[TensorRT-LLM](https://...)` vira `TensorRT-LLM`. A URL não ajuda a
      recuperação e ocupa tokens; a citação já guarda `documento_url` separado.

    O que FICA, de propósito: blocos de código. `docker run nvcr.io/nim/...` é exatamente o
    tipo de trecho concreto que faz a justificativa técnica da recomendação não ser genérica.
    """
    texto = _COMENTARIO_HTML.sub("", texto)
    # Heading em tag HTML vira ATX ANTES da remoção geral de tags, senão perde-se a seção.
    texto = _TAG_HEADING.sub(lambda m: f"\n{'#' * int(m.group(1))} {m.group(2).strip()}\n", texto)
    texto = _IMAGEM_LINK.sub("", texto)
    texto = _IMAGEM.sub("", texto)
    texto = _LINK.sub(r"\1", texto)
    texto = _TAG_QUALQUER.sub("", texto)

    # Linhas que sobraram vazias ou só com pontuação de badge
    linhas = [ln.rstrip() for ln in texto.split("\n")]
    linhas = [ln for ln in linhas if ln.strip() not in ("", "|", "-", "·") or ln == ""]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(linhas)).strip()
