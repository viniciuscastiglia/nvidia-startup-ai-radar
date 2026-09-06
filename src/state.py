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
    literalmente, e a qualquer leitor conferir a citação sem abrir o banco.
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
    # Preenchido em produção por `avaliar()`, o mesmo caminho que produz `Diagnostico.
    # motivo_confianca` — que D-066 mandou preencher para "o rodapé não mentir". Este ainda não é
    # impresso pelo briefing: é o irmão por-afirmação daquele, e a lacuna é a mesma (P-14).
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
    # SEM CONSUMIDOR (P-14, levantado em 31/08). Este campo, `estrategia_analise`,
    # `StartupRef.score_recuperacao` e `Afirmacao.motivo_validacao` são calculados corretamente e
    # NADA os lê. Não são código morto — são capacidade anunciada e não entregue: a arquitetura
    # publicada diz "Query Planner: critérios de busca + estratégia de análise", e a estratégia é
    # descartada. Apagá-los esconderia a lacuna; ficam anotados, como manda D-020. Ou o subgrafo
    # passa a lê-los, ou o diagrama para de prometê-los — a decisão é P-14.
    exige_sinais_ia: bool = True
    max_startups: int = 5
    estrategia_analise: str = ""   # sem consumidor — P-14

    def discrimina(self) -> bool:
        """Existe ALGUM critério que estreite a base? (D-081)

        Sem nenhum, `SQL_BUSCAR` cai em `tsq = ''` com todos os filtros nulos e devolve os
        `max_startups` primeiros em ordem alfabética — e o briefing os apresenta como
        resultado, sem nada na saída que denuncie a diferença entre isso e um acerto.
        **O modo de falha não era o resultado errado; era o resultado errado indistinguível
        do certo.** Quem chama isto tem de dizer ao usuário quando for `False`.
        """
        return bool(
            self.setores or self.estagios or self.localizacoes or self.palavras_chave
            or self.porte_min_time is not None or self.porte_max_time is not None
        )


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
    score_recuperacao: float = 0.0   # sem consumidor — P-14


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


def derivar_quadrante(
    classe: ClasseStartup, maturidade: MaturidadeStack, sinal_verificado: bool = True
) -> Quadrante:
    """Torna o modelo de dois eixos executável em vez de decorativo.

    O rótulo que o TAPI pede continua saindo em `Diagnostico.classe`; a PRIORIZAÇÃO da
    recomendação sai daqui. Ver a matriz em contexto/02 §4.

    `sinal_verificado` responde à pergunta "o rótulo foi constatado, ou é o silêncio da
    extração?" — que é diferente de "o que oferecer a esta empresa", respondida pela matriz de
    `contexto/02` §4. A matriz continua com quatro células; este parâmetro não acrescenta uma.

    `fora-do-funil` É INALCANÇÁVEL A PARTIR DO CLASSIFIER DE HOJE, E ISSO NÃO É BUG — É O
    ACHADO (D-103). A primeira redação de D-101 dizia *"um `non-AI` CONSTATADO continua fora do
    funil"*, e um code review de 04/09 provou por força bruta sobre o espaço de detectores que
    **esse estado não existe**: o único caminho para `non-AI` em `classifier.node` é
    `pontos == 0`, que é exatamente `sinal_verificado=False`. Logo `classe == "non-AI"` implica
    `not sinal_verificado`, e a linha abaixo nunca dispara vinda do grafo.

    A razão é mais funda que a implementação: **o sistema não tem detector POSITIVO de
    `non-AI`.** A rubrica define a classe por ausência de IA no caminho crítico, e os três
    detectores do Extractor só sabem afirmar presença. Enquanto for assim, `fora-do-funil`
    descreve um caso que este classificador não produz.

    ENTÃO POR QUE O RAMO FICA: `derivar_quadrante` implementa a matriz PUBLICADA em
    `contexto/02` §4, e a célula `non-AI -> fora do funil` faz parte dela. Apagá-la faria a
    função divergir da rubrica que ela existe para executar, e faria o dia em que um detector
    positivo de `non-AI` existir custar uma re-leitura da rubrica em vez de um argumento a mais.
    Fica, com a inalcançabilidade DECLARADA aqui em vez de descoberta por quem ler depois.

    O default `True` mantém o contrato antigo para quem não faz a pergunta nova, e é o que faz
    `tests/test_grafo.py::test_non_ai_nao_recebe_recomendacao` seguir verde sem edição — esse
    teste passou a cobrir a matriz, não o caminho de produção.
    """
    if classe == "non-AI" and not sinal_verificado:
        # AUSÊNCIA DE SINAL NÃO É SINAL NEGATIVO — a regra 4 do Evidence Validator, escrita no
        # dia 2 do projeto e desobedecida aqui até 04/09. `Elegibilidade` já a aplica (`x`
        # provado versus `?` não provado); este era o componente que a contrariava. Sem
        # constatação, a empresa não é declarada fora do funil: ela entra como qualquer outra
        # de sinal fraco, e o briefing diz que o rótulo não foi verificado.
        return "prospect-de-evolucao"
    if classe == "non-AI":
        # INALCANÇÁVEL a partir de `classifier.node` — ver o docstring. É a célula da matriz de
        # `contexto/02` §4 para um `non-AI` CONSTATADO, e nenhum detector de hoje constata isso.
        return "fora-do-funil"
    if maturidade == "alta":
        return "ja-otimizada" if classe == "AI-native" else "prospect-de-evolucao"
    return "sweet-spot" if classe == "AI-native" else "prospect-de-evolucao"


