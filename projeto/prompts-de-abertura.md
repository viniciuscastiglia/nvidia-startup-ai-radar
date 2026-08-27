# Mensagem de abertura — sessão 08

> Copiar e colar num chat novo. Este arquivo guarda **só a próxima sessão**: prompt de abertura
> velho é armadilha, porque carrega diagnóstico que já mudou. Os anteriores estão no git.
>
> **Aperte `Shift+Tab` duas vezes ANTES de enviar**, para entrar em plan mode.

## Por que esta sessão não é sobre agente

A 07 fez o que tinha que fazer e o resultado foi negativo: as duas mudanças de agente foram
medidas contra o critério fixado antes do código e **as duas foram reprovadas**. A produção voltou
byte a byte à linha de base. Isso está fechado e não precisa ser revisitado.

O que mudou a prioridade foi outra coisa: **no meio da sessão 07 a stack NVIDIA caiu pela terceira
vez em três meses.** O LLM dos agentes devolve 410 e o reranker devolve 404 — e desta vez **não há
substituto no catálogo**. O sistema não roda ponta a ponta hoje.

A contingência para exatamente isto foi escrita em 25/08, agendada como "Bloco 0 da próxima
sessão", e escorregou duas vezes. Ela vem primeiro agora.

---

```
Sessão 08. Estou em plan mode de propósito — não escreva código nesta conversa
antes de o plano ser aprovado.

Leia, nesta ordem: projeto/sessao-07.md (o fechamento, com o EOL e as duas
reprovações), depois em projeto/decisoes.md as decisões D-064 (o terceiro EOL,
medido) e D-065 (por que "Cohere é pago" era falso, e o que isso revela sobre
como as alternativas foram descartadas).

ANTES DE PROPOR QUALQUER COISA, confirme o estado da stack com os próprios olhos:

    python scripts/smoke_nvidia.py

Em 27/08 dava 1/3: chat 410, reranking 404, embedding OK. Se algo voltou a
responder, o plano muda — então meça, não assuma. E rode a régua dos agentes,
que custa ZERO chamada e não depende da stack:

    python scripts/avaliar_agentes.py --validar
    python scripts/avaliar_agentes.py
    python scripts/avaliar_agentes.py --exclusoes

BLOCO 0 — a stack. É bloqueante: nada roda ponta a ponta sem isto, e o vídeo é
07/09.

São DUAS decisões independentes. Não as trate como uma.

  · LLM — o grafo NUNCA chama LLM. Ele é usado em dois lugares: o passo 8
    (src/rag/geracao.py) e o juiz do Extractor, que está desligado desde D-056.
    Trocar NÃO encosta no Diferencial. Opções: substituto no catálogo NVIDIA
    (nvidia/mistral-nemo-minitron-8b-8k-instruct), Grok (a liga sugeriu, o que o
    pré-autoriza), ou os dois com fallback.
    O custo real não é código — é UMA ENV VAR. É a RE-MEDIÇÃO: abstenção
    (20-22/24), json_schema (n=5) e o juiz (50-62%) foram produzidos por um
    modelo que não existe mais. Trocar não conserta esses números, INVALIDA.
    Me diga, antes de trocar, quais serão re-medidos com n=3 e quais serão
    declarados históricos com modelo e data — que é o que D-046 fez.

  · RERANKING — é ele que quebra a demo: o nvidia_rag chama reranker DENTRO do
    grafo. Sondei 18 combinações de path x modelo em 27/08, todas 404/410, e o
    catálogo vivo (84 modelos) não lista nenhum reranker.
    A hipótese de D-065, que é filha do método deste projeto: cross-encoder
    local como DEFAULT (o repositório roda sempre, sem chave, sem quota, sem
    EOL) E Cohere com trial key atrás de env var, com AS DUAS LINHAS na tabela
    de ablação ao lado de "sem rerank". É --truncar-pool aplicado ao fornecedor,
    e responde "por que não Cohere?" com número em vez de narrativa.
    Avalie essa hipótese de verdade, incluindo contra ela. Não a assuma.

O ARGUMENTO QUE DEVE DECIDIR NÃO É DE PONTOS, é o eliminatório nº 3: "projeto que
não executa E cujo vídeo não demonstra funcionamento real". Um avaliador que
clonar este repositório em outubro bate no mesmo 404 que eu bati em 27/08.
Componente hospedado em catálogo de preview é passivo do ENTREGÁVEL, não só um
problema de hoje.

VERIFICAR antes de o roteiro do vídeo depender disso: a trial do Cohere limita
Rerank a 10 req/min, e um run do grafo faz ~20 chamadas sequenciais — ~2 minutos
parado de throttle, num vídeo com teto de 7 minutos.

BLOCO 1 — os 4 achados do code review da 07 que NÃO foram pagos (D-066):
  · a dedup do nvidia_rag faz dores_enderecadas SUB-declarar — uma página puxada
    por duas dores guarda só o dor_origem da primeira. Pagar exige dor_origem
    virar lista, o que muda o contrato de CitacaoRAG.
  · profundidade_tecnica lê documentos crus e contorna o juiz de D-053. Só
    importa se a rubrica for promovida — ela está reprovada e desligada.
  · _perfil_de_um_trecho duplica o helper de tests/test_elegibilidade.py. A hora
    de unificar é quando elegibilidade() mudar de corpus, que é a decisão que
    D-061 deixou aberta.
Avalie se algum deles vale a sessão 08 ou se todos esperam. ORCE A RE-MEDIÇÃO
PÓS-REVIEW como bloco: as sessões 05 e 06 estouraram o orçamento exatamente por
não orçá-la, e na 06 foram 156 chamadas não previstas.

BLOCO 2 — a M3: 30 empresas, decidido em D-062, em duas camadas (8 com gabarito,
22 como dado, 3-4 adversariais para a régua de exclusão). Timebox 3h, piso 20.
Só depois do Bloco 0.

O QUE ESTE PLANO NÃO FAZ, e os cortes são decisão:
  · não revisita as duas mudanças reprovadas na 07 (D-059, D-060) — estão atrás
    de flag, medidas, e o veredito está escrito
  · não mexe em maturidade_stack (6/7, é guarda)
  · não escreve interface nem README — são 04-07/09

Antes de eu aprovar, o plano precisa dizer: quantas chamadas de API custa no
total, contando o pytest (~64/run) e o python -m src.graph (~42/run); o que ele
NÃO faz; e o bloco de contingência de re-medição.

Regras: português. Toda decisão vai para decisoes.md no momento em que é tomada.
Limpe __pycache__ antes de cada medição — na 07 uma medição foi contaminada por
bytecode obsoleto, porque a edição preservou o tamanho do arquivo.
```

