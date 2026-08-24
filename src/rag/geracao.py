"""Passo 8 do pipeline RAG do TAPI: geração da resposta com citações. Ver D-035 e D-040.

ESTE PASSO CARREGA A ABSTENÇÃO, E NÃO POR ELEGÂNCIA — POR ELIMINAÇÃO MEDIDA
----------------------------------------------------------------------------
A sessão 02 apostou que um limiar sobre o score denso separaria "não sei". Não separa: margem
−0,2810 com 5 perguntas sem resposta (D-033, atualizado). A sessão 03 apostou que o cross-encoder
resolveria, porque ele julga o par (consulta, passagem) e não só o tópico. Também não: margem
**−17,6328** (D-035). A q23 — *"o TensorRT-LLM é mais rápido que o vLLM?"* — recebe logit +8,53,
um dos mais altos do gabarito inteiro, porque a passagem que cita as duas tecnologias na mesma
frase É altamente relevante. Ela só não contém a comparação.

**Relevância não é responsibilidade.** Distinguir "fala do assunto" de "contém o fato pedido"
exige ler a passagem procurando a coisa específica, e o único componente que lê é este.

O PROMPT TEM UM TRABALHO SÓ, E ELE É NEGATIVO
----------------------------------------------
Um gerador de RAG comum é instruído a responder bem. Este é instruído, antes de tudo, a
RECONHECER QUANDO NÃO DEVE. As passagens que chegam aqui já passaram por recuperação híbrida e
por um cross-encoder: elas são, por construção, altamente relevantes. O erro que este passo existe
para evitar não é "responder com trecho irrelevante" — é **responder com trecho perfeitamente
relevante que não contém o fato**, citando fonte real e inventando só o número.

A CITAÇÃO É POR ÍNDICE, NÃO POR URL ESCRITA NA PROSA
------------------------------------------------------
O modelo devolve `indices_citados`, apontando para posições da lista que ele recebeu. Índice fora
da faixa é erro detectável por código; URL escrita no meio de um parágrafo não é. Rastreabilidade
é requisito duro do TAPI, citado duas vezes — então ela precisa ser verificável, não plausível.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.llm import estruturado
from src.state import CitacaoRAG, RespostaRAG


# ─────────────────────────────────────────────────────────────────────────────
# O QUE O MODELO DEVOLVE ≠ O QUE O PASSO 8 ENTREGA
#
# `RespostaRAG` é o contrato com o resto do sistema e carrega `citacoes:
# list[CitacaoRAG]` — que QUEM MONTA É O CÓDIGO, logo abaixo, a partir da lista que já estava em
# mãos. Mandar aquele schema ao modelo pedia a ele um campo cujo valor seria descartado na linha
# seguinte, e arrastava junto todo o `$defs.CitacaoRAG`.
#
# E arrastava uma coisa pior: **o docstring de uma classe Pydantic vira o `description` do JSON
# Schema, ou seja, vira PROMPT.** O de `RespostaRAG` é prosa de decisão — cita "margem −0,2810",
# "D-021", "D-033 e D-035". Isso não é documentação para quem lê o repositório quando está dentro
# da chamada; é ruído endereçado ao modelo. Medido em 24/08: 2.585 chars de schema por chamada.
#
# Daí este tipo estreito, com docstring curto e escrito PARA O MODELO. A alternativa — manter
# `RespostaRAG` e só encurtar o docstring — resolvia metade e deixava o campo descartado de pé.
# ─────────────────────────────────────────────────────────────────────────────

class SaidaGerador(BaseModel):
    """Resposta a uma pergunta sobre tecnologias NVIDIA, baseada só nos trechos fornecidos."""

    texto: str
    abstencao: bool = False
    motivo_abstencao: str | None = None
    indices_citados: list[int] = Field(default_factory=list)

INSTRUCAO = """Você responde perguntas sobre tecnologias NVIDIA usando APENAS os trechos fornecidos.

REGRA PRINCIPAL, e ela vem antes de qualquer outra:
Se os trechos não contiverem o fato específico que a pergunta pede, defina abstencao=true e
explique em motivo_abstencao o que exatamente falta. Não complete com conhecimento próprio, não
estime, não aproxime, não ofereça um número parecido.

Os trechos que você recebe já foram selecionados por relevância, então eles quase sempre FALAM do
assunto da pergunta. Falar do assunto não é conter a resposta. Exemplos do erro a evitar:
- pergunta pede um preço, o trecho descreve o modelo de licenciamento -> abstencao=true
- pergunta pede uma comparação entre A e B, o trecho cita A e B juntos mas não os compara -> abstencao=true
- pergunta pede um recorte regional, o trecho descreve o programa global -> abstencao=true

ATENÇÃO AO IDIOMA: os trechos estão em inglês e a pergunta vem em português. Traduzir para
comparar faz parte do trabalho. Um termo em inglês que corresponde ao que a pergunta pede CONTA
como resposta encontrada — inclusive quando aparece dentro de uma lista.

Quando os trechos CONTÊM a resposta:
- responda em português, de forma direta e curta
- use apenas informação presente nos trechos
- preencha indices_citados com os números dos trechos que sustentam a resposta
- deixe abstencao=false e motivo_abstencao vazio"""


def formatar(citacoes: list[CitacaoRAG]) -> str:
    """Numera os trechos e prefixa a tecnologia — é a âncora de atribuição do modelo.

    A tecnologia vem de `CitacaoRAG.tecnologia`, que a curadoria fixou no manifesto (D-025), e
    não de um heading do documento. Sem ela, o trecho da q19 pareceria ser sobre TensorRT-LLM.
    """
    return "\n\n".join(
        f"[{i}] ({c.tecnologia}) {c.trecho}" for i, c in enumerate(citacoes)
    )


def gerar(consulta: str, citacoes: list[CitacaoRAG]) -> RespostaRAG:
    """Passo 8. `citacoes` são os top-k já reranqueados — o que for citado é o que foi lido."""
    if not citacoes:
        # Zero passagens não é caso de LLM: não há o que ler. Gastar uma chamada aqui seria
        # pedir ao modelo que decidisse sobre o vazio, que é exatamente onde ele inventaria.
        return RespostaRAG(
            texto="",
            citacoes=[],
            abstencao=True,
            motivo_abstencao="A recuperação não devolveu nenhum trecho para esta consulta.",
        )

    bruta = estruturado(SaidaGerador, temperatura=0.0).invoke(
        f"{INSTRUCAO}\n\nTRECHOS:\n{formatar(citacoes)}\n\nPERGUNTA: {consulta}"
    )

    # O modelo não devolve as citações — ele devolve índices. Quem monta a lista final é o código,
    # e índice fora da faixa é descartado em silêncio no campo mas não na lista: as passagens
    # continuam anexadas para auditoria, ainda que o modelo tenha apontado errado.
    validos = [i for i in (bruta.indices_citados or []) if 0 <= i < len(citacoes)]
    return RespostaRAG(
        texto=bruta.texto,
        citacoes=citacoes,
        abstencao=bruta.abstencao,
        motivo_abstencao=bruta.motivo_abstencao if bruta.abstencao else None,
        indices_citados=validos,
    )
