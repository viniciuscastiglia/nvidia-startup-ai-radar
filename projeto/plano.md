# Plano de execução — 22/08 a 09/09/2026

**Entrega: 09/09/2026 às 23:59.** 18 dias contando hoje.

## Princípio que organiza tudo

O barema não premia volume de features. Nível 2 ("cumpre o mínimo") em todos os critérios dá
**50/100**; nível 3 ("bom, com decisões técnicas conscientes") dá **75**. A diferença entre os
dois não está em entregar mais — está em **cada escolha ter uma razão articulada**.

E a distribuição de peso é contra-intuitiva:

- **Núcleo de IA** (multiagente + RAG + recomendação) = **60 pontos**
- **Comunicação** (vídeo 20 + repositório e documentação 10) = **30 pontos** — 30% da nota não é código
- **Produto** (interface 5 + diferencial 5) = **10 pontos**

O vídeo vale o mesmo que o sistema multi-agente inteiro. A interface vale um quarto do vídeo.

## Sequência

| Período | Foco | Por que nessa ordem |
|---|---|---|
| **22–25/08** | decisões de stack, esqueleto do grafo, fatia vertical com 5 startups | mata o risco do eliminatório "não executa" e revela erros de modelagem do estado cedo |
| **26–30/08** | RAG NVIDIA completo: ingestão das 16 tecnologias, chunking semântico, busca híbrida, reranking, **avaliação** | 20 pontos e é a parte mais autocontida — dá para fechar sem depender do resto |
| **29/08–02/09** | base de startups completa (30 a 50 empresas) | sobrepõe de propósito: é trabalho braçal que não bloqueia código |
| **31/08–04/09** | profundidade nos agentes + motor de recomendação | 40 pontos; precisa da base populada para ter o que testar |
| **04–06/09** | interface web | 5 pontos, mas a demo do vídeo depende dela |
| **06–07/09** | README completo + **gravar o vídeo** | |
| **08–09/09** | buffer, refinar o vídeo, entregar | |

## Regras duras

1. **O vídeo é gravado até 07/09.** Vale 20 pontos, é eliminatório se faltar, e tem teto de
   7 minutos — o que exige roteiro e provavelmente três tomadas. Deixar para o dia 09 é
   apostar o projeto inteiro num dia.
2. **Um commit por decisão**, com o *porquê* na mensagem.
3. **`projeto/decisoes.md` é atualizado no momento da decisão**, não no fim. Reconstituir o
   raciocínio no dia 08/09 é impossível — e é exatamente esse texto que vira o roteiro do vídeo
   e a seção de arquitetura do README.
4. **Nada entra no repositório sem ser lido.** O eliminatório nº 4 é *"código integralmente
   gerado sem compreensão"*.
5. **Escopo é fixo, profundidade é variável.** Se o tempo apertar, cortar profundidade de um
   agente — nunca deixar um entregável de fora. Entregável ausente é nível 0 no critério.

## Marcos e critérios de pronto

**M1 — 25/08 · O pipeline executa**
Grafo LangGraph com os 8 nós rodando ponta a ponta, 5 startups no Postgres, decisões de stack
fechadas e registradas (D-001 a D-024).

**M2 — 30/08 · O RAG responde com citação**
As 16 tecnologias NVIDIA ingeridas, busca híbrida funcionando, reranking aplicado, resposta
saindo com citação da fonte. **Mais um harness de avaliação** — é o passo 9 do pipeline que o
TAPI pede e que quase ninguém entrega; é o que sustenta nível 4 no critério 2.

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
Alvo é "funcional e limpa", não "impressionante".

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

**O que a realidade fez com esta tabela, e vale mais que o placar:** a M2 fechou adiantada e a M3
travou. O sumidouro previsto no risco nº 3 era o certo — mas ele não consumiu tempo, foi
**despriorizado** três vezes seguidas por EOL de stack. Três das oito sessões foram gastas
reconstruindo a stack de recuperação, não construindo o produto.

**Onde a sessão marginal rende, hoje:** o critério 3 (motor de recomendação, 20 pontos) **não tem
régua** — o gabarito das 8 fixtures não tem campo de recomendação, então nada quebra se ela vier
errada. É o mesmo estado que os agentes tinham antes de D-050. Depois disso, a M3 e o vídeo.

**Não rende mais:** o critério 2 está em nível 4 e para lá. O sweep de dimensão, banda de chunk e
`k1`/`b` continua **cortado**, e o corte é decisão.

## Riscos identificados

| Risco | Mitigação |
|---|---|
| **A stack morrer de novo antes de 09/09.** Já aconteceu **TRÊS** vezes: 18/05 (D-013), 25/08 (D-046) e 27/08 (D-064) — e o catálogo **encolhe entre execuções**, não só em datas de EOL (D-070) | **parcial.** O passo 7 ganhou `provedor` (D-068), então perder o fornecedor inteiro é uma env var; `nenhum` degrada com graça. **O embedder continua descoberto:** trocá-lo invalida os 381 vetores — `reembedar.py` são ~25 chamadas, mas a régua inteira precisa ser re-medida junto. Cross-encoder local segue **não medido**, e é a saída se a trial do Cohere apertar |
| ~~Créditos do build.nvidia.com insuficientes~~ | **não se materializou** em 9 dias de uso. O risco real era outro — EOL de modelo, linha acima. O que aperta hoje é a **trial do Cohere**: 1.000 chamadas/mês e 10 req/min, o que já custa ~2-3 min de throttle num run completo (D-065, D-068) |
| **A M3 não acontecer.** 8 de 30 empresas, e ela foi adiada três vezes | timebox de 3h com piso em 20, duas camadas: só as 8 atuais têm gabarito, as demais entram como dado (D-062). 3-4 escolhidas adversarialmente compram caso real para a régua de exclusão |
| ~~Estado do grafo mal modelado~~ | **não se materializou.** D-008 e D-009 seguraram: nenhuma sessão precisou refatorar os nós por causa do estado |
| Vídeo deixado para o fim | data-limite 07/09 tratada como inegociável |
| Perder pontos por não conseguir defender uma decisão | log de decisões atualizado na hora + sessões de arguição (ver `guia-de-trabalho.md`) |

## Questões a levar para a liga

O TAPI não responde:
- qual o **canal de submissão** e o formato da entrega
- se a entrega é **individual ou em grupo** (a linguagem sugere individual)

Vale perguntar cedo — o eliminatório nº 1 é entrega fora do prazo *sem alinhamento prévio*.
