"""Testes do passo 3 do pipeline RAG. Sem rede: fixtures reproduzem as formas medidas.

AS FIXTURES NÃO SÃO INVENTADAS. Elas imitam as duas formas que a medição de 23/08 achou no
corpus real, porque são elas que o algoritmo tem que resolver:

- `HTML_FRAGMENTADO` — página de produto: muitas seções curtas, headings genéricos que não
  nomeiam produto (`Benefits`, `Models`), conteúdo em `div` que NÃO é irmão do heading.
- `MARKDOWN_DENSO` — README de GitHub: poucas seções enormes, título setext, `<h4>` embutido.

O primeiro teste é o mais importante do arquivo: é a propriedade que motivou D-025 inteira.
"""

from __future__ import annotations

import pytest

from src.rag.chunking import (
    MetaDocumento,
    chunk_estrutural,
    chunk_fixo,
    contar_tokens,
    secoes_de_markdown,
)

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

HTML_FRAGMENTADO = """
<html><body>
  <nav><a href="/">Products</a><a href="/x">Get Started</a></nav>
  <main>
    <h1>NVIDIA NIM Microservices</h1>
    <div><p>Prebuilt containers for deploying models anywhere on accelerated infrastructure.
      Each container packages the model together with an optimized inference engine, a standard
      API and every runtime dependency, so that a deployment that used to take weeks of tuning
      now takes minutes. The engine underneath may be TensorRT-LLM, vLLM or SGLang, chosen per
      model, and the container runs unchanged on cloud, data center or workstation.</p></div>
    <h2>Enterprise Generative AI That Does More for Less</h2>
    <section>
      <h3>Benefits</h3>
      <div><p>Reduce total cost of ownership with high-throughput inference serving.</p></div>
      <h3>Models</h3>
      <div><p>Support for Llama, Mistral, and hundreds of other open models out of the box.</p></div>
      <h3>Performance and Scale</h3>
      <div><p>Improve TCO with low-latency inference that scales across Kubernetes clusters.</p></div>
    </section>
    <h2>Boost Throughput</h2>
    <div><p>Llama 3.1 8B on H100 reaches 1201 tokens per second against 613 of baseline.</p></div>
    <footer>Copyright NVIDIA</footer>
  </main>
</body></html>
"""

MARKDOWN_DENSO = """
<div align="center">

TensorRT LLM
============

<h4>Optimizes inference for large language models on NVIDIA GPUs.</h4>

[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen.svg)](https://nvidia.github.io/TensorRT-LLM/)

</div>

<!-- este comentario nao deve aparecer no chunk -->

## Quantization

Supported formats include FP8, FP4, INT8 and INT4 with AWQ activation-aware weight quantization.
Each format trades accuracy for memory footprint in a different way, and the right choice
depends on the deployment target and on how much accuracy the application can give up.

- FP8 keeps accuracy closest to the original weights on Hopper and Blackwell hardware.
- INT4 AWQ compresses the most and is the usual choice for memory-bound single-GPU serving.

## Algorithmic Optimizations

Speculative decoding delivers roughly three times the throughput on supported models by
drafting several tokens ahead and verifying them in a single forward pass of the target model.

Paged KV cache and KV cache reuse cut memory pressure when many concurrent requests share a
common prompt prefix, which is the normal shape of a production chat workload.

```bash
docker run nvcr.io/nim/meta/llama-3.1-8b-instruct
```

#### Sub-heading that must not open a section

This line belongs to the Algorithmic Optimizations section, not to a section of its own.
"""

META_HTML = MetaDocumento("NVIDIA NIM", "https://exemplo/nim", "NIM", "html")
META_MD = MetaDocumento("TensorRT-LLM", "https://exemplo/trtllm", "TensorRT-LLM", "markdown")


# ─────────────────────────────────────────────────────────────────────────────
# A propriedade que motivou a estratégia
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("bruto,meta", [(HTML_FRAGMENTADO, META_HTML), (MARKDOWN_DENSO, META_MD)])
def test_todo_chunk_carrega_o_nome_da_tecnologia(bruto, meta):
    """É POR ISTO QUE D-025 EXISTE.

    Sem o caminho prefixado, um chunk cujo heading é `Benefits` ou `Models` não contém a
    palavra "NIM" em lugar nenhum — o BM25 não o recupera pelo nome do produto e o LLM que o
    ler não tem como atribuir a tecnologia. Atribuição é o 7º campo obrigatório do TAPI.
    """
    chunks = chunk_estrutural(bruto, meta)
    assert chunks
    for c in chunks:
        assert meta.tecnologia.lower() in c.texto_indexado.lower(), c.caminho_secao


def test_janela_fixa_perde_a_atribuicao():
    """O contraponto: o braço de controle NÃO tem essa propriedade — e é o ponto dele.

    Sem este teste, "estrutural é melhor" seria afirmação. Com ele, a diferença entre as duas
    estratégias é verificável antes mesmo de medir recall@k.
    """
    chunks = chunk_fixo(HTML_FRAGMENTADO, META_HTML, tamanho=200)
    assert any("NIM" not in c.texto_indexado for c in chunks)


# ─────────────────────────────────────────────────────────────────────────────
# Fundir
# ─────────────────────────────────────────────────────────────────────────────