---

## Estado em 27/08, para quem abrir o chat novo

**Funciona:** os 381 vetores (o embedder sobreviveu) · os 8 agentes, todos determinísticos · a
régua dos agentes e a régua de exclusão, ambas com zero API · 48 de 49 testes · as linhas
denso/BM25/híbrida da tabela do RAG.

**Não funciona:** `python -m src.graph` (404 no reranker) · o passo 8 (410 no LLM) ·
`test_grafo_roda_ponta_a_ponta` · as linhas com rerank da tabela.

**O `/code-review` da 07 já rodou:** 15 achados, 11 pagos, 4 registrados em D-066. `pytest` está em
**52 passed, 1 failed** de 53 — a única falha é o 404. A régua de produção continua idêntica à
linha de base depois das correções, que é o esperado de correção de rastreabilidade.

**Calendário:** entrega 09/09 · vídeo 07/09, eliminatório, teto de 7 min · tudo que o vídeo mostra
tem que existir em 06/09.

**Perguntas para a liga**, se houver contato: (1) o reranker hospedado da NVIDIA saiu do ar e o
TAPI recomenda Cohere, que também não é NVIDIA — cross-encoder local é aceitável no passo 7?
(2) vocês vão **executar** o projeto na avaliação, e com chave de quem? (3) aviso de que o catálogo
de preview aposentou modelos em 18/05, 25/08 e 27/08.
