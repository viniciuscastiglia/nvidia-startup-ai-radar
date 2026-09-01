"""Cliente de LLM — a única porta do projeto para chat completions.

POR QUE ESTE ARQUIVO EXISTE, COM UM USUÁRIO SÓ HOJE
-----------------------------------------------------
A convenção do repositório é *"provedor de LLM/embedding/rerank só via `src/config.py`, nenhum
agente conhece a NVIDIA"*. `src/config.py` guarda os DADOS da configuração; falta o lugar que
constrói o cliente a partir deles. Sem este módulo, o primeiro agente da M4 inventaria a
construção e os outros sete copiariam — que é como um provedor vaza para oito arquivos.

`src/rag/geracao.py` é o primeiro usuário. Os oito agentes são os próximos.

POR QUE `method="json_schema"` E NÃO `function_calling`
--------------------------------------------------------
Medido em 24/08, mesmo modelo, mesmo prompt, `temperature=0`, na pergunta-armadilha do gabarito
(q23: *"o TensorRT-LLM é mais rápido que o vLLM? Em quantos por cento?"*, cuja resposta não
existe na base):

    function_calling  ->  abstencao=False, "o TensorRT-LLM é mais rápido que o vLLM em 30%"
    json_mode         ->  não faz parse (o modelo devolve JSON com outro shape)
    json_schema       ->  abstencao=True, "a passagem não fornece informação sobre..."

Três métodos, um modelo, e a diferença entre alucinar um número e abster-se. A leitura provável é
que `function_calling` adiciona pressão para PREENCHER os campos da ferramenta, enquanto o
`json_schema` restringe a decodificação ao schema sem esse viés. Seja qual for a causa, o
comportamento é medido e é ele que manda.
"""

from __future__ import annotations

from typing import TypeVar

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from src.config import LLM

T = TypeVar("T", bound=BaseModel)

METODO_ESTRUTURADO = "json_schema"


def chat(temperatura: float | None = None) -> ChatOpenAI:
    """O cliente cru. `temperature` vem do `.env` (D-002) e pode ser sobrescrita por nó."""
    return ChatOpenAI(
        base_url=LLM.base_url,
        api_key=LLM.api_key,
        model=LLM.modelo,
        temperature=LLM.temperatura if temperatura is None else temperatura,
        timeout=LLM.timeout,
    )


def estruturado(schema: type[T], temperatura: float | None = None):
    """Cliente que devolve `schema` validado pelo Pydantic. Ver o docstring do módulo."""
    return chat(temperatura).with_structured_output(schema, method=METODO_ESTRUTURADO)
