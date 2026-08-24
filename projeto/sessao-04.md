# Sessão 04 — fechar a M2: os commits, as correções da revisão, e sair do RAG

## Sessão 03 — FECHADA em 24/08/2026

**Concluído:** os passos **6, 7 e 8** do pipeline do TAPI. Com o passo 9 já existente desde a 02,
**os 9 passos estão fechados dentro da M2**. 9 decisões novas (D-034 a D-042), 39 testes,
gabarito de 20 → **24 perguntas**.

### O resultado, na mesma régua de sempre

| motor | r@1 | r@3 | r@5 | e@1 | e@3 | e@5 |
|---|---|---|---|---|---|---|
| denso — linha de base (D-032) | 89% | 100% | 100% | 68% | 79% | 84% |
| lexical sozinho | 58% | 63% | 74% | 42% | 47% | 63% |
| híbrido (RRF) | 68% | 89% | 100% | 53% | 68% | 84% |
| **rerank sobre denso** | **95%** | 100% | 100% | 79% | 84% | 95% |
| **rerank sobre híbrido** | **95%** | 100% | 100% | 79% | 84% | 95% |

> **Nota da revisão de 24/08:** a linha `híbrido` acima é a do **default do CLI**
> (`K=20`, `peso_lexical=0.5`). Na configuração de produção (`K=10`, `0.3`) ela é
> **84 / 100 / 100 · 74 / 79 / 84**, que é a tabela de D-037 e do `CLAUDE.md`. Os dois
> números estão certos; o erro foi publicar tabelas de configurações diferentes como se
> fossem a mesma régua. Ver `revisao-03.md` §2.4 e §3.

**Geração (passo 8), três execuções:** acurácia de abstenção **22–24 de 24**. Quinze
oportunidades de alucinar, **zero alucinações** — todo erro é abstenção falsa.

### Cinco coisas que só apareceram medindo

| | O que se supunha | O que a medição mostrou |
|---|---|---|
| **Janela do reranker** | 512 de cross-encoder, e chunk de 450 estaria no limite | **8.192 conjuntos** (query+passagem). O risco que bloqueava a sessão não existia; o achado útil foi a curva de diluição (D-034) |
| **BM25** | resolveria a q14 e a q19, que o denso erra | resolve **as duas isoladamente** — e a fusão não colhe nenhuma. Depois do rerank contribui **zero** (D-037) |
| **Abstenção pelo reranker** | o cross-encoder julga se a passagem *responde* | margem de **−17,63**. A q23 recebe logit **+8,53**, dos mais altos do gabarito, sem conter a resposta (D-035) |
| **n=1 do gabarito** | ampliar traria calma à conclusão | piorou a margem em **4x**. O n=1 estava subestimando o problema (D-039) |
| **Saída estruturada** | detalhe de implementação | `function_calling` alucina "30%" onde `json_schema` abstém. Mesmo modelo, mesmo prompt (D-040) |

### Duas afirmações minhas que a própria sessão derrubou

1. **"A q19 é armadilha lexical."** Errado — olhei presença de termo por *documento*; o BM25
   pontua *chunk*, e existe **um único chunk no corpus com `vllm` e `sglang` juntos: o do NIM**.
2. **"RRF empata ranks espelhados, nenhum peso quebra."** Errado — o teste
   `test_rrf_em_ranks_espelhados_so_obedece_a_ordem_dos_PESOS` derrubou. O empate só ocorre em
   `w_denso == w_lexical`; fora disso vence quem tem o peso maior. A versão correta é **pior**
   para o RRF: em ranks espelhados ele decide por hiperparâmetro, não por evidência.

### Dívida deixada de propósito

