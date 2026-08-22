"""Estado do grafo e tipos de domínio.

Este é o arquivo mais consequente do projeto: o estado define o que cada agente enxerga e o
que produz. Errar aqui custa refatorar os 8 nós.

TRÊS DECISÕES QUE ESTRUTURAM ESTE ARQUIVO
------------------------------------------

1. EVIDÊNCIA É O ÁTOMO, NÃO UM CAMPO OPCIONAL.
   O TAPI exige duas vezes que "toda conclusão do sistema sobre uma startup precise apontar
   para o documento que a sustenta". Se `evidencias` fosse um campo adicionado no fim, ela não
   sobreviveria ao caminho até o Briefing. Aqui `Afirmacao` — a unidade que os agentes produzem —
   não existe sem `list[Evidencia]`. Rastreabilidade vira propriedade do tipo, não disciplina
   do programador.

2. TYPEDDICT PARA O ESTADO DO GRAFO, PYDANTIC PARA O QUE TRAFEGA DENTRO DELE.
   O estado é TypedDict porque os reducers do LangGraph vivem em `Annotated[...]` e porque um
   nó devolve atualização PARCIAL (`return {"campo": valor}`); com um modelo Pydantic como
   estado, todo nó teria que reconstruir o objeto inteiro.
   Já os payloads são Pydantic porque atravessam a fronteira do LLM: dão structured output,
   validam o que o modelo devolveu, e tornam os 7 campos obrigatórios do TAPI verificáveis
   lendo uma classe em vez de auditando prompt.

3. DOIS ESTADOS, PORQUE A TOPOLOGIA É SUBGRAFO + Send (ver D-007).
   `EstadoRadar` é o grafo pai (uma consulta, N startups). `EstadoAnalise` é o subgrafo
   (uma startup). O fan-in acontece no reducer `operator.add` de `EstadoRadar.analises`.
"""

from __future__ import annotations

import operator
from datetime import date
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# Vocabulário fechado
#
# Literal e não str livre: o LLM devolve exatamente um destes valores ou o Pydantic rejeita.
# É a diferença entre "o classificador respondeu 'meio AI-native'" e um erro de validação
# que o retry_policy do nó consegue tratar.
# ─────────────────────────────────────────────────────────────────────────────

TipoDocumento = Literal["site", "blog", "noticia", "vaga", "perfil_founder", "release"]
Confianca = Literal["alta", "media", "baixa"]
ClasseStartup = Literal["AI-native", "AI-enabled", "non-AI"]
MaturidadeStack = Literal["baixa", "media", "alta"]
Prioridade = Literal["alta", "media", "baixa"]
Complexidade = Literal["baixa", "media", "alta"]

# As OITO dores que o próprio TAPI lista na contextualização (linhas 55-57 do original).
# São a chave de junção com a tabela "dor observável -> tecnologia" de contexto/03 §4.
# Enum fechada e não texto livre: é o que impede o motor de recomendação de virar
# "o LLM achou que combinava".
Dor = Literal[
    "custo",
    "latencia",
    "escalabilidade",
    "governanca",
    "privacidade",
    "avaliacao",
    "observabilidade",
    "dependencia_fornecedor",
]

# Quadrante do modelo de dois eixos (contexto/02 §4). Classificar AI-native NÃO é a mesma
# coisa que qualificar como prospect — a intensidade da recomendação vem do GAP entre
# maturidade AI-native e maturidade de stack.
Quadrante = Literal[
    "sweet-spot",             # AI-native + stack imatura -> melhor prospect
    "prospect-de-evolucao",   # AI-enabled + stack imatura -> conversa é sair do wrapper
    "ja-otimizada",           # AI-native + stack madura -> provável membro do Inception
    "fora-do-funil",          # non-AI
]


# ─────────────────────────────────────────────────────────────────────────────
# O átomo de rastreabilidade
# ─────────────────────────────────────────────────────────────────────────────


class DocumentoRef(BaseModel):
    """Documento recuperado da base. `conteudo_texto` é NÃO ESTRUTURADO de propósito —
    é sobre ele que o Extractor, o Classifier e o Evidence Validator trabalham."""

    documento_id: int
    tipo: TipoDocumento
    titulo: str
    url_fonte: str
    data_publicacao: date | None = None
    conteudo_texto: str