class Diagnostico(BaseModel):
    """Saída do Startup Classifier, com a confiança preenchida pelo Evidence Validator.

    `motivo_confianca` é a regra 5 de `contexto/02` §6 levada a sério: *"o output deve carregar a
    confiança, não só o rótulo"*. `avaliar()` já devolve a frase que explica o grau — qual regra
    decidiu, quantos tipos de documento corroboraram, se algum está dentro da janela — e até 27/08
    essa frase era jogada fora para o diagnóstico, enquanto era guardada para cada `Afirmacao`.
    O briefing imprimia `(confiança baixa)` sem fonte, sob o rodapé que promete o contrário.
    """

    classe: ClasseStartup
    # O PAR QUE `Elegibilidade` JÁ TEM, APLICADO AO RÓTULO (D-101).
    # `Elegibilidade` separa `motivos_exclusao` (a base PROVA) de `requisitos_nao_verificados`
    # (a base NÃO PROVA), e só o primeiro exclui. `classe` não tinha esse par: `non-AI` saía
    # tanto de "constatamos que não há IA no caminho crítico" quanto de "nenhum dos três
    # detectores disparou" — e a rubrica define a classe por uma propriedade POSITIVA, que
    # exige evidência. Medido em 04/09 na base de 30: 9 empresas com zero detector, todas com
    # 2 a 7 dores de IA extraídas com evidência pelo MESMO Extractor.
    # `False` significa: o rótulo é o que a regra produziu, não o que a base constatou.
    sinal_verificado: bool = True
    maturidade_stack: MaturidadeStack
    quadrante: Quadrante
    confianca: Confianca
    justificativa: str
    evidencias: list[Evidencia] = Field(default_factory=list)
    motivo_confianca: str | None = None


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

    # QUAL DOR PUXOU ESTA CITAÇÃO. `None` = "não veio de uma consulta por dor" (o caminho da
    # interface, onde quem pergunta é um humano). O pipeline de RAG NÃO preenche este campo e
    # nem conhece o conceito de dor — quem o preenche é `nvidia_rag`, que é o nó que sabe por
    # qual consulta pediu. É o que mantém D-041 de pé: `src/rag/` continua ignorando o domínio.
    dor_origem: str | None = None


