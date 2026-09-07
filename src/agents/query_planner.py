"""Query Planner — consulta em linguagem natural -> critérios de busca + estratégia de análise.

Os campos espelham o vocabulário do próprio TAPI: "setor, porte, estágio, palavras-chave,
sinais de IA" mais a estratégia de análise.

POR QUE REGRAS E NÃO UM LLM, E ISSO É DECISÃO E NÃO TRABALHO INACABADO
-----------------------------------------------------------------------
Este arquivo se declarou "STUB DA SESSÃO 01" até 06/09, e o rótulo passou a ser falso muito
antes disso. Três razões medidas mantêm o casador aqui:

  · **Latência que o usuário sente no primeiro clique.** O planner é o PRIMEIRO nó do grafo.
    Pôr uma chamada de LLM aqui põe a mediana do fornecedor — faixa medida de 17 a 88 s, e uma
    variável de estado, não uma constante (D-080, D-108) — entre apertar "Analisar" e ver
    qualquer coisa acontecer na tela.
  · **Robustez.** O grafo roda hoje com ZERO chamada de LLM em produção, e foi isso que o fez
    sobreviver ao quarto EOL do catálogo em três meses (D-087). O primeiro nó é o pior lugar
    para abrir mão disso: uma falha aqui não degrada o run, ela impede que ele comece.
  · **O trabalho é casamento de vocabulário fechado.** Setor, estágio e dor são enums; o que
    este nó faz é mapear texto livre para elas. É o regime em que uma tabela declarada ganha de
    um modelo, e é auditável — `SETORES` tem teste que garante que toda chave tem empresa.

A assinatura continua sendo a definitiva: quando o LLM entrar, ele devolve um `PlanoDeBusca`
com `with_structured_output` e nada mais muda.

E O PLANNER PASSOU A PLANEJAR DE VERDADE — P-14, D-112
-------------------------------------------------------
Até 06/09 `estrategia_analise` era uma STRING CONSTANTE: o mesmo texto para toda consulta, e
nenhum nó a lia. A arquitetura publicada prometia *"critérios de busca + estratégia de
análise"* e o sistema entregava só a primeira metade. Fazer um nó ler aquela constante teria
satisfeito a letra da P-14 sem mudar nada — um nó lendo uma frase fixa.

Agora a estratégia VARIA com a consulta (`DORES_NA_CONSULTA` abaixo) e o subgrafo AGE sobre
ela: `nvidia_rag.node` ordena as dores da empresa por `dores_prioritarias` antes de consultar a
base NVIDIA, e como `recommendation` corta em 3, a ordem decide qual tecnologia sai.
"""

from __future__ import annotations

import re

from src.config import MAX_STARTUPS
from src.state import EstadoRadar, PlanoDeBusca

SETORES = {
    "saúde": ["saude", "saúde", "health", "hospital", "clinic", "médic", "medic"],
    "fintech": ["fintech", "financ", "banco", "pagament", "crédit", "credit"],
    "agro": ["agro", "agricult", "fazend", "rural"],
    "logística": ["logistic", "logístic", "frete", "transport", "entrega"],
    "jurídico": ["jurídic", "juridic", "legal", "advocac", "contencios"],
    "indústria": ["indústri", "industri", "manufatur", "fábric", "manutenç"],
    "educação": ["educaç", "educac", "ensino", "escola"],
    "varejo": ["varejo", "retail", "e-commerce", "comércio"],
    # OS DOIS SETORES QUE ENTRARAM COM A BASE DE 03/09 (D-090)
    # ---------------------------------------------------------
    # A chave TEM de ocorrer literalmente na coluna `setor`, porque `buscar_startups` filtra
    # com `s.setor ILIKE '%<chave>%'` (ver `_curinga` em src/db.py). É a mesma armadilha que
    # fazia "fintechs" devolver zero, uma casa adiante: setor na base sem chave aqui é
    # empresa que só a busca lexical alcança, e aí "call center" traz qualquer empresa que
    # cite "call". As duas chaves abaixo casam `voz e call center` e
    # `agro — agricultura digital e robótica`, que são os rótulos que a curadoria produziu.
    "voz": ["voz", "call center", "callcenter", "telefon", "transcri", "speech", "ura"],
    "robótica": ["robótic", "robotic", "robô", "robot"],
}