class Evidencia(BaseModel):
    """O span exato que sustenta uma afirmação — não o documento inteiro.

    Guardar o trecho e não só o `documento_id` é o que permite ao briefing citar
    literalmente, e ao avaliador conferir a citação sem abrir o banco.
    """

    documento_id: int
    tipo_documento: TipoDocumento
    url_fonte: str
    trecho: str
    data_publicacao: date | None = None

    @classmethod
    def de_documento(cls, doc: DocumentoRef, trecho: str) -> "Evidencia":
        return cls(
            documento_id=doc.documento_id,
            tipo_documento=doc.tipo,
            url_fonte=doc.url_fonte,
            trecho=trecho,
            data_publicacao=doc.data_publicacao,
        )


class Afirmacao(BaseModel):
    """Nada é afirmado sem lastro.

    Divisão de responsabilidade: o Extractor preenche `texto` e `evidencias`;
    o Evidence Validator preenche `confianca` e `validada`. Por isso os dois últimos
    nascem `None` — `None` significa "ainda não passou pelo validator", que é
    diferente de "passou e ficou baixa".
    """

    texto: str
    evidencias: list[Evidencia] = Field(default_factory=list)
    confianca: Confianca | None = None
    validada: bool | None = None
    motivo_validacao: str | None = None

    @property
    def tipos_de_fonte(self) -> set[TipoDocumento]:
        """Regra 2 de contexto/02 §6: sinal corroborado por dois TIPOS diferentes de
        documento vale mais que sinal repetido no mesmo tipo."""
        return {e.tipo_documento for e in self.evidencias}


class DorObservada(Afirmacao):
    """Uma afirmação categorizada numa das oito dores. É o que o Recommendation consome."""

    dor: Dor


# ─────────────────────────────────────────────────────────────────────────────
# Saídas dos agentes
# ─────────────────────────────────────────────────────────────────────────────


class PlanoDeBusca(BaseModel):
    """Saída do Query Planner. Os campos espelham o vocabulário do próprio TAPI:
    'setor, porte, estágio, palavras-chave, sinais de IA' + a estratégia de análise."""

    consulta_original: str
    setores: list[str] = Field(default_factory=list)
    estagios: list[str] = Field(default_factory=list)
    localizacoes: list[str] = Field(default_factory=list)
    porte_min_time: int | None = None
    porte_max_time: int | None = None
    palavras_chave: list[str] = Field(default_factory=list)
    exige_sinais_ia: bool = True
    max_startups: int = 5
    estrategia_analise: str = ""


class StartupRef(BaseModel):
    """Saída do Retriever: a empresa mais os documentos que serão analisados."""

    startup_id: int
    nome: str
    site: str | None = None
    setor: str | None = None
    estagio: str | None = None
    localizacao: str | None = None
    ano_fundacao: int | None = None
    tamanho_time: int | None = None
    descricao_curta: str | None = None
    documentos: list[DocumentoRef] = Field(default_factory=list)
    score_recuperacao: float = 0.0


class PerfilStartup(BaseModel):
    """Saída do Extractor: texto não estruturado -> perfil estruturado.

    `modelo_entrega` carrega o eixo copilot/autopilot da Sequoia (contexto/02 §1) e
    `dores_observadas` é a ponte para o motor de recomendação.
    """

    startup_id: int
    nome: str
    proposta_valor: Afirmacao | None = None
    modelo_entrega: Afirmacao | None = None
    stack_declarada: list[Afirmacao] = Field(default_factory=list)
    sinais_dado_proprietario: list[Afirmacao] = Field(default_factory=list)
    sinais_otimizacao_tecnica: list[Afirmacao] = Field(default_factory=list)
    dores_observadas: list[DorObservada] = Field(default_factory=list)

    @property
    def afirmacoes(self) -> list[Afirmacao]:
        """Todas as afirmações do perfil, para o Evidence Validator varrer."""
        itens: list[Afirmacao] = [
            *self.stack_declarada,
            *self.sinais_dado_proprietario,
            *self.sinais_otimizacao_tecnica,
            *self.dores_observadas,
        ]
        if self.proposta_valor:
            itens.append(self.proposta_valor)
        if self.modelo_entrega:
            itens.append(self.modelo_entrega)
        return itens


def derivar_quadrante(classe: ClasseStartup, maturidade: MaturidadeStack) -> Quadrante:
    """Torna o modelo de dois eixos executável em vez de decorativo.

    O rótulo que o TAPI pede continua saindo em `Diagnostico.classe`; a PRIORIZAÇÃO da
    recomendação sai daqui. Ver a matriz em contexto/02 §4.
    """
    if classe == "non-AI":
        return "fora-do-funil"
    if maturidade == "alta":
        return "ja-otimizada" if classe == "AI-native" else "prospect-de-evolucao"
    return "sweet-spot" if classe == "AI-native" else "prospect-de-evolucao"


