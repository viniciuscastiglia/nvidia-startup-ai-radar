# Revisão da sessão 03 — auditoria dos números e code review

> Sessão de 24/08/2026. **Nenhum arquivo do repositório foi alterado por ela** além deste
> documento, do `sessao-04.md` e de `scripts/auditoria/`. As correções abaixo estão escritas,
> não aplicadas.

A sessão 03 rodou ~50 min seguidos e produziu 9 decisões, 5 módulos novos e ~1.350 linhas.
O `guia-de-trabalho.md` prescreve três coisas que ela pulou por ter ficado longa: `/code-review`
antes de considerar pronto, não deixar entrar código não lido, e usar o Claude como banca. Esta
revisão é as duas primeiras. A terceira não rodou.

---

## 1. O que reproduz

| verificação | comando | resultado |
|---|---|---|
| testes | `pytest -q` | **39 passed** |
| gabarito vs corpus | `avaliar_rag.py --validar` | **24/24 válidas** |
| linha de base D-032 | `avaliar_rag.py --motor denso` | **89/100/100 · 68/79/84 · margem −0,2810** — exato, em dois processos independentes |
| D-037, config de produção | `--motor hibrido --k-rrf 10 --peso-lexical 0.3` | **84/100/100 · 74/79/84** — exato |
| varredura de fusão | `--varredura` | as 5 linhas citadas em D-037 batem uma a uma |

**A identidade `rerank_denso ≡ rerank_hibrido` de D-037 reproduz, e mais forte que o escrito.**
Testada em três pools com **os mesmos logits**, o que isola a diferença de pool do ruído de
serving:

| pool reranqueado | r@1 | r@3 | r@5 | e@1 | e@3 | e@5 | falha em r@1 |
|---|---|---|---|---|---|---|---|
| 20 densos | 95% | 100% | 100% | 79% | 84% | 95% | q14 |
| top-20 da fusão | 95% | 100% | 100% | 79% | 84% | 95% | q14 |
| união inteira (20–39) | 95% | 100% | 100% | 79% | 84% | 95% | q14 |

**Duas afirmações do docstring de `pipeline.py` que não tinham teste, agora verificadas:**
`peso_lexical=0.0` reduz à densa **exatamente** (8 consultas × 2 fusões, 0 divergências), e
`buscar_com_rerank` manda **a união inteira** ao reranker (30/30, 20/20, 31/31, 36/36).

**A premissa de `rerank.py:37` se sustenta.** Levantei a hipótese de que o logit depende da
composição do lote e **testei: está errada.** 18 chamadas, 6 composições (1, 2, 10 e 30
passagens, ordens trocadas), sempre `−6,8281`.

**Um número que não existia:** `--estrategia fixo-800` roda com todos os motores. O braço de
controle de D-027, medido **através do pipeline inteiro** pela primeira vez:

| estratégia | denso r@1 | rerank r@1 | rerank e@1 | rerank e@3 |
|---|---|---|---|---|
| estrutural-v1 | 89% | **95%** | **79%** | 84% |
| fixo-800 | 84% | 89% | 74% | **89%** |

D-025 continua ganhando 6 pontos em r@1 depois do reranker. Perde em e@3.

---

## 2. O que NÃO reproduz

### 2.1 A justificativa de D-036 §1 está errada no ponto que decide

Três achados, do mais grave ao menos.

**O `bm25s` nunca produz IDF negativo com `robertson`.** `bm25s/scoring.py:178`:

```python
def _score_idf_robertson(df, N, allow_negative=False):
    inner = (N - df + 0.5) / (df + 0.5)
    if not allow_negative and inner < 1:
        inner = 1                      # -> log(1) = 0
```

`allow_negative` não é passado de lugar nenhum na biblioteca. Medido no índice real: com
`robertson`, `nvidia` e `ai` pontuam **exatamente +0,0000**. A frase *"o Okapi original puniria o
chunk por conter a marca"* é falsa — ele **neutraliza** o termo. A fórmula citada em D-036 é a do
artigo, não a da biblioteca em uso.

**O recall é idêntico nas duas variantes** — os seis números: 58/63/74 e 42/47/63. A decisão não
tem consequência medida neste corpus, e o motivo é sadio: um termo com df de 92% é quase um
deslocamento constante em qualquer das duas fórmulas.