| # | O que | Por quê |
|---|---|---|
| 1 | **A citação é o ponto fraco.** q07 aponta fonte errada nas 3 execuções; 1 a 5 respostas por execução não apontam nada | A abstenção está resolvida, o "de onde veio" não. Rastreabilidade é requisito duro do TAPI — é trabalho da M4 (modelo maior só neste nó, ou verificação por código) |
| 2 | `&nbsp;` vaza para o `caminho_secao` de 7 chunks | Consertar exige re-ingerir → re-embedar → invalidar a linha de base no meio da sessão. Vai junto do re-ingest do sweep de teto |
| 3 | `dores_enderecadas` do Recommendation lista todas as dores validadas | Amarrar dor → citação exige informação que passou a existir hoje (`nvidia_rag` consulta uma vez por dor) mas que `CitacaoRAG` não carrega. M4 |
| 4 | Fidelidade da prosa ao contexto | Não medida, e **declarada como não medida**. Exigiria LLM-as-judge, que traz uma régua que também precisaria ser validada |
| 5 | A hipótese central de D-042 | "O léxico paga na consulta com stack literal" continua **não medida**. Exigiria um gabarito de consultas no formato que o Extractor produz |
| 6 | **A recomendação ponta a ponta PIOROU** enquanto a recuperação melhorava | Ver abaixo — é o achado mais desconfortável da sessão e o que mais muda a M4 |

### A dívida nº 6, por extenso, porque ela é contraintuitiva

`python -m src.graph "startups brasileiras de saúde usando IA"` roda, cita a base NVIDIA e toda
URL resolve. Mas para a **Laura Networks** (saúde) ele recomenda **Morpheus** (cybersecurity) e
**CUDA Toolkit** — esta com justificativa técnica *"Resources / NVIDIA Developer Forums / An
information exchange to help developers get answers to their technical questions"*, que é seção
de navegação e não capacidade técnica.

**As métricas de recuperação subiram e a qualidade da recomendação caiu.** Não é contradição, e
o diagnóstico tem duas partes, nenhuma delas no RAG:

1. **O Extractor ainda é stub** e produz dores genéricas — `custo, escalabilidade,
   observabilidade, privacidade` para toda startup. Consulta genérica recupera chunk genérico, e
   o recuperador está fazendo exatamente o que foi medido fazendo bem.
2. **O Recommendation pega os 3 primeiros trechos sem julgar o que eles são.** Um chunk de
   "Resources / Forums" não deveria ser recomendável em nenhuma circunstância.

**O stub antigo parecia melhor porque a tabela dor→tecnologia era curada à mão** — boa aparência
sem base. Trocá-la pelo RAG real transformou uma qualidade falsa numa qualidade ruim e
*mensurável*, que é progresso mesmo parecendo o contrário. Mas é o argumento mais fácil de um
avaliador na demo, então **a M4 precisa atacar isto antes de qualquer refinamento de prompt.**

Duas linhas de ataque, a decidir com medição:
- **Filtro de recomendabilidade no chunk**: seções de navegação, instalação e fórum saem do pool
  do Recommendation. Cuidado: isso é diferente do limiar de abstenção que D-035 derrubou — não é
  "esta passagem responde?", é "esta passagem descreve uma capacidade?".
- **Extractor real primeiro**, e re-medir antes de mexer no resto: pode ser que dor específica
  resolva sozinha, já que o recuperador demonstrou recall@1 de 95% quando a consulta é boa.

---

## Revisão de 24/08 — a pauta abaixo foi REESCRITA

A sessão de revisão auditou os números da 03 e mudou o que a 04 deve fazer. O relatório inteiro
está em **`projeto/revisao-03.md`**; o que muda a pauta é isto:

- **A auditoria eliminou o RAG como suspeito.** Três pools de rerank, duas estratégias de
  chunking, duas variantes de BM25 e a grade de fusão inteira convergem nos mesmos números. Não
  há métrica a comprar ali — o que confirma, com medição, o que a dívida nº 6 já dizia.
- **A M2 vencia em 30/08 e fechou em 24/08.** Há seis dias de folga, e o barema diz onde eles
  valem: o critério 2 tem ~5 pontos de teto; o critério 3 tem 10 a 15 e está com o motor
  recomendando Morpheus para uma startup de saúde.