ESTAGIOS = ["pre-seed", "pré-seed", "seed", "série a", "serie a", "série b", "serie b"]

# AS OITO DORES, COMO QUEM OPERA O RADAR AS NOMEIA — P-14, D-112.
#
# POR QUE ESTA TABELA É SEPARADA DE `extractor.GATILHOS_DOR`, e a separação é a decisão:
# as duas casam o mesmo vocabulário fechado e leem textos de naturezas OPOSTAS.
#
#   · `GATILHOS_DOR` lê o MARKETING DA STARTUP, onde a dor aparece de esguelha e quase nunca
#     nomeada — por isso ele é um gerador de candidatos com recall 100% e **precisão 49%**
#     (D-052), e por isso existe um juiz previsto para ele.
#   · esta lê a CONSULTA DO GERENTE, onde nomear a dor É a intenção. Não há candidato a julgar:
#     quem escreve "startups com problema de custo de inferência" está dizendo o que quer.
#
# Compartilhar a tabela custaria os dois lados. Traria para cá `"powered by"`, `"gpt-4"` e
# `"integração com"`, que são assinaturas de dependência no site de uma empresa e ruído numa
# consulta — *"startups que fazem integração com WhatsApp"* viraria `dependencia_fornecedor`.
# E acoplaria o ajuste: mexer nesta lista para melhorar a consulta moveria a precisão de 49%
# que a régua mede, em silêncio.
#
# O EFEITO DE UM FALSO POSITIVO AQUI É PEQUENO E DECLARADO: uma dor a mais na lista só reordena
# as dores que a empresa JÁ TEM. Ela não cria dor, não filtra empresa e não muda diagnóstico.
DORES_NA_CONSULTA: dict[str, list[str]] = {
    "custo": ["custo", "caro", "barato", "gasto", "margem", "cogs", "preço por token"],
    "latencia": ["latência", "latencia", "lento", "lentidão", "tempo de resposta", "tempo real"],
    "escalabilidade": ["escala", "escalar", "escalabilidade", "volume", "carga", "throughput"],
    "governanca": ["governança", "governanca", "compliance", "auditoria", "regulad",
                   "regulament"],
    "privacidade": ["privacidade", "lgpd", "dado sensível", "dados sensíveis", "on-premise",
                    "soberania"],
    "avaliacao": ["avaliação", "avaliacao", "qualidade do modelo", "acurácia", "acuracia",
                  "benchmark"],
    "observabilidade": ["observabilidade", "monitoramento", "monitorar", "telemetria"],
    "dependencia_fornecedor": ["dependência de fornecedor", "dependencia de fornecedor",
                               "wrapper", "vendor lock", "lock-in", "api de terceiro"],
}

# Palavras funcionais que não carregam sinal e só poluem o tsquery.
#
# AS DE DOIS CARACTERES ENTRARAM EM 02/09 (D-081), E ELAS SÃO A CORREÇÃO INTEIRA.
# Antes, o corte era `len(t) > 2` — um filtro de TAMANHO fazendo o trabalho de uma lista de
# stopwords. Funciona para "de"/"em"/"os" e falha exatamente onde dói: **"ia" e "ai" têm dois
# caracteres**, então o radar de startups de IA descartava a palavra "IA" do plano de busca.
# A consulta `"startups de IA"` saía com `palavras_chave=[]`.
# Um filtro de tamanho nunca soube a diferença entre palavra curta e palavra vazia.
VAZIAS = {
    "startups", "startup", "brasileiras", "brasileiro", "brasileira", "brasil", "que",
    "usando", "usam", "usa", "com", "para", "das", "dos", "uma", "empresas", "empresa",
    "quais", "sao", "são", "mais", "sobre", "por", "seu", "sua", "estao", "estão",
    # dois caracteres, sem sinal — o que o corte de tamanho pegava por acidente
    "de", "do", "da", "em", "no", "na", "os", "as", "um", "ao", "se", "ou", "me", "te",
}