**A linha `and` da tabela é um fantasma.** `and` está na `STOPWORDS` de `lexical.py:83` e nunca
vira token. O `df=173` veio de um tokenizador ad-hoc que não aplicava a lista. As outras três
linhas reproduzem exatas sobre `texto_indexado`.

O que ainda sustenta `lucene`: só **2 de 3.063** termos do vocabulário teriam IDF negativo pela
fórmula do papel — mas são `nvidia` e `ai`, e **14 das 24 consultas** contêm um dos dois.

### 2.2 "A âncora da q17 não está no top-10" (D-040)

| pool reranqueado | âncora (chunk 81) no pool? | posição |
|---|---|---|
| união inteira — `pipeline.responder()` | **sim** | **6º** |
| top-20 da fusão — o que o `--geracao` mede | **não** | — |
| 20 densos | não | — |

O chunk 81 entra **só pelo braço lexical**, além do 20º da fusão. Como o harness trunca em 20 e a
produção não trunca, **o `--geracao` mediu um pipeline em que a âncora não existe.** Idêntico em
K=10/0,3 e K=20/0,5.

O "teto real de 23/24" sobrevive por acidente aritmético (6 > 5 = `k` do gerador), mas o
diagnóstico está trocado: não é *"a recuperação entrega o documento certo e não o chunk que
responde"*, é **entrega em 6º e o gerador lê 5**. `k=6` resolveria a q17 hoje.

### 2.3 A curva de diluição de D-034 — problema de validade, não de variância

**Os logits reproduziram.** 4 execuções × 9 tamanhos = **36 de 36 idênticos dígito a dígito**.
D-034 afirma o contrário.

**O enchimento fala de OUTRO assunto** (cuDF) enquanto a query pergunta de NIM: o teste mede "o
chunk ficou mais off-topic", não "o chunk ficou maior". Um chunk real de 800 tokens é 800 tokens
sobre o mesmo produto. Refeito concatenando chunks vizinhos reais do documento do NIM — que é o
que um `TETO_TOKENS` maior de fato produziria:

| tokens | 176 | 380 | 564 | 712 | 898 | 1076 | 1217 | 1391 | 1533 | 2181 |
|---|---|---|---|---|---|---|---|---|---|---|
| logit | −2,56 | −2,56 | −6,83 | −9,10 | −8,53 | −9,10 | −6,83 | −6,26 | −8,53 | −9,10 |

Duas execuções, idênticas. Com texto real a cobrança começa **entre 380 e 564** — não entre 600 e
800 — e depois **satura** em vez de continuar caindo. Isso é a favor de `TETO_TOKENS = 450` e
contra a faixa de busca de ~800 declarada para o sweep da sessão 04.

*Limite deste achado: um documento, uma consulta. Ganhou em validade sobre o teste de D-034 e não
ganhou nada em amostra.*

### 2.4 Dois números pequenos

**A união é de 20 a 39** (média 29,1 nas 24 consultas), não "28 a 34" como diz
`pipeline.py:33-35`. Três consultas dão exatamente 20 (q02, q11, q18 — braço lexical curto ou
vazio) e **9 de 24 gastam dois lotes de rerank**, não "algumas".

**`K=60` não é "uniformemente pior" que `K=10`.** Em peso 1,0 os dois dão 63%.

---

## 3. Texto pronto para o `decisoes.md`

Notas datadas, para o fim de cada decisão afetada. Acrescentar no fim **não reescreve** — não
apaga nem altera o que está lá, e deixa a correção onde quem lê a decisão vai encontrá-la.

### Para o fim de D-034

```
**Atualização — 24/08/2026, sessão de revisão.** Três correções, todas medidas
(`scripts/auditoria/auditoria_diluicao.py` e `auditoria_lote.py`):

1. **"Os logits não reproduzem dígito a dígito" não se confirmou.** Quatro execuções novas dos
   nove tamanhos deram 36 de 36 logits IDÊNTICOS. A hipótese de que a variação vinha da
   composição do lote foi testada e DERRUBADA: 18 chamadas em 6 composições (1, 2, 10 e 30
   passagens, ordens trocadas) devolveram sempre −6,8281. A variação registrada aqui é rara e
   intermitente, não sistemática. A regra operacional — nada depende de margem abaixo de ~2
   logits — continua valendo; o mecanismo descrito acima não descreve o que se observa.
2. **O teste de diluição tem um problema de VALIDADE que a ressalva de variância não cobre.** O
   enchimento fala de cuDF enquanto a query pergunta de NIM: o que ele mede é "o chunk ficou mais
   off-topic", não "o chunk ficou maior". Um chunk real de 800 tokens é 800 tokens sobre o mesmo
   produto.
3. **Refeito com texto REAL** (chunks vizinhos concatenados do documento do NIM, que é o que um
   TETO maior produziria): 176→−2,56 · 380→−2,56 · 564→−6,83 · 712→−9,10 · e depois PLATÔ entre
   −6,26 e −9,10 até 2.181. Duas execuções idênticas. A cobrança começa entre 380 e 564, não
   entre 600 e 800, e SATURA. Isso reforça TETO_TOKENS=450 e fecha a faixa de busca do sweep em
   ~120–560, não ~800. Limite: um documento, uma consulta.
```

