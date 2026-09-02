# Pauta corrente — 02/09, fim da sessão de revisão do plano

> Único arquivo de sessão do repositório. Guarda **o que está aberto**, não o que já aconteceu —
> isso está em `decisoes.md` e no git.
>
> **O PLANO DOS DIAS FINAIS ESTÁ FECHADO e mora em `projeto/plano.md`.** Ele é a fonte única do
> que falta: todo item aberto tem destino (FAZER com dia · ACEITAR com justificativa · DECIDIR).
> **Comece por ele.** Este arquivo só diz onde a última sessão parou.
> Visão visual: [Os últimos sete dias](https://claude.ai/code/artifact/b6d37462-6743-43c1-ac6d-da5a15af7839).

## O que a sessão de 02/09 fez

Revisão do plano que **rodou o sistema** em vez de lê-lo. Três defeitos que duas sessões de
auditoria estática não tinham achado, todos corrigidos e medidos:

- **D-080** — o `smoke_nvidia.py` chamava **lento de morto**. O modelo escolhido em D-079 não
  morreu: responde HTTP 200 com mediana de **51 s** (17-88 s). `LLM_TIMEOUT` 30 → 120, e o smoke
  ganhou o estado `LENTO`, separado de `FALHOU`. **Ler `LENTO` como EOL teria aberto uma migração
  desnecessária a 5 dias do vídeo.**
- **D-081** — o `query_planner` descartava **"ia" e "ai"** (filtro `len > 2`), em **dois lugares**.
  `"startups de IA"` saía com `palavras_chave=[]` e o sistema imprimia um briefing confiante sobre
  uma fatia alfabética da base. `discrimina()` mata o silêncio. 14 testes novos; suíte 53 → 67.
- **D-082** — a `justificativa_tecnica` saía como case de **outra empresa**. Inception filtrado da
  recomendação (mas **mantido no corpus**: 4 perguntas do gabarito dependem dele), entulho de página
  removido (177 → 175 chunks), `ano_fundacao` de 3 → 6 de 8. **P-20** aberta.

## Estado verificado em 02/09

| verificação | resultado |
|---|---|
| `smoke_nvidia.py` | **3/3 (1 LENTO)** — chat 51 s de mediana, embedding 607 ms, rerank 263 ms |
| `pytest -q` | **67 passed** |
| `python -m src.graph` | roda ponta a ponta, ~2 min, **zero chamada de LLM em produção** |
| `avaliar_agentes.py` | `classe 3/7 · stack 6/7 · confianca 0/6 · elegivel 4/6+1amb · 49%/100%` |
| `--exclusoes` | `7/7` falso negativo · `2/7` falso positivo |
| `--rubrica` / `--confianca-diagnostico` | **4/7** e **2/6** — idênticos a D-060 e D-059 |

## O que ficou pendurado

- **`--juiz` (D-072) rodou >1 h em background e não foi coletado.** É a bifurcação
  determinístico × julgamento por LLM. **Não bloqueia nada**: P-09 já está classificada como
  ACEITAR no plano — *medir não é promover*, e promover a 5 dias do vídeo exigiria revalidar todo o
  subgrafo a jusante. Se der vontade de refazer: `avaliar_agentes.py --juiz`, ~52 chamadas, ~45 min.
- **`--sustentacao` e `--geracao` não rodaram.** `--geracao` **precisa** rodar depois da
  re-ingestão de D-082, junto com `avaliar_rag.py` — `e@1 = 79%` é de um corpus com entulho dentro.

## A correção de premissa que a sessão trouxe

A fila anterior mandava *"re-medir o que foi medido em modelo morto"* e listava quatro braços.
**Dois deles nunca precisaram:** `--rubrica` e `--confianca-diagnostico` são **zero API** e foram
reproduzidos hoje idênticos a D-060 e D-059. A morte do modelo nunca os tocou.

## A regra que esta sessão comprou

> **Leitura de código não substitui execução.** Duas sessões de auditoria estática não acharam
> nenhum dos três defeitos acima. Uma execução achou os três em uma hora.
> **Toda sessão que mexe em comportamento roda o grafo antes de fechar.**

## Decisões que dependem do Vinícius

Estão em `plano.md` §3.3, com prazo. As duas de hoje: **a chave do Grok** (único risco sem
contramedida) e **P-10** (de onde sai a `justificativa_tecnica`).
