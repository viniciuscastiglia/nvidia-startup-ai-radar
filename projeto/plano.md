# Plano de execução — 22/08 a 09/09/2026

**Entrega: 09/09/2026 às 23:59.** 18 dias contando hoje.

## Princípio que organiza tudo

**O sistema tem um usuário real** — o gerente de Startups & VCs da NVIDIA Brasil, que precisa
decidir quais startups abordar e com qual argumento. A pergunta que ordena a fila é sempre a mesma:
**o que, hoje, faz este sistema falhar na mão dele?**

Três consequências para o cronograma:

- **Prazo é restrição, não objetivo.** Os dias são escassos e isso decide *quanto* cabe. Nunca
  decide *o quê* por contagem de pontos.
- **Não existe teto.** Nenhuma parte do sistema "já está pronta o bastante". O que encerra o
  trabalho numa parte é custo/benefício de engenharia — escrito como decisão, não herdado.
- **O pipeline inteiro é escopo.** Um pipeline com buraco não é um sistema: cada etapa ausente é um
  ponto onde a conclusão final deixa de ter lastro.

## Sequência

| Período | Foco | Por que nessa ordem |
|---|---|---|
| **22–25/08** | decisões de stack, esqueleto do grafo, fatia vertical com 5 startups | um sistema que não roda não pode ser medido, e o esqueleto revela erros de modelagem do estado cedo |
| **26–30/08** | RAG NVIDIA completo: ingestão das 16 tecnologias, chunking semântico, busca híbrida, reranking, **avaliação** | é a parte mais autocontida — dá para fechar e medir sem depender do resto |
| **29/08–02/09** | base de startups completa (30 a 50 empresas) | sobrepõe de propósito: é trabalho braçal que não bloqueia código |
| **31/08–04/09** | profundidade nos agentes + motor de recomendação | é o miolo do produto, e precisa da base populada para ter o que medir |
| **04–06/09** | interface web | é a única superfície que um não-engenheiro consegue avaliar, e a demo do vídeo depende dela |
| **06–07/09** | README completo + **gravar o vídeo** | |
| **08–09/09** | buffer, refinar o vídeo, entregar | |

## Regras duras

1. **O vídeo é gravado até 07/09.** É obrigatório, tem teto de 7 minutos — o que exige roteiro e
   provavelmente três tomadas — e é a única forma de o trabalho ser visto por quem não vai clonar o
   repositório. Deixar para o dia 09 é apostar o projeto inteiro num dia.
2. **Um commit por decisão**, com o *porquê* na mensagem.
3. **`projeto/decisoes.md` é atualizado no momento da decisão**, não no fim. Reconstituir o
   raciocínio no dia 08/09 é impossível — e é exatamente esse texto que vira o roteiro do vídeo
   e a seção de arquitetura do README.
4. **Nada entra no repositório sem ser lido.** Código que entra sem ninguém entender por quê é
   código que ninguém consegue evoluir nem depurar depois — e este repositório vai ser mantido
   além da entrega.
5. **Escopo é fixo, profundidade é variável.** Se o tempo apertar, cortar profundidade de um
   agente — nunca deixar um entregável de fora. Um pipeline com buraco não é um sistema: a
   conclusão final perde o lastro exatamente na etapa que faltou.

## Marcos e critérios de pronto

**M1 — 25/08 · O pipeline executa**
Grafo LangGraph com os 8 nós rodando ponta a ponta, 5 startups no Postgres, decisões de stack
fechadas e registradas (D-001 a D-024).

**M2 — 30/08 · O RAG responde com citação**
As 16 tecnologias NVIDIA ingeridas, busca híbrida funcionando, reranking aplicado, resposta
saindo com citação da fonte. **Mais um harness de avaliação** — é o passo 9 do pipeline que o
TAPI pede, e sem ele o RAG é infalsificável: não há como saber se uma mudança melhorou ou piorou
a recuperação.

**M3 — 02/09 · A base está pronta**
30 a 50 startups, 3+ documentos cada, `url_fonte` real e resolvendo, diversidade entre
AI-native / AI-enabled / non-AI, incluindo os casos difíceis de propósito (inelegível ao
Inception, evidência fraca, wrapper disfarçado de AI-native).

**M4 — 04/09 · As recomendações são defensáveis**
Classificação ancorada na rubrica de `contexto/02`, evidências validadas, recomendação com os
**7 campos obrigatórios** do TAPI, briefing gerado. Filtro de elegibilidade do Inception
funcionando — o sistema recusa recomendar o programa para quem não se qualifica, e explica por quê.

**M5 — 06/09 · A demo é apresentável**
Interface que permite consultar, ver as empresas, ver as recomendações e exportar o briefing.
O escopo é decisão de produto em aberto (P-06): o que o gerente precisa ver, em que ordem, e o que
o briefing precisa mostrar para ele conseguir abordar a startup no dia seguinte.