def node(state: EstadoRadar) -> dict:
    consulta = state["consulta"]
    baixa = consulta.lower()

    setores = [nome for nome, gatilhos in SETORES.items() if any(g in baixa for g in gatilhos)]
    estagios = [e for e in ESTAGIOS if e in baixa]

    # `> 1` e não `> 2`: o piso agora só descarta fragmento de um caractere; quem decide o que
    # é palavra vazia é `VAZIAS`, que sabe a diferença entre "de" e "ia". Ver D-081.
    termos = [t for t in re.split(r"\W+", baixa, flags=re.UNICODE) if len(t) > 1]
    palavras = [t for t in termos if t not in VAZIAS]
    # O setor detectado entra como palavra-chave também: ele é sinal lexical, não só filtro.
    palavras += [s for s in setores if s not in palavras]

    # A ORDEM DA LISTA É A DA CONSULTA, NÃO A DO DICIONÁRIO — e isso importa, porque é ela que
    # `nvidia_rag` usa para desempatar. Quem escreve "custo e latência" pediu custo primeiro;
    # iterar `DORES_NA_CONSULTA` devolveria a ordem em que EU escrevi o dicionário, que não é
    # informação sobre nada.
    dores = sorted(
        (d for d, gatilhos in DORES_NA_CONSULTA.items() if any(g in baixa for g in gatilhos)),
        key=lambda d: min(baixa.find(g) for g in DORES_NA_CONSULTA[d] if g in baixa),
    )
    exige_ia = any(t in baixa for t in ["ia", "inteligência", "inteligencia", "ai", "ml"])

    plano = PlanoDeBusca(
        consulta_original=consulta,
        setores=setores,
        estagios=estagios,
        palavras_chave=list(dict.fromkeys(palavras)),
        exige_sinais_ia=exige_ia,
        # O estado ganha prioridade sobre a constante do processo — ver `EstadoRadar.max_startups`.
        # `or` e não `if is None`: um `0` vindo da tela não é "sem teto", é entrada inválida, e
        # cair no default é a leitura certa dele.
        max_startups=state.get("max_startups") or MAX_STARTUPS,
        dores_prioritarias=dores,
        estrategia_analise=descrever_estrategia(dores, exige_ia),
    )
    return {"plano": plano}


def descrever_estrategia(dores: list[str], exige_sinais_ia: bool) -> str:
    """A frase que o briefing imprime — DERIVADA do que o subgrafo vai fazer, não fixa (D-112).

    Até 06/09 esta frase era uma constante literal dentro de `node`, idêntica em toda consulta,
    e nenhum nó a lia. Uma "estratégia de análise" que não varia e que ninguém executa é
    decoração com nome de campo.

    Agora ela é o **texto da mesma decisão** que `dores_prioritarias` carrega em dado: o que ela
    afirma é exatamente o que `nvidia_rag.node` faz. Se as duas divergirem, o briefing passa a
    mentir — e é por isso que ela é derivada aqui em vez de escrita à mão em `briefing.py`.

    A cláusula da rubrica fica em toda consulta porque ela é verdade em toda consulta: o
    Classifier e o Evidence Validator rodam sempre, com a mesma régua.
    """
    partes = ["classificar pela rubrica AI-native/AI-enabled/non-AI, medir a maturidade da "
              "stack como eixo separado e priorizar pelo gap entre os dois"]
    if dores:
        partes.append("consultar a base NVIDIA priorizando "
                      f"{', '.join(d.replace('_', ' ') for d in dores)}")
    if exige_sinais_ia:
        partes.append("marcar quem não confirma sinal de IA")
    return "; ".join(partes) + "."