### Para o fim de D-036

```
**Atualização — 24/08/2026, sessão de revisão.** A tabela de IDF acima foi calculada num script
solto com tokenizador inline, não com `src.rag.lexical.tokenizar`. Recalculada com o tokenizador
real (`scripts/auditoria/idf_lucene_vs_robertson.py`):

1. **A linha `and` não existe.** `and` está na STOPWORDS e nunca vira token: não tem df, não tem
   IDF e não participa de ranking. As outras três linhas reproduzem exatas sobre `texto_indexado`.
2. **O ARGUMENTO CENTRAL ESTÁ ERRADO PARA A BIBLIOTECA EM USO.** `bm25s/scoring.py:178` trava o
   IDF de Robertson em zero (`if inner < 1: inner = 1`), e `allow_negative` não é passado de lugar
   nenhum. Medido no índice real: com `robertson`, `nvidia` e `ai` pontuam exatamente +0,0000. O
   Okapi original NEUTRALIZA o termo, não o pune. A fórmula citada acima é a do artigo, não a do
   `bm25s`.
3. **O recall é idêntico nas duas variantes:** 58/63/74 e 42/47/63, os seis números. A escolha não
   tem consequência medida neste corpus — um termo com df de 92% é quase um deslocamento
   constante em qualquer das duas fórmulas.

A decisão (`lucene`) FICA, e o argumento passa a ser este: só 2 de 3.063 termos do vocabulário
teriam IDF negativo pela fórmula do papel, mas são `nvidia` e `ai`, e 14 das 24 consultas contêm
um dos dois — sob `robertson` esses tokens ficariam inertes; sob `lucene` contribuem pouco e
positivo. É um argumento mais estreito que o escrito, e sem efeito na régua.
```

### Para o fim de D-037

```
**Atualização — 24/08/2026, sessão de revisão.**

1. **A tabela de ablação acima vale em K=10 / peso_lexical=0,3, e isso não estava escrito.** Os
   defaults do `avaliar_rag.py` são K=20 / 0,5, e nessa configuração a híbrida dá 68/89/100 ·
   53/68/84 — que é a tabela publicada no `sessao-04.md`. Os dois números estão certos; o erro é
   três documentos apresentarem tabelas diferentes como se fossem a mesma régua. O corolário
   "antes do rerank a híbrida é melhor no estrito, e@1 74% vs 68%" só vale em K=10/0,3: no default
   do CLI a híbrida é PIOR (53% vs 68%).
2. **"`K=60` é uniformemente pior que `K=10`" é falso num ponto:** em peso 1,0 os dois dão 63%.
   Pior ou igual, estritamente pior em 3 dos 4 pesos.
3. **A identidade `rerank_denso ≡ rerank_hibrido` foi reconfirmada e é mais forte que o escrito:**
   vale também sobre a UNIÃO INTEIRA, com os mesmos logits, mesma falha única (q14). Corolário
   incômodo: não truncar a união custa 37,5% mais chamadas de rerank e compra zero nesta régua.
```

### Para o fim de D-040

