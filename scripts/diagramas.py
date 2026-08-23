"""Regenera os diagramas Mermaid do grafo a partir do próprio código (D-019).

POR QUE UM SCRIPT E NÃO GERAR À MÃO UMA VEZ
--------------------------------------------
Diagrama desenhado à mão mente com o tempo — este aqui já tinha ficado desatualizado uma vez,
quando D-023 acrescentou a aresta `retriever -> briefing`. Gerando do grafo compilado, o
diagrama não pode divergir do código: se a topologia mudar e ninguém rodar o script, o diff
do `.mmd` denuncia na próxima execução.

`draw_mermaid()` e não `draw_mermaid_png()`: o PNG chama a API externa mermaid.ink, o que
transforma "gerar a documentação" em dependência de rede. O GitHub renderiza `.mmd`
nativamente, e texto sobrevive a diff.

    python scripts/diagramas.py
"""

from pathlib import Path

from src.graph import SUBGRAFO, construir_grafo

DOCS = Path(__file__).resolve().parent.parent / "docs"

ALVOS = {
    "grafo-pai.mmd": construir_grafo().get_graph(),
    "subgrafo-analise.mmd": SUBGRAFO.get_graph(),
}

for nome, grafo in ALVOS.items():
    destino = DOCS / nome
    antes = destino.read_text(encoding="utf-8") if destino.exists() else ""
    depois = grafo.draw_mermaid()
    destino.write_text(depois, encoding="utf-8")
    print(f"{'atualizado' if antes != depois else 'inalterado'}: docs/{nome}")
