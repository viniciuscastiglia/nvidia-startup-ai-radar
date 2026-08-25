"""Re-embeda o corpus NVIDIA já ingerido, SEM re-baixar nem re-chunkar. Ver D-046.

POR QUE ESTE SCRIPT EXISTE EM VEZ DE `python scripts/ingerir_nvidia.py`
-----------------------------------------------------------------------
Quando o embedder morre (410 Gone — aconteceu em 18/05 e de novo em 25/08/2026), os vetores
guardados em `chunks_nvidia` viram lixo: o espaço vetorial do modelo novo é outro. O corpus,
porém, continua bom.

Rodar o `ingerir_nvidia.py` resolveria — e traria junto um efeito colateral que arruína a
medição. Ele começa no **passo 1**, baixando as 16 URLs do manifesto. As páginas mudam; o
chunker rodaria sobre texto diferente; os `chunk_id` mudariam. O resultado é que
*"os vetores mudaram"* ficaria inseparável de *"o corpus mudou"* — e as âncoras do gabarito,
que são casadas por `documento_url` e por `frase_ancora` dentro do texto, poderiam deixar de
valer em silêncio.

Este script lê `texto_indexado` DO BANCO e faz `UPDATE` só das duas colunas de vetor.
**A única variável que se move é o vetor.** É a mesma disciplina de variável controlada que
D-027 (a estratégia de chunking como coluna) e D-044 (o harness rodando a config de produção)
já codificam.

O QUE ELE EMBEDA, E POR QUE `texto_indexado`
---------------------------------------------
`texto_indexado` = breadcrumb + texto (D-025). É o campo que a ingestão original embedou e o
que o reranker lê (D-038). Embedar `texto` aqui descartaria em silêncio a correção do passo 3
e tornaria os números incomparáveis com os da sessão 02/03.

USO
---
    python scripts/reembedar.py --so-validar   # conta o que faria, zero chamada de API
    python scripts/reembedar.py                # re-embeda tudo
    python scripts/reembedar.py --estrategia estrutural-v1   # só um braço
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx

# Os helpers do passo 4 moram no script que É o passo 4. Importar daqui evita duplicar a
# chamada da API e garante que os dois caminhos (ingestão e re-embed) usem exatamente o mesmo
# payload — `input_type="passage"`, `dimensions=2048`, `truncate="END"`.
from ingerir_nvidia import TAMANHO_LOTE, como_vetor, embedar, truncar

from src.config import EMBEDDING, tem_credencial
from src.db import conectar

SQL_LER = """
SELECT id, estrategia, texto_indexado
FROM chunks_nvidia
{filtro}
ORDER BY estrategia, id
"""

# `coletado_em` NÃO entra neste UPDATE, e isso é a invariante do módulo em forma de SQL:
# ele significa "quando a página-fonte foi buscada", e este script não busca nada. Carimbá-lo
# aqui faria os 381 chunks alegarem terem sido coletados hoje e falsificaria a proveniência de
# que o README e `contexto/04` §3 dependem — exatamente a mistura de variáveis que este script
# existe para impedir. Achado do code review de 25/08.
SQL_ATUALIZAR = """
UPDATE chunks_nvidia
SET embedding = %(embedding)s::vector,
    embedding_bruto = %(embedding_bruto)s::vector
WHERE id = %(id)s
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--so-validar", action="store_true",
                    help="conta os chunks e os lotes sem tocar na API nem no banco")
    ap.add_argument("--estrategia", help="limita a uma estratégia (default: todas)")
    args = ap.parse_args()

    filtro = "WHERE estrategia = %(estrategia)s" if args.estrategia else ""
    params = {"estrategia": args.estrategia} if args.estrategia else {}

    with conectar() as cx, cx.cursor() as cur:
        cur.execute(SQL_LER.format(filtro=filtro), params)
        linhas = cur.fetchall()

    if not linhas:
        print("Nenhum chunk encontrado. Rodou `ingerir_nvidia.py` antes?")
        return 1

    por_estrategia: dict[str, int] = {}
    for linha in linhas:
        por_estrategia[linha["estrategia"]] = por_estrategia.get(linha["estrategia"], 0) + 1

    lotes = sum(-(-n // TAMANHO_LOTE) for n in por_estrategia.values())
    print(f"Modelo: {EMBEDDING.modelo}  ·  dimensão indexada: {EMBEDDING.dimensao}")
    print(f"Chunks: {len(linhas)}  " +
          " · ".join(f"{e}={n}" for e, n in sorted(por_estrategia.items())))
    print(f"Lotes de {TAMANHO_LOTE} -> {lotes} chamadas de API")

    if args.so_validar:
        print("\n--so-validar: nada foi enviado nem gravado.")
        return 0

    if not tem_credencial():
        print("Sem credencial: defina NVIDIA_API_KEY ou LLM_API_KEY no .env")
        return 1

    # Um grupo por estratégia: mantém os lotes homogêneos e o progresso legível.
    t0 = time.perf_counter()
    feitos = 0
    with httpx.Client() as cliente, conectar() as cx:
        for estrategia in sorted(por_estrategia):
            grupo = [linha for linha in linhas if linha["estrategia"] == estrategia]
            print(f"\n  {estrategia} ({len(grupo)} chunks)")
            for i in range(0, len(grupo), TAMANHO_LOTE):
                lote = grupo[i:i + TAMANHO_LOTE]
                vetores = embedar([linha["texto_indexado"] for linha in lote], cliente)

                if len(vetores) != len(lote):
                    print(f"    ERRO: pedi {len(lote)} vetores e vieram {len(vetores)}")
                    return 1

                with cx.cursor() as cur:
                    for linha, bruto in zip(lote, vetores):
                        cur.execute(SQL_ATUALIZAR, {
                            "id": linha["id"],
                            "embedding": como_vetor(truncar(bruto, EMBEDDING.dimensao)),
                            "embedding_bruto": como_vetor(bruto),
                        })
                feitos += len(lote)
                print(f"    lote {i // TAMANHO_LOTE + 1}: {feitos}/{len(linhas)} chunks")

        # UM COMMIT SÓ, no fim, e não por lote. Com commit por lote, uma falha no lote 12 de 24
        # deixaria METADE do corpus no espaço vetorial novo e metade no antigo — e
        # `buscar_denso_bruto` ranqueia os dois juntos sem erro nenhum, devolvendo lixo
        # plausível. Não há coluna que registre qual modelo produziu cada vetor, então nada
        # detectaria o estado misto. Sendo atômico, ou o corpus inteiro migra ou nada migra.
        # Achado do code review de 25/08; a coluna `modelo_embedding` que tornaria o estado
        # misto IMPOSSÍVEL (e não só improvável) fica anotada para a próxima sessão.
        cx.commit()

    print(f"\n{feitos} chunks re-embedados em {time.perf_counter() - t0:.1f}s.")
    print("A régua agora está desatualizada: rode `python scripts/avaliar_rag.py`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