class Diagnostico(BaseModel):
    """Saída do Startup Classifier, com a confiança preenchida pelo Evidence Validator."""

    classe: ClasseStartup
    maturidade_stack: MaturidadeStack
    quadrante: Quadrante
    confianca: Confianca
    justificativa: str
    evidencias: list[Evidencia] = Field(default_factory=list)


class Elegibilidade(BaseModel):
    """Filtro do NVIDIA Inception (contexto/03 §2).

    `motivos_exclusao` e `requisitos_nao_verificados` são campos SEPARADOS pela mesma
    disciplina do Evidence Validator: "a base não prova que tem developer" é diferente de
    "a base prova que é consultoria". Só o segundo exclui.
    """

    elegivel: bool
    motivos_exclusao: list[str] = Field(default_factory=list)
    requisitos_nao_verificados: list[str] = Field(default_factory=list)
    evidencias: list[Evidencia] = Field(default_factory=list)


class CitacaoRAG(BaseModel):
    """Um trecho recuperado da base de conhecimento NVIDIA, com os três scores.

    Guardar denso, lexical e rerank separadamente permite MOSTRAR no vídeo o reranker
    mudando a ordem — e alimenta o harness de avaliação do passo 9 do pipeline RAG.
    """

    tecnologia: str
    trecho: str
    url_fonte: str
    score_denso: float | None = None
    score_lexical: float | None = None
    score_rerank: float | None = None


class Recomendacao(BaseModel):
    """OS 7 CAMPOS OBRIGATÓRIOS DO TAPI, um por atributo (contexto/01, §5.5).

    Escrito assim de propósito: "cumpre o requisito" passa a ser verificável lendo esta
    classe, em vez de auditando o texto que o LLM gerou.
    """

    tecnologias: list[str]                                     # 1
    justificativa_tecnica: str                                 # 2
    justificativa_negocio: str                                 # 3
    prioridade: Prioridade                                     # 4
    complexidade: Complexidade                                 # 5
    proxima_acao: str                                          # 6
    evidencias: list[Evidencia] = Field(default_factory=list)  # 7a — base de startups
    citacoes_rag: list[CitacaoRAG] = Field(default_factory=list)  # 7b — base NVIDIA
    dores_enderecadas: list[Dor] = Field(default_factory=list)


class AnaliseStartup(BaseModel):
    """O resultado completo de UMA startup — o que o subgrafo devolve ao grafo pai.

    Todos os campos de análise são opcionais para que uma falha parcial ainda devolva
    algo útil: com `error_handler` por nó, uma startup com dado ruim vira uma análise
    incompleta com `erros` preenchido, não um run derrubado.
    """

    startup_id: int
    nome: str
    perfil: PerfilStartup | None = None
    diagnostico: Diagnostico | None = None
    elegibilidade: Elegibilidade | None = None
    recomendacoes: list[Recomendacao] = Field(default_factory=list)
    erros: list[str] = Field(default_factory=list)

    @property
    def completa(self) -> bool:
        return bool(self.perfil and self.diagnostico and not self.erros)


# ─────────────────────────────────────────────────────────────────────────────
# Os dois estados do grafo
# ─────────────────────────────────────────────────────────────────────────────


class EstadoAnalise(TypedDict, total=False):
    """Estado do SUBGRAFO — o que a análise de UMA startup enxerga.

    Roda isolado no pytest: basta montar `plano` + `startup` e invocar.
    """

    plano: PlanoDeBusca
    startup: StartupRef
    perfil: PerfilStartup | None
    diagnostico: Diagnostico | None
    elegibilidade: Elegibilidade | None
    citacoes_rag: list[CitacaoRAG]
    recomendacoes: list[Recomendacao]
    erros: Annotated[list[str], operator.add]


class EstadoRadar(TypedDict, total=False):
    """Estado do GRAFO PAI — uma consulta, N startups.

    `analises` é o único campo com reducer de acumulação: é ONDE O FAN-IN ACONTECE.
    Cada branch disparada por `Send` devolve `{"analises": [uma]}` e o `operator.add`
    concatena. Sem esse reducer, a última branch a terminar sobrescreveria as outras.
    """

    consulta: str
    plano: PlanoDeBusca | None
    startups: list[StartupRef]
    analises: Annotated[list[AnaliseStartup], operator.add]
    briefing: str | None
    erros: Annotated[list[str], operator.add]
