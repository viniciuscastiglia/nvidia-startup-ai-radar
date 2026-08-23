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