```
**Atualização — 24/08/2026, sessão de revisão.** A afirmação "a âncora da q17 NÃO está no top-5,
nem no top-10" não reproduz sob o pipeline final (`scripts/auditoria/auditoria_q17.py`):

- pela `pipeline.responder()`, a âncora (chunk 81) está na união e o reranker a põe em **6º**;
- pelo `--geracao`, ela **não está no pool** — o harness trunca a fusão em 20 e o chunk 81 entra
  só pelo braço lexical, além dessa posição.

O teto de 23/24 sobrevive por acidente aritmético (6 > 5 = k do gerador), mas o diagnóstico está
trocado: não é "a recuperação entrega o documento certo e não o chunk que responde", é **entrega
em 6º e o gerador lê 5**. `k=6` resolveria a q17 hoje, sem tocar em chunking — o que remove a
justificativa de atacar este caso com um modelo de 70b antes de testar o parâmetro.

**Não medido nesta revisão:** a acurácia de abstenção, a q07 sistemática e o `indices_citados`
continuam com as três execuções de 24/08. O `--geracao` não foi re-rodado.
```

### Decisão NOVA, que depende de você — não foi escrita

**O harness passa a rodar a configuração de produção?** Importar `K_RRF_PADRAO`,
`PESO_LEXICAL_PADRAO` e `POOL_PADRAO` de `src.rag.pipeline` em vez de redeclarar em
`avaliar_rag.py:73` e `main()`, e parar de truncar o pool em `avaliar_rag.py:208`.

É decisão e não correção porque a alternativa defensável existe: manter o harness truncando **de
propósito**, como braço de controle do "vale a pena não truncar?" — que hoje é a única evidência
de que a união inteira custa 37,5% mais rerank e compra zero.

---

## 4. Code review — o que está mais fraco

### `pipeline.py` existe para quebrar ciclo de import — o módulo está certo, a justificativa não

O ciclo é real, mas a causa não é a orquestração: é `busca.py` fazer **dois trabalhos**. A
convenção é *"um passo do pipeline = um módulo em `src/rag/`"*, e `busca.py` é o passo 6a **e** o
módulo de tipos do pipeline inteiro. O sintoma está em `scripts/avaliar_rag.py:64`, que importa
`Passagem` de `src.rag.busca` para avaliar motores que não são o denso.

**Proposta:** `Passagem` e `para_citacao` saem para `src/rag/tipos.py`. `pipeline.py` continua
existindo — `responder()` compõe 6+7+8 e alguém tem que ser a porta de entrada —, mas passa a
existir por desenho e não por necessidade. Barato agora, caro depois que os oito agentes da M4
importarem de `busca`.

### O fallback de `justificativa_negocio` — problema legítimo, implementação que encobre