def test_fundir_junta_irmas_curtas_sob_o_pai_comum():
    chunks = chunk_estrutural(HTML_FRAGMENTADO, META_HTML, piso=60)
    juntou = [c for c in chunks if "Benefits" in c.texto and "Models" in c.texto]
    assert juntou, "seções irmãs curtas deveriam ter sido fundidas"
    assert "Enterprise Generative AI" in juntou[0].caminho_secao, \
        "o breadcrumb do chunk fundido é o caminho do PAI COMUM"


def test_fundir_preserva_o_subtitulo_inline():
    """Fundir quatro irmãs numa só não pode apagar o subtópico de cada uma."""
    chunks = chunk_estrutural(HTML_FRAGMENTADO, META_HTML, piso=60)
    texto = "\n".join(c.texto for c in chunks)
    for subtitulo in ("Benefits", "Models", "Performance and Scale"):
        assert subtitulo in texto


def test_fundir_nao_duplica_nem_perde_conteudo():
    chunks = chunk_estrutural(HTML_FRAGMENTADO, META_HTML)
    juntado = "\n".join(c.texto for c in chunks)
    assert juntado.count("1201 tokens per second") == 1
    for frase in ("Prebuilt containers", "Reduce total cost", "Llama, Mistral"):
        assert frase in juntado


# ─────────────────────────────────────────────────────────────────────────────
# Dividir
# ─────────────────────────────────────────────────────────────────────────────

def test_dividir_respeita_o_teto_do_texto_indexado():
    """O teto vale para o que é EMBEDADO, então inclui o breadcrumb.

    Regressão de um defeito real: dividir por `teto` e prefixar depois produzia chunk de 457
    tokens com teto de 450, medido no corpus real em 23/08.
    """
    teto = 120
    chunks = chunk_estrutural(MARKDOWN_DENSO, META_MD, teto=teto)
    assert chunks
    for c in chunks:
        assert c.n_tokens <= teto, f"{c.n_tokens} > {teto} em {c.caminho_secao}"
        assert c.n_tokens == contar_tokens(c.texto_indexado)


def test_dividir_sobrepoe_um_paragrafo_entre_partes():
    """Sobreposição existe para que uma ideia partida ao meio apareça inteira em algum chunk."""
    partes = [c for c in chunk_estrutural(MARKDOWN_DENSO, META_MD, teto=90)
              if "Algorithmic" in c.caminho_secao]
    assert len(partes) >= 2, "a seção deveria ter sido dividida com este teto"
    assert any(
        any(p.strip() and p.strip() in partes[i + 1].texto
            for p in partes[i].texto.split("\n\n"))
        for i in range(len(partes) - 1)
    ), "nenhum parágrafo se repete entre partes consecutivas"


# ─────────────────────────────────────────────────────────────────────────────
# Parsing
# ─────────────────────────────────────────────────────────────────────────────

def test_markdown_entende_setext_e_h4_embutido():
    """O README do TensorRT-LLM usa os dois. Um parser só de `#` perderia o título inteiro."""
    secoes = secoes_de_markdown(MARKDOWN_DENSO)
    titulos = [s.titulo for s in secoes]
    assert "TensorRT LLM" in titulos, "título setext (====) não foi reconhecido"
    assert "Quantization" in titulos
    # h4 NÃO abre seção — vira corpo, senão viraria um chunk de seis palavras
    assert "Sub-heading that must not open a section" not in titulos
    corpo = "\n".join(s.corpo for s in secoes)
    assert "Sub-heading that must not open a section" in corpo


def test_limpeza_remove_ruido_mas_preserva_codigo():
    chunks = chunk_estrutural(MARKDOWN_DENSO, META_MD)
    tudo = "\n".join(c.texto for c in chunks)
    assert "este comentario nao deve aparecer" not in tudo
    assert "img.shields.io" not in tudo, "badge deveria ter sumido"
    assert "docker run nvcr.io/nim" in tudo, "bloco de código é conteúdo, tem que ficar"


def test_html_ignora_menu_e_rodape():
    chunks = chunk_estrutural(HTML_FRAGMENTADO, META_HTML)
    tudo = "\n".join(c.texto for c in chunks)
    assert "Get Started" not in tudo
    assert "Copyright NVIDIA" not in tudo


def test_documento_sem_heading_nenhum_nao_estoura():
    """Caminho degenerado: cai para divisão por parágrafo, com o nome da tecnologia no caminho."""
    texto = "Um parágrafo qualquer sobre inferência acelerada.\n\nOutro parágrafo distinto."
    chunks = chunk_estrutural(texto, META_MD)
    assert len(chunks) == 1
    assert chunks[0].caminho_secao == "TensorRT-LLM"


# ─────────────────────────────────────────────────────────────────────────────
# Contrato compartilhado pelas duas estratégias
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("fn,estrategia", [(chunk_estrutural, "estrutural-v1"), (chunk_fixo, "fixo-800")])
def test_ordinal_contiguo_e_estrategia_marcada(fn, estrategia):
    """`UNIQUE (estrategia, documento_url, ordinal)` do schema depende das duas coisas."""
    chunks = fn(HTML_FRAGMENTADO, META_HTML)
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    assert {c.estrategia for c in chunks} == {estrategia}
    assert all(c.documento_url == META_HTML.documento_url for c in chunks)
    assert all(c.texto.strip() for c in chunks)
