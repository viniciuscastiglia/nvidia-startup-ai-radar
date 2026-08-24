# Scripts de auditoria da sessão 03

Artefatos da **sessão de revisão de 24/08/2026**, copiados sem alteração do scratchpad em que
foram escritos. Eles produziram os números de `projeto/revisao-03.md`.

**Não são ferramentas mantidas.** Têm caminho absoluto no `sys.path` e assumem
`/Users/viniciustavarescastiglia/case-nvidia`. Estão aqui porque neste projeto medição sem
instrumento é argumento — se um número de `revisao-03.md` for contestado, é aqui que se
reproduz.

| script | o que mede | custa API? |
|---|---|---|
| `idf_auditoria.py` | df e IDF com o tokenizador REAL, em `texto` e em `texto_indexado` | não |
| `idf_lucene_vs_robertson.py` | o IDF que o `bm25s` de fato usa + recall lexical nas duas variantes | não |
| `auditoria_pool.py` | tamanho da união, três pools de rerank com os mesmos logits, posição da âncora | sim |
| `auditoria_diluicao.py` | 4 execuções da curva de D-034 + a variante com texto REAL do corpus | sim |
| `auditoria_lote.py` | o logit muda com a composição do lote? (hipótese testada e DERRUBADA) | sim |
| `auditoria_pipeline.py` | caminhos de `src/rag/pipeline.py` que nunca tinham rodado | sim |
| `auditoria_q17.py` | a âncora da q17 nos pools de produção e do harness | sim |