O problema é real: o campo é um dos 7 obrigatórios do TAPI e vinha vazio. Mas o texto do fallback
**não menciona a tecnologia** — recomendar Morpheus, CUDA Toolkit ou Riva para a mesma startup
produz `justificativa_negocio` byte a byte idêntica. E a última frase (*"São gargalos que hoje
limitam margem ou velocidade de entrega"*) afirma um fato de negócio sem fonte, contra a
convenção do repositório.

O que decide a questão é o teste: `assert getattr(rec, campo)` só checa verdade booleana. **O
fallback o satisfaz por construção**, e nenhum teste consegue mais pegar que o campo é vazio de
conteúdo. Uma falha detectável virou indetectável.

**Proposta, em red-green:** fortalecer o teste primeiro — assertar que duas recomendações com
tecnologias diferentes têm `justificativa_negocio` diferentes —, ver falhar com o código de hoje,
e só então decidir se o fallback varia com a tecnologia ou se a recomendação não sai.

### A instrução de idioma em `geracao.py` — duas frases de arquitetura e uma de régua ajustada

As duas primeiras frases são D-014 declarada (corpus EN, consulta PT) e a defesa de D-040 vale
inteiramente para elas. **A oração final não:** *"inclusive quando aparece dentro de uma lista"*
descreve a forma da evidência no caso único que falhou — a palavra "Portuguese" numa enumeração
de idiomas na página do Riva. Nenhum fato de arquitetura diz que a evidência deste sistema vem em
listas.

**Proposta:** tirar a oração e re-medir. Se a q05 continuar passando, era decoração e a decisão
fica limpa; se falhar, D-040 precisa mudar o que afirma.

*Nota a favor: a checagem de regressão que D-040 descreve foi a certa. O risco de uma instrução
assim é deixar o modelo mais ávido por achar resposta, e isso apareceria como falsa resposta no
conjunto `sem_resposta` — que foi o que se conferiu.*

### O que a sessão 03 não declarou e é mais grave que os três

1. **O harness não mede o sistema que a produção roda** — defaults divergentes e truncagem do
   pool. `POOL_PADRAO`, `K_RRF` e os pesos estão declarados duas vezes e já divergiram. A q17 é a
   prova concreta.
2. **`justificativa_tecnica=citacao.trecho`** manda o texto cru do chunk para um campo obrigatório
   do TAPI. É a origem, numa linha, da dívida nº 6 do `sessao-04.md`.
3. **`fusao.py:30` diz "listas de 10 — 15% de amplitude"** e D-037 diz "listas de 20 — 31%".
   `POOL_PADRAO` é 20, e o parágrafo emenda "no nosso, com pool de 20" logo depois de usar 10.
4. **Bug: consulta vazia estoura com `httpx.HTTPStatusError: 400`** no embedder. A guarda de "zero
   passagens" em `geracao.py:72` é inalcançável por `responder()`, e `nvidia_rag.consulta_da_dor`
   devolve `""` se uma dor vier sem texto e sem stack.

---

## 5. O que NINGUÉM mediu — nem a sessão 03, nem esta revisão

**O risco mais carregado do conjunto não está entre os erros acima.** A tabela que decide
`json_schema` contra `function_calling` em D-040 é **uma pergunta (a q23), com uma execução por
método** — e a mesma decisão estabelece, duas seções acima, que o passo 8 é não-determinístico
(22, 23 e 24 de 24 com o mesmo código). Foi a mesma sessão que criou D-039 exatamente para
resolver esse problema do outro lado: *"com n=1 de um lado não há distribuição, há um ponto"*.

Esse padrão não foi aplicado à escolha do método de saída estruturada — e ela virou
`METODO_ESTRUTURADO` em `src/llm.py`, o portão único por onde os oito agentes da M4 vão passar.

**Fechar isso custa ~15 chamadas:** a q23 nos três métodos, cinco execuções cada.

Também continuam sem medição, e as três já estavam declaradas assim:

- **a hipótese central de D-042** — "o léxico paga na consulta com stack literal". Ela importa
  mais agora: depois desta revisão, é o **único argumento vivo** para manter o BM25;
- **a qualidade ponta a ponta** (dívida nº 6), observada uma vez;
- **a fidelidade da prosa ao contexto**.

E nada das sessões 01 e 02 entrou nesta auditoria — D-001 a D-031 não foram tocadas.

---

## 6. Recorte de commits sugerido

Doze commits na ordem de dependência, cada um deixando a árvore testável. O `decisoes.md` entra
em pedaços — `git add -p` por bloco — que é o que faz "commit por decisão" valer no `git log`.

| # | escopo | arquivos |
|---|---|---|
| 1 | **D-034** — a janela do reranker é 8.192, e o teto do chunk fica por outro motivo | `scripts/verificar_reranker.py`, `src/rag/chunking.py`, hunk D-034 |
| 2 | **D-041** — `Passagem` interna, `CitacaoRAG` de contrato | `src/rag/busca.py`, hunk D-041 |
| 3 | **D-036** — BM25 `lucene` e a tokenização que dobra acento | `src/rag/lexical.py`, `tests/test_lexical.py`, `requirements.txt`, hunk D-036 |
| 4 | **D-037** — fusão RRF, soma como controle | `src/rag/fusao.py`, `tests/test_fusao.py`, hunk D-037 |
| 5 | **D-038** — o reranker lê `texto_indexado` | `src/rag/rerank.py`, hunk D-038 |
| 6 | composição dos passos 6+7+8 | `src/rag/pipeline.py` |
| 7 | **D-039** — o gabarito ganha 4 perguntas sem resposta | `data/avaliacao/gabarito.yaml`, hunk D-039 |
| 8 | o harness que mede a ablação | `scripts/avaliar_rag.py` |
| 9 | **D-035** — a hipótese de D-033 está refutada | hunk D-035 |
| 10 | **D-040** — passo 8, geração com citação e abstenção | `src/llm.py`, `src/rag/geracao.py`, `src/state.py`, hunk D-040 |
| 11 | **D-042** — a consulta do NVIDIA RAG sai da dor + da stack | `src/agents/nvidia_rag.py`, `src/agents/recommendation.py`, hunk D-042 |
| 12 | documentação da M2 | `CLAUDE.md`, `projeto/plano.md`, `projeto/sessao-04.md` |

Depois, um 13º com as notas da seção 3 mais este documento e `scripts/auditoria/` — separado de
propósito, para o `git log` mostrar que a correção veio de uma auditoria e não de um retoque no
meio do trabalho.