- **O Bloco 2 encolheu.** A diluição refeita com texto real mostra que a cobrança começa entre
  380 e 564 tokens e satura — a faixa de busca fecha em ~120–560, não ~800.
- **O Bloco 3 ganhou um alvo de graça.** A âncora da q17 está em **6º** na produção; `k=6` pode
  resolver o caso sistemático que ia justificar um modelo de 70b.

---

## Pauta da sessão 04 — fechar a M2 e sair do RAG

### Bloco 0 — o que estava pendente da 03 (~1h30, e nada aqui é opcional)
- [ ] **`/code-review`** sobre a árvore de trabalho, antes dos commits — é o passo que a 03 pulou
- [ ] **Os 12 commits** do recorte em `revisao-03.md` §6. 1.350 linhas sem commit violam a regra
      dura nº 2 do `plano.md`, e as mensagens **são** o roteiro do vídeo e a seção de arquitetura
      do README
- [ ] **As 4 notas de correção** no `decisoes.md` — texto pronto em `revisao-03.md` §3
- [ ] **A decisão nova que ficou em aberto:** o harness passa a rodar a config de produção, ou
      fica truncando de propósito como braço de controle? (`revisao-03.md` §3, fim)

### Bloco 1 — os ~15 chamados que fecham o risco aberto (~15min)
- [ ] **q23 nos três métodos de saída estruturada, cinco execuções cada.** É a afirmação mais
      carregada e menos amostrada do projeto: `METODO_ESTRUTURADO` em `src/llm.py` é o portão
      único dos oito agentes da M4 e foi decidido com n=1, na mesma sessão que criou D-039 para
      resolver exatamente esse problema do outro lado
- [ ] **`k=6` na geração.** Cinco minutos, e pode resolver a q17

### Bloco 2 — `docs/rag.md`, o de maior retorno da pauta (~1h)
- [ ] A tabela de ablação completa, **com a configuração ao lado de cada linha** — foi a falta
      disso que produziu três documentos com números diferentes na "mesma régua"
- [ ] Alimenta README (peso 10) e vídeo (peso 20). É o único bloco da pauta original que não era
      otimização
- [ ] Conferir que `python -m src.graph` roda ponta a ponta com o RAG real

### CORTADOS, e o corte é decisão
- ~~Os três sweeps de graça (dimensão, `k1`×`b`, `K`×pesos)~~
- ~~A banda de chunk~~ — o único que custava crédito
- ~~`llama-3.1-70b` no nó de citação~~ — testar `k=6` antes

**Registrar o corte no `decisoes.md`.** *"A ablação mostrou que não há métrica a comprar no
critério 2; a folga de seis dias vai para o critério 3"* é uma decisão de nível 4, não uma
desculpa — e é exatamente o tipo de frase que o eliminatório nº 4 cobra.

---

## Depois da 04: o Extractor, e o aviso do prazo

A próxima sessão de código é o **Extractor**. É a linha de ataque que a dívida nº 6 já elegeu
(*"Extractor real primeiro, e re-medir antes de mexer no resto"*), e a auditoria removeu a
alternativa concorrente da mesa: o recuperador tem recall@1 de 95% quando a consulta é boa, então
o problema é a consulta.

**E a M3 não começou.** 30 a 50 startups, vence em 02/09, e o próprio `plano.md` a chama de *"o
maior sumidouro do projeto"*. É trabalho braçal que não bloqueia código — é o candidato natural
para consumir a folga em paralelo. Se algo vai estourar prazo neste projeto, a aposta é essa, não
o RAG.

## Medir cada incremento contra o gabarito

O de sempre, e com o cuidado que a 03 ensinou e a revisão confirmou: **a geração varia entre
execuções** (22, 23 e 24 de 24 com o mesmo código). Número de geração se reporta em três
execuções ou não se reporta. A **recuperação**, ao contrário, reproduz — a revisão a mediu duas
vezes em processos independentes e deu igual.
