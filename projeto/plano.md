# Plano de execução — revisado em 02/09/2026

**Entrega: 09/09 às 23:59. Vídeo: 07/09.** Faltam **7 dias**, e **5 até o vídeo**.

> Este plano foi reescrito em 02/09 depois de uma revisão que **rodou o sistema** em vez de lê-lo.
> Os números aqui são medidos, e o que não foi medido está marcado. O histórico do que mudou está
> em `decisoes.md` (D-080, D-081, D-082); o que está aberto, em `sessao-atual.md`.

## Princípio que organiza tudo

**O sistema tem um usuário real** — o gerente de Startups & VCs da NVIDIA Brasil, que precisa
decidir quais startups abordar e com qual argumento. A pergunta que ordena a fila é sempre a mesma:
**o que, hoje, faz este sistema falhar na mão dele?**

- **Prazo é restrição, não objetivo.** Os dias decidem *quanto* cabe. Nunca decidem *o quê*.
- **Não existe teto.** O que encerra o trabalho numa parte é custo/benefício escrito como decisão.
- **O pipeline inteiro é escopo.** Cada etapa ausente é um ponto onde a conclusão perde lastro.

E uma regra que 02/09 comprou caro:

> **Leitura de código não substitui execução.** Duas sessões de auditoria estática não acharam o
> bug do `query_planner`, o entulho no corpus, nem o `justificativa_tecnica` errado. Uma execução
> achou os três em uma hora. **Toda sessão que mexe em comportamento roda o grafo antes de fechar.**

## Regras duras

1. **O vídeo é gravado até 07/09.** Teto de 7 minutos, exige roteiro e provavelmente três tomadas.
   Deixar para o dia 09 é apostar o projeto num dia.
2. **`smoke_nvidia.py` roda antes de gravar e antes de entregar.** São 4 segundos. Desde D-080 ele
   distingue LENTO de MORTO — **`LENTO` não é EOL e não justifica trocar modelo.**
3. **Um commit por decisão**, com o *porquê* na mensagem.
4. **`decisoes.md` é atualizado no momento da decisão**, não no fim.
5. **Nada entra no repositório sem ser lido.**
6. **Escopo é fixo, profundidade é variável.** Se apertar, corta-se profundidade — nunca um
   entregável. Um pipeline com buraco não é um sistema.

## Onde o sistema falha hoje, em ordem de custo para quem usa

Tudo abaixo foi observado na saída real do grafo em 02/09.

1. **A `justificativa_tecnica` não é técnica.** É o primeiro campo que o gerente lê, e sai como
   *"Join our ecosystem of startups, partners, and developers"* (Healthcare) e como um case da
   **Writer** (NeMo) — a empresa errada. Vem de `citacao.trecho`, o chunk recuperado **cru**.
   D-082 removeu três causas (Inception como tecnologia, entulho de página, dado faltante) e
   **o defeito sobreviveu**: o padrão é do corpus inteiro e **não tem assinatura estrutural**.
   É a decisão **P-10**, e está sem dono. *Nada mais no sistema é lido antes disto.*
2. **A base devolve zero em consultas naturais.** `"fintechs AI-native em série A"` → 0.
   `"startups de agro"` → 0. São **8 de 30** empresas (27% do piso do TAPI). Não é débito de
   volume: é taxa de resultado vazio na primeira pergunta.
3. **Não existe interface.** Zero byte, e **P-06 continua aberta**. É a única superfície pela qual
   quem não lê código julga o sistema, e a demo do vídeo depende dela.
4. **`extractor` não tem teste.** 249 linhas, primeiro nó do subgrafo, alimenta todos os outros.
   (`query_planner`, o outro sem teste, foi coberto em D-081.)
5. **`README.md` afirma coisas falsas** — "a definir" para decisões já tomadas, "Em breve" para
   como rodar, e a árvore não lista `src/`, `scripts/`, `data/`, `tests/`.
6. **A `confianca` é 0/6 constante** — um campo do briefing carregando zero informação (P-11).

## Sequência — 7 dias

| Dia | Foco | Critério de pronto |
|---|---|---|
| **02/09** ✔ | instrumento e correções de execução | **feito**: D-080, D-081, D-082 · 67 testes |
| **03/09** | **P-10** + base para 30 | a justificativa técnica é técnica; fintech e agro deixam de dar zero |
| **04–05/09** | interface (P-06 decidida na frente do briefing real) | consultar → ver → exportar |
| **06/09** | README verdadeiro + roteiro do vídeo | alguém clona e roda sozinho |
| **07/09** | **gravar o vídeo** | ≤ 7 min: arquitetura, RAG, demo funcional |
| **08–09/09** | buffer, refinar, entregar | |

### 03/09 — os dois defeitos que o gerente sente

**P-10 primeiro, porque é o campo que ele lê primeiro.** A decisão é sobre de onde sai a
justificativa técnica, e as opções estão medidas, não supostas:

- **(a) escolher melhor entre os recuperados** — em vez do topo do reranker, o mais técnico dos `k`
  por densidade de marcador. Barato, determinístico, não depende do LLM lento.
