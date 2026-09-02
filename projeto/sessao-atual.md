# Pauta corrente — 02/09, fim da sessão de execução

> Único arquivo de sessão do repositório. Guarda **o que está aberto**, não o que já aconteceu —
> isso está em `decisoes.md` e no git.
>
> **O plano dos dias finais mora em `projeto/plano.md`** e continua sendo a fonte do que falta.
> Este arquivo só diz onde a última sessão parou.

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
  Registrado dentro de **D-068**. **`--geracao` (P-15) está rodando** e é o que falta: a abstenção
  do passo 8 depende do LLM, que trocou em 01/09.
- **`--juiz` (D-072)** segue não coletado. Não bloqueia nada: P-09 é ACEITAR no plano.
- **A base continua em 8.** `"fintechs"` e `"agro"` devolvem zero — confirmado no banco.

## O que esta sessão comprou de método

> **Duas vezes no mesmo dia a execução achou o que a leitura não acharia** — e a segunda vez foi
> contra o próprio plano: o item "entulho de página, rodada 2" foi **cancelado por evidência**,
> porque os três chunks que casavam os marcadores tinham conteúdo bom dentro. O diagnóstico estava
> errado; o defeito nunca esteve no corpus.

## Decisões que dependem do Vinícius

Em `plano.md` §3.3. As que continuam abertas e **não foram tocadas hoje**:
**a chave do 2º provedor de LLM** (único risco sem contramedida), **quem escolhe as 22 empresas da
base**, e **o canal de submissão** — que é eliminatório por logística.