**M6 — 07/09 · O vídeo está gravado**
Até 7 minutos: arquitetura dos agentes, sistema RAG, demonstração funcional pela interface.

## Estado em 31/08 — 9 dias da entrega, 7 do vídeo

| marco | estado |
|---|---|
| **M1** pipeline executa | **fechada** em 23/08, dois dias adiantada |
| **M2** RAG responde com citação | **fechada** — os 9 passos do TAPI, mais o harness do passo 9 |
| **M3** base 30-50 startups | **8 de 30.** É o maior débito aberto (D-062) |
| **M4** recomendações defensáveis | régua existe (D-050); 4 dos 9 agentes ainda sem instrumento |
| **M5** interface | não começada |
| **M6** README + vídeo | README desatualizado; vídeo não gravado |

**O que a realidade fez com esta tabela:** a M2 fechou adiantada e a M3 travou. O sumidouro previsto
no risco nº 3 era o certo — mas ele não consumiu tempo, foi **despriorizado** três vezes seguidas
por EOL de stack. Três das oito sessões foram gastas reconstruindo a stack de recuperação, não
construindo o produto.

**Onde o sistema falha hoje, em ordem de quanto o defeito custa a quem usa:**

1. **A recomendação sai sem lastro e nada quebra.** O motor não tem régua — o gabarito das 8
   fixtures não tem campo de recomendação. E o defeito já é visível na saída: para dor de **custo**,
   a justificativa técnica sai como *"Join our ecosystem of startups, partners, and developers"*.
   É o texto que o gerente lê primeiro, e é o que o faria fechar a aba. Mesmo estado que os agentes
   tinham antes de D-050.
2. **A base não discrimina.** 8 startups, 7 delas com profundidade técnica zero. A régua satura e o
   gargalo de vocabulário do Classifier (P-12) é insolúvel nesse tamanho.
3. **A primeira citação do RAG erra 1 vez em 5.** `e@1 = 79%` em produção (D-068): em 21% das
   perguntas o chunk mais bem colocado **não contém a âncora**. `r@3` e `e@3` estão altos, então a
   resposta certa quase sempre está no pool — mas quem lê a primeira citação e para ali é servido
   errado com frequência.
4. **O vídeo.** Sem ele o trabalho não é visível para ninguém, e a data-limite é 07/09.

**O sweep do RAG (dimensão, banda de chunk, `k1`/`b`) continua cortado, e o corte volta a ser
decisão aberta.** Ele foi mantido cortado enquanto a razão era "o critério 2 já está no teto" — teto
de nota não é razão de engenharia, e o item 3 acima mostra que havia o que melhorar. A razão que
pode sustentar o corte é outra e precisa ser dita: com 24 perguntas de gabarito, uma grade fina
provavelmente ajusta ao gabarito em vez de generalizar. Re-decidir junto com a ampliação da base.

## Riscos identificados

| Risco | Mitigação |
|---|---|
| **A stack morrer de novo antes de 09/09.** Já aconteceu **TRÊS** vezes: 18/05 (D-013), 25/08 (D-046) e 27/08 (D-064) — e o catálogo **encolhe entre execuções**, não só em datas de EOL (D-070) | **parcial.** O passo 7 ganhou `provedor` (D-068), então perder o fornecedor inteiro é uma env var; `nenhum` degrada com graça. **O embedder continua descoberto:** trocá-lo invalida os 381 vetores — `reembedar.py` são ~25 chamadas, mas a régua inteira precisa ser re-medida junto. Cross-encoder local segue **não medido**, e é a saída se a trial do Cohere apertar |
| ~~Créditos do build.nvidia.com insuficientes~~ | **não se materializou** em 9 dias de uso. O risco real era outro — EOL de modelo, linha acima. O que aperta hoje é a **trial do Cohere**: 1.000 chamadas/mês e 10 req/min, o que já custa ~2-3 min de throttle num run completo (D-065, D-068) |
| **A M3 não acontecer.** 8 de 30 empresas, e ela foi adiada três vezes | timebox de 3h com piso em 20, duas camadas: só as 8 atuais têm gabarito, as demais entram como dado (D-062). 3-4 escolhidas adversarialmente compram caso real para a régua de exclusão |
| ~~Estado do grafo mal modelado~~ | **não se materializou.** D-008 e D-009 seguraram: nenhuma sessão precisou refatorar os nós por causa do estado |
| Vídeo deixado para o fim | data-limite 07/09 tratada como inegociável |
| Uma decisão virar inexplicável e, com isso, irrevisável | log de decisões atualizado na hora + sessões de arguição (ver `guia-de-trabalho.md`) |

## Questões a levar para a liga

O TAPI não responde:
- qual o **canal de submissão** e o formato da entrega
- se a entrega é **individual ou em grupo** (a linguagem sugere individual)

Vale perguntar cedo — entrega fora do prazo só é aceita com alinhamento prévio.
