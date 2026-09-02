"""Query Planner — consulta em linguagem natural -> critérios de busca.

STUB DA SESSÃO 01: regras, sem LLM. O objetivo hoje é provar que o estado atravessa o grafo
íntegro, não que a extração é boa. A assinatura já é a definitiva: quando o LLM entrar, ele
devolve um `PlanoDeBusca` com `with_structured_output` e nada mais muda.

Os campos espelham o vocabulário do próprio TAPI: "setor, porte, estágio, palavras-chave,
sinais de IA" mais a estratégia de análise.
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
}

ESTAGIOS = ["pre-seed", "pré-seed", "seed", "série a", "serie a", "série b", "serie b"]

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

    plano = PlanoDeBusca(
        consulta_original=consulta,
        setores=setores,
        estagios=estagios,
        palavras_chave=list(dict.fromkeys(palavras)),
        exige_sinais_ia=any(t in baixa for t in ["ia", "inteligência", "inteligencia", "ai", "ml"]),
        max_startups=MAX_STARTUPS,
        estrategia_analise=(
            "Classificar cada empresa pela rubrica AI-native/AI-enabled/non-AI, medir a "
            "maturidade da stack técnica como eixo separado, e priorizar pelo gap entre os dois."
        ),
    )
    return {"plano": plano}
