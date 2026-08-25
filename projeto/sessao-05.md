# Sessão 05 — o segundo EOL, e o chão medido de novo

## Sessão 05 — FECHADA em 25/08/2026

Não era a pauta. Às 09:00Z a NVIDIA aposentou **embedder e reranker** com HTTP 410, e a sessão
virou reconstrução. Ver **D-046** (troca de stack), **D-047** (`json_schema` com n=5) e as notas
datadas em D-013, D-014, D-015, D-034, D-035, D-037, D-038, D-040.

### O que ficou de pé no fim do dia

| verificação | resultado |
|---|---|
| `smoke_nvidia.py` | 3/3 |
| `pytest -q` | **40 passed** |
| `avaliar_rag.py --validar` | 24/24 |
| `avaliar_rag.py` | reproduz a tabela do `CLAUDE.md` linha por linha |
| `python -m src.graph "..."` | ponta a ponta, sem `erros` |

### As quatro coisas que a medição decidiu

1. **Embedder: `llama-nemotron-embed-vl-1b-v2`**, por regra fixada ANTES de medir. O
   `nemotron-3-embed-1b` separa **melhor** (+0,4323 vs +0,3801) e mesmo assim perdeu: 1,14x não
   alcançou o 1,5x exigido para pagar o custo de schema. O empate está escrito em D-046 como o
   motivo, não escondido.
2. **A recuperação MELHOROU com a troca.** O denso puro sozinho já faz r@1 95%, que antes exigia
   o reranker. O ganho do passo 7 migrou do frouxo para o estrito: e@3 de 79% → 95%.
3. **O braço lexical passou a pagar — por uma pergunta.** `rerank_hibrido` bate `rerank_denso` em
   e@5 (100% vs 95%); o controle `--truncar-pool` mostra que vem do pool maior, e o diagnóstico é
   a **q17** (âncora `Evaluator`, que o denso não recupera de jeito nenhum). 1 em 19, só em e@5.
4. **A geração PIOROU: 20–22 de 24**, e a assimetria "nunca alucina" de D-040 está **refutada** —
   a q23 inventou "60%" sob `json_schema`. Nada foi ajustado para recuperar o número.

### Dívida nova: a curva de diluição de D-034 não foi re-medida

A janela do reranker foi (é ~6.958 conjuntos, contra 8.192 do 1B). A **curva de diluição** não —
e é ela que informa a banda de chunk. A faixa de sweep de ~120 a ~560 é do modelo morto. Está
anotado em `src/rag/chunking.py`, no comentário de `TETO_TOKENS`.

---

## Code review de 25/08 — o que foi pago e o que NÃO foi

Rodado com `/code-review high` antes de qualquer commit. Sete achados. **Quatro pagos na hora:**

| # | achado | correção |
|---|---|---|
| 1 | **`.env.example` ainda fixava os quatro modelos mortos** — e `_env()` lê o ambiente antes do default, então quem seguisse o `cp .env.example .env` documentado tomava 410 em tudo | atualizado, e conferido contra o `.env` chave a chave |
| 3 | `verificar_reranker.py` bissecava em `[7000, 8600]`, faixa herdada do 1B — com a janela nova de ~6.958 o guard disparava e o teste **pulava em silêncio**, enquanto o rodapé seguia imprimindo "a janela e 8.192" como conclusão | bracket exponencial, e o rodapé não imprime mais conclusão codificada |
| 4 | `reembedar.py` commitava **por lote**: falha no lote 12 de 24 deixaria metade do corpus num espaço vetorial e metade no outro, e `buscar_denso_bruto` ranquearia os dois juntos sem erro | um commit só, no fim — ou tudo migra ou nada migra |
| 5 | `reembedar.py` carimbava `coletado_em = CURRENT_DATE`, **contradizendo a própria invariante do docstring** ("a única variável que se move é o vetor") e falsificando a proveniência | linha removida — e a data real (2026-08-23, do manifesto e do git) restaurada nos 381 chunks, que a primeira execução já tinha corrompido |

**Três NÃO pagos, porque o plano da sessão excluiu os agentes de propósito.** Ficam aqui porque
produzem saída errada HOJE:

1. **`briefing.py:25` — `"token"` na lista de exclusão de cripto, casado como substring.**
   `SINAIS_TECNICOS` do Extractor inclui `"tokens por segundo"`, então uma frase sobre custo de
   inferência vira evidência e dispara *"exclusão por 'cripto'"*. **Qualquer startup que fale em
   "custo por token" é reportada como NÃO ELEGÍVEL ao Inception pelo motivo errado** — no filtro
   que o projeto chama de diferencial. Precisa de fronteira de palavra e contexto, ou sair.
2. **`briefing.py:36` — `Elegibilidade.evidencias` nasce `[]` e nunca é preenchida**, enquanto os
   motivos afirmam "o termo X aparece nos documentos" e o briefing imprime tudo sob o rodapé
   *"Toda conclusão acima aponta para o documento que a sustenta"*. É a única conclusão do sistema
   sem `list[Evidencia]` — contra a invariante do repositório, e sem teste.
3. **`recommendation.py:135` — o filtro de dores é tautológico** (`any(c.tecnologia == citacao.tecnologia for c in citacoes)` com `citacao ∈ citacoes`). Já documentado como dívida; anotado
   de novo porque afeta dois dos **7 campos obrigatórios** do TAPI.

