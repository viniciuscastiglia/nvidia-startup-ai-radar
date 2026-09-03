# Pauta corrente — 03/09, depois da auditoria do plano

> Único arquivo de sessão do repositório. Guarda **o que está aberto**, não o que já aconteceu —
> isso está em `decisoes.md` e no git.
>
> **O plano dos dias finais mora em `projeto/plano.md`** e continua sendo a fonte do que falta.
> Este arquivo só diz onde a última sessão parou.

## 03/09, antes de começar: a auditoria do plano (D-088)

**As réguas de 02/09 foram re-rodadas e conferem todas** — `pytest 81 passed`, smoke `3/3`, agentes
`3/7 · 6/7 · 0/6 · 6/6`, exclusões `7/7 · 7/7`, justificativas `12/21 → 15/21`. **Nenhum número
documentado ontem é falso.** O que faltava era o inverso: o que a fila de 01/09 mapeava e o
`plano.md` não herdou. Quatro achados, todos já corrigidos no plano:

1. **`justificativa_negocio` estava sem dono** — zero menções no plano, nunca foi P-número, stub em
   **11 de 16** tecnologias, e o código adiava para uma "M4" que não existe mais. Virou **P-22**,
   FAZER em 05/09.
2. **A P-21 dizia que não havia gabarito** — as **7 regras do TAPI** são gabarito, e a de `Saúde`
   cobre 4 das 8 startups e reprova o caso do Morpheus. Falta o harness, e a cobertura cresce com a
   base de hoje.
3. **P-09, P-11 e P-12 se apoiam em números de modelo morto** (D-059, D-060, D-072). Não re-medir
   está **ACEITO e escrito** — muda a frase da defesa, não a decisão.
4. **"Muda o que o vídeo mostra" tinha voltado** na §3.3, sete linhas acima de onde D-084 limpou.

> **Um achado meu foi retirado sob conferência:** eu disse que a ACEITAR da P-09 prometia um número
> inexistente. Ele existe (D-072, 28/08). Confundi a re-medição com a medição.

## O que a sessão de 02/09 (execução) fez

A sessão **rodou o grafo antes de tocar em código** (D-083) — e a saída reordenou a fila que o
plano tinha fechado horas antes.

- **D-084 — "efeito no vídeo" sai do lugar de critério técnico.** Levantado pelo Vinícius: o
  `plano.md` §5 comparava as opções de P-10 numa tabela cuja coluna era *"efeito no vídeo"*. É
  **D-078 com outra roupa** — o barema saiu da função objetivo e o vídeo sentou na cadeira vazia
  em 5 dias. Recomparado por defeito · latência sentida · fornecedor único · reversibilidade,
  apareceu o argumento que a coluna escondia: o **fornecedor único**. Entrou no `CLAUDE.md`.
- **D-085 — o filtro do Inception recusava quem devia entrar.** Fecha **P-13** (aberta desde 25/08)
  e **P-20**. As duas empresas do run saíam `NÃO ELEGÍVEL`; a Axenya, prospect de maior prioridade
  da base, por *"Integramos consultoria"*. Veto de terceiro **com escopo de frase** — é o escopo,
  não a lista de palavras, que generaliza. Falso positivo **2/7 → 7/7**, falso negativo 7/7 sem
  regressão.
- **D-086 — a `justificativa_tecnica` deixa de ser o chunk cru.** Fecha **P-10**, abre **P-21**.
  A régua foi rotulada e **commitada antes do seletor**. Seletor **15/21** contra linha trivial
  **12/21**; num run real, justificativas que servem **1/6 → 4/6**.

## Estado verificado em 02/09, fim da sessão

| verificação | resultado |
|---|---|
| `pytest -q` | **81 passed** (era 67 no início do dia) |
| `python -m src.graph` | roda ponta a ponta, **as duas empresas ELEGÍVEIS**, zero LLM em produção |
| `avaliar_agentes.py` | `classe 3/7 · stack 6/7 · confianca 0/6 · elegivel 6/6+1amb · 49%/100%` |
| `--exclusoes` | **7/7** falso negativo · **7/7** falso positivo |
| `--justificativas` | trivial **12/21** · seletor **15/21** |

## O que ficou pendurado

- **`avaliar_rag.py` rodou** (02/09): o caminho de **produção não se moveu em nenhuma das seis
  colunas** depois da re-ingestão de D-082. A dúvida *"`e@1=79%` é de um corpus com entulho
  dentro"* está respondida — os 2 chunks removidos nunca ocuparam posição que o gabarito medisse.
  Registrado dentro de **D-068**. **`--geracao` rodou e FECHA P-15:** a abstenção do passo 8 dá
  **23/24 = 96%** no modelo atual (era 20-22/24 no modelo morto), e o único erro é **abstenção
  indevida**, não alucinação — o lado seguro.
- **A RE-MEDIÇÃO de `--juiz` (D-072)** segue não coletada — a medição existe, é de 28/08 e do
  modelo morto. Não bloqueia: P-09 é ACEITAR, e desde D-088 o plano diz que aceita o número velho.
- **A base continua em 8.** `"fintechs"` e `"agro"` devolvem zero — confirmado no banco.

## O que esta sessão comprou de método

> **Duas vezes no mesmo dia a execução achou o que a leitura não acharia** — e a segunda vez foi
> contra o próprio plano: o item "entulho de página, rodada 2" foi **cancelado por evidência**,
> porque os três chunks que casavam os marcadores tinham conteúdo bom dentro. O diagnóstico estava
> errado; o defeito nunca esteve no corpus.

## Decisões que dependem do Vinícius

Em `plano.md` §3.3. **O item 1 caiu em 02/09 (D-087):** alinhado com a liga, a morte do
modelo não pontua contra — o fallback do Grok **não entra**, e a hora vai para a base e a interface.
O risco real mudou de componente: o LLM tem zero chamada no grafo; quem ficou sem plano B é o
**embedder**.

Continuam abertas: **quem escolhe as 22 empresas da base** e **o canal de submissão** — este é
eliminatório por logística, não por qualidade, e é o único que ninguém consegue consertar em 09/09.