class RespostaRAG(BaseModel):
    """Passo 8 do pipeline do TAPI: a resposta gerada, com citação e com abstenção explícita.

    A ABSTENÇÃO É CAMPO ESTRUTURADO, NÃO PROSA A INTERPRETAR — e isso é decisão (D-040).
    Depois de D-033 e D-035, sabe-se por medição que nenhum limiar sobre score decide "não sei":
    nem a cosseno densa (margem −0,2810) nem o logit do cross-encoder (−17,6328). O único
    componente que consegue distinguir "fala do assunto" de "contém o fato pedido" é o que LÊ a
    passagem. Então a decisão é dele — e ele a declara num booleano, não numa frase que alguém
    depois teria que classificar com regex.

    Mesmo princípio de D-021: campo sem fonte literal vira valor explícito, não valor plausível.

    `indices_citados` aponta para posições de `citacoes`. Fazer o modelo devolver ÍNDICES em vez
    de escrever a fonte no texto é o que torna a citação verificável por código: um índice fora
    da faixa é erro detectável, uma URL escrita na prosa não é.
    """

    texto: str
    citacoes: list[CitacaoRAG] = Field(default_factory=list)
    abstencao: bool = False
    motivo_abstencao: str | None = None
    indices_citados: list[int] = Field(default_factory=list)


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
    algo útil: com `error_handler` por nó do subgrafo (ver `graph.registrar_falha`), a
    etapa que falha registra o erro e salta para o END — o que as etapas ANTERIORES já
    produziram continua no estado. Uma startup com dado ruim vira análise parcial com
    `erros` preenchido, não um buraco no briefing nem um run derrubado.
    """

    startup_id: int
    nome: str
    perfil: PerfilStartup | None = None
    diagnostico: Diagnostico | None = None
    elegibilidade: Elegibilidade | None = None
    recomendacoes: list[Recomendacao] = Field(default_factory=list)
    # POR QUE A CAUSA VIAJA NO ESTADO EM VEZ DE SER INFERIDA NO BRIEFING (D-100).
    # `briefing.py` imprimia a frase fixa "nenhuma — sem evidência validada que sustente uma
    # recomendação" para TODA lista vazia. Medido em 04/09: Conta Simples, Core AI e Iniciador
    # têm 3, 5 e 7 dores VALIDADAS e mesmo assim recebiam essa frase — a causa real era o corte
    # de `non-AI` em `recommendation.py`. O briefing afirmava ao gerente uma causa falsa, sob o
    # rodapé "toda conclusão acima aponta para o documento que a sustenta".
    # Quem sabe a causa é quem decidiu não recomendar; então é ele quem a devolve.
    motivo_sem_recomendacao: str | None = None
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
    motivo_sem_recomendacao: str | None
    erros: Annotated[list[str], operator.add]


class EstadoRadar(TypedDict, total=False):
    """Estado do GRAFO PAI — uma consulta, N startups.

    `analises` é o único campo com reducer de acumulação: é ONDE O FAN-IN ACONTECE.
    Cada branch disparada por `Send` devolve `{"analises": [uma]}` e o `operator.add`
    concatena. Sem esse reducer, a última branch a terminar sobrescreveria as outras.
    """

    consulta: str
    # TETO DE EMPRESAS POR RUN, E NÃO POR PROCESSO (06/09, interface).
    # `config.MAX_STARTUPS` é lido no import, então até aqui o teto era do PROCESSO: mudá-lo
    # exigia editar o `.env` e reiniciar. Quem opera a interface decide por consulta — 3 para
    # olhar rápido, 10 para varrer um setor — e a cena do vídeo PRECISA dele baixo, porque um
    # run completo gasta 2-3 min só no throttle do Cohere (D-068).
    # `None` mantém o contrato antigo: quem não pede nada continua recebendo `MAX_STARTUPS`.
    max_startups: int | None
    plano: PlanoDeBusca | None
    startups: list[StartupRef]
    analises: Annotated[list[AnaliseStartup], operator.add]
    briefing: str | None
    erros: Annotated[list[str], operator.add]