- **(b) o LLM redige a partir das passagens** — é o que M4 sempre previu. Custa ~51 s por
  recomendação, o que **inviabiliza a demo ao vivo do vídeo** (5 startups × 3 recs ≈ 12 min).
- **(c) filtrar chunk de depoimento por marcador de texto** — frágil, e D-082 mostrou que não há
  assinatura estrutural.

> **Recomendação: (a) agora, (b) atrás de flag medida.** (a) cabe no dia e serve ao vídeo; (b) fica
> registrada como caminho, medida se sobrar tempo, e **não entra em produção sem régua** — a saída
> que o usuário lê é a única sem instrumento, e é por isso que ela errou tanto tempo em silêncio.

**Base para 30, com REGRA DE PARADA.** D-062 já dá a estrutura de duas camadas: só as 8 atuais têm
gabarito; as 22 novas entram como dado, com `url_fonte` real e verificada. `scripts/coletar.py`
puxa o texto e `seed.py --verificar-urls` confere.

> **Ordem obrigatória: fintech e agro primeiro** — são os setores que hoje devolvem zero. Assim,
> parar em 20 já comprou a correção do defeito nº 2. **Timebox de 3 h. O que não couber vira
> decisão escrita, não silêncio** — o autor do plano anterior já chamou 22 × 3 documentos em 3 h de
> "otimista", e ele estava certo.

### 04–05/09 — interface

**Primeiro passo, antes de escolher framework: ler o briefing real juntos**, já com P-10 aplicado e
a base ampliada — a saída que o vídeo vai mostrar. P-06 sai da pergunta *"o que o gerente precisa
ver, e em que ordem, para abordar a startup no dia seguinte"*, não de um orçamento de esforço.

Escopo mínimo inegociável: **consultar → ver empresas com classificação → ver recomendações com
evidência → exportar briefing.**

> **Este é o ponto único de falha do plano.** Duas janelas coladas no único prazo imóvel. Por isso
> a interface começa em 04/09 e não em 05/09, e por isso a base tem regra de parada.

## O que roda em background, sem ocupar ninguém

A re-medição do LLM é custo de **API, não de atenção** — chamadas sequenciais, ~51 s de mediana.

| braço | estado |
|---|---|
| `--rubrica`, `--confianca-diagnostico` | **não precisavam de re-medição.** São zero API; reproduzidos em 02/09 idênticos a D-060 (3/7→4/7) e D-059 (0/6→2/6). A morte do modelo nunca os tocou |
| `--juiz` (D-072) | **rodando em 02/09** — decide a bifurcação determinístico × julgamento por LLM |
| `--sustentacao` (D-075) | na fila |
| `--geracao` (P-15) | **depois** da re-ingestão — o corpus mudou em D-082 |
| `avaliar_rag.py` | **obrigatória**: `e@1 = 79%` é de um corpus com entulho dentro. O número novo **não é comparável** ao velho como "melhora" — o denominador mudou |

**Se o juiz ganhar**, promover a 5 dias do vídeo significa revalidar tudo a jusante. **Medir não é
promover** (D-078): o resultado vira decisão escrita, e a promoção é um segundo ato, com dia próprio
ou nenhum.

## Riscos

| Risco | Estado |
|---|---|
| **Fornecedor único de LLM.** 4 EOLs em 3 meses, **0 vivos de 10** na sondagem de 02/09, e o único vivo a 51 s de mediana | **NÃO MITIGADO, e é o maior risco aberto.** `src/config.py` isola o provedor e o Grok está pré-autorizado desde 28/08 (D-067) — **o bloqueio é a chave, não o código.** Ação: pedir hoje |
| **A stack morrer de novo antes de 09/09** | parcial. O passo 7 já tem `provedor` (D-068); o embedder segue descoberto — trocá-lo invalida os vetores e exige re-medir a régua inteira |
| **Confundir lento com morto** | **fechado em D-080.** Era risco real: o smoke reportava `FALHOU` para um modelo vivo, e a conduta de D-079 mandaria migrar |
| **A M3 não acontecer** | ativo. Mitigação: ordem por setor faltante + regra de parada acima |
| **Interface escorregar e não haver demo** | ativo, e é o ponto único de falha. Sem mitigação além de começar antes |
| **Trial do Cohere** (1.000/mês, 10 req/min) | ~2-3 min de throttle num run completo. **A cena do vídeo é uma consulta com `MAX_STARTUPS` baixo**, não o run inteiro |
| ~~Créditos insuficientes~~ · ~~Estado mal modelado~~ | não se materializaram |

## Decisões que dependem de você, não de mim

1. **A chave do Grok.** Único caminho fora do `build.nvidia.com`. Desbloqueia o risco nº 1.
2. **P-10** — de onde sai a `justificativa_tecnica`. Recomendação acima.
3. **P-06** — escopo da interface, a decidir na frente do briefing real.
4. Executam o projeto na avaliação, e com chave de quem? A conta gratuita não alcança **nenhum**
   modelo de terceiros (0 vivos em 12).
5. O reranker da NVIDIA saiu do ar e o projeto migrou para o Cohere, que o próprio TAPI recomenda —
   confirmam que é aceitável?