**Anotado, não pago:** uma coluna `modelo_embedding` em `chunks_nvidia`, conferida contra
`EMBEDDING.modelo` na consulta. O commit atômico torna o estado misto improvável; só a coluna o
torna impossível — inclusive no caso "trocou o `.env` e esqueceu de re-embedar".

---

## Orçamento de API — estourou, e a conta honesta

| bloco | orçado | gasto |
|---|---|---|
| 1 sonda do embedder | ~24 | 7 |
| 2 re-embed (×2, por causa da correção do review) | 25 | 50 |
| 3 janela do reranker | ~15 | 36 |
| 4 ablação | 81 | 81 |
| 4c contingência `--truncar-pool` | 72 | 72 |
| 4d diagnóstico da q17 (**não orçado**) | 0 | 22 |
| 5 `--geracao` × 3 | 243 | 243 |
| 6 métodos com n=5 (inclui ~12 de uma tentativa abortada) | 18 | ~30 |
| 0 smoke | — | 5 |
| **subtotal contado** | **478** | **546** |
| 7 `pytest` ×4 + grafo — **não instrumentado** | ~65 | ~200 est. |
| | **~543** | **~750 est.** |

Quatro causas: o bracket exponencial custou mais que a bissecção estimada; o diagnóstico da q17
não estava no plano e foi adicionado porque escrever "o léxico compra 5 pontos" sem saber qual
pergunta repetiria o erro que a revisão da 03 achou duas vezes; **o `pytest` foi subestimado em
~3x** (o e2e roda o grafo de verdade contra 3 startups); e o re-embed rodou duas vezes.

**Lição para o próximo orçamento:** contar o `pytest` como bloco de API, não como verificação
grátis.

---

## Pauta da próxima sessão

> **Revisto em 25/08, depois de reler o `prompts-de-abertura.md`.** A primeira versão desta pauta
> abria com o fallback local. **Retirado do primeiro lugar**, e o motivo é que o custo de um
> terceiro EOL mudou: o playbook de recuperação agora existe e está provado — `reembedar.py`, a
> sonda de desempate e a janela re-medida fizeram a reconstrução caber em **uma sessão**. O
> fallback transforma "uma sessão de recuperação" em "zero", o que só importa se o EOL cair entre
> 05 e 09/09; e para essa janela o seguro mais barato é **capturar o material de demonstração do
> vídeo antes dela**, porque o eliminatório nº 3 exige *"não executa **E** o vídeo não demonstra
> funcionamento real"* — o **e** é o que protege. O prompt pronto está em
> `prompts-de-abertura.md`, Chat B.

**Aquecimento (~5 min) — o `"token"` de `briefing.py:25`**, em red-green. Uma linha, diagnóstico
fechado, e ele reprova hoje qualquer startup que fale em "custo por token" — inclusive a Axenya,
que a curadoria marcou como prospect de prioridade máxima.

**Bloco 0 — a RÉGUA dos agentes, e ela é bloqueante.** A base tem 3 startups e as 3 são
`perfil_alvo: AI-native`: um classificador que devolvesse "AI-native" incondicionalmente passaria
em 3 de 3. Não há como medir que um Extractor com LLM bate o casador de substring. **O RAG chegou
a nível 4 porque teve régua desde o primeiro dia; os agentes não têm nenhuma** — e escrever o
agente antes da régua é exatamente o erro que a revisão da sessão 03 achou em dois lugares.
Alvo: 6 a 8 fixtures, uma por quadrante de `contexto/02`, com resultado esperado escrito. Não é a
M3 inteira.

**Bloco 1 — o Extractor**, que agora tem contra o que ser medido.

**Bloco 2 — o fallback local** (Opção B do plano da 05). Embedder e cross-encoder em processo,
atrás da costura de `src/config.py`, NVIDIA como primário. É a defesa contra o terceiro EOL, e o
argumento do Diferencial fica mais forte: *"medi que o catálogo morre a cada três meses e projetei
para isso"*. D-015 descartou o cross-encoder local com um motivo **narrativo** ("perde o argumento
do Diferencial") — é a única linha do log onde uma história venceu uma propriedade técnica, e foi
ela que deixou o projeto sem contingência em 25/08.

**Bloco 1 — M4, os agentes com LLM.** `src/rag/geracao.py` é o **único** arquivo do projeto que
chama um LLM. Os 8 agentes são determinísticos: o Extractor casa substring. São **40 pontos** do
barema (critérios 1 e 3) em nível de stub, contra 20 do critério 2 que já está no teto.
Começar pelos três achados de code review acima — o `"token"` é uma linha e produz saída errada.

**Bloco 2 — fixtures negativas.** As 3 startups da base são **todas** `perfil_alvo: AI-native`.
O Classifier, o Evidence Validator e o filtro de elegibilidade nunca viram um caso que devam
recusar; um classificador que devolvesse `AI-native` incondicionalmente passaria em 3 de 3 hoje.

**CORTADO, e o corte é decisão:** o sweep de dimensão, banda de chunk e `k1`/`b`. O critério 2
vale 20 pontos, para em nível 4 e já está lá. E qualquer sweep precisaria re-medir a diluição
antes, porque a faixa de busca é do modelo morto.
