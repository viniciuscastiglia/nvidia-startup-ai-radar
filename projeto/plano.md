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
fechadas e registradas. Detalhamento em `sessao-01.md`.

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

## Projeção de sessões (feita em 23/08, ao fechar a M1)

**11 a 13 sessões** do calibre da 01 (4-5h). Restam 17 dias — cerca de 0,7 sessão por dia.

| Marco | Sessões | Corte |
|---|---|---|
| **M2** RAG | **3** | ~~ingestão+embed+gabarito~~ 23/08 · ~~híbrida+rerank+**geração**~~ 24/08 · resta só otimização medida. A sessão 03 puxou o passo 8 para dentro da M2 (D-040), então **os 9 passos do TAPI estão fechados** e a 3ª sessão vira sweep, não entrega |
| **M3** base 30-50 startups | **2-3** | ⚠️ o sumidouro |
| **M4** agentes com LLM | **2-3** | inclui corrigir os 3 erros de D-020 |
| **M5** interface | **1** | vale 5 pontos, não vale mais |
| **M6** README + vídeo | **2** | uma para roteiro, uma para gravar |
| buffer | **1** | |

**Três coisas que a tabela esconde:**

1. **A restrição não é sessão, é calendário.** O vídeo é 07/09, é eliminatório se faltar e tem
   teto de 7 minutos. Tudo que ele precisa *mostrar* tem que existir em 06/09.
2. **M3 pode virar 5 sessões sem avisar.** D-021 matou o atalho: resumo automático de página não
   preenche campo do banco. Cada empresa é ~15-20 min feita direito. Se estourar, **corte o
   número de empresas, não o rigor** — 25 bem curadas com a diversidade coberta valem mais que
   50 rasas.
3. **"Mais completo" tem teto.** O barema para em nível 4 por critério, e entregável fora dos 7
   vale zero. A sessão marginal rende mais no **harness do passo 9** e no **vídeo** — nunca em
   mais startups nem em mais interface.

Uma sessão a mais, fora da conta: **os conceitos de domínio 11 e 12 de `conceitos.md`** (stack
NVIDIA e rubrica AI-native). Não se aprendem implementando e são o que o vídeo mais cobra.

**Estado em 25/08, depois do segundo EOL:** M1 fechada dois dias adiantada, **os 9 passos do
pipeline RAG do TAPI fechados**, e a stack de recuperação **trocada inteira** (D-046) porque
embedder e reranker morreram às 09:00Z. Reconstruído no mesmo dia: 381 chunks re-embedados,
régua re-medida, `pytest` de volta a 40, grafo rodando ponta a ponta.

`recall@1` está em **95%** já no denso puro, e@3 em **95%** com reranking. A acurácia de abstenção
caiu para uma faixa de **20–22 de 24** e a assimetria "nunca alucina" foi **refutada** (D-040,
Atualização 3). `json_schema` fechado com n=5 (D-047).

**O sweep que esta terceira sessão da M2 tinha reservado — dimensão, banda de chunk, `k1`/`b` —
está CORTADO.** O critério 2 vale 20 pontos e para em nível 4; ele já está lá. A sessão marginal
rende mais na M4, onde 40 pontos ainda estão em nível de stub: `src/rag/geracao.py` é o único
arquivo do projeto que chama um LLM, e os 8 agentes são determinísticos.

**O risco de abstenção que a sessão 02 abriu está FECHADO, e não como se esperava.** D-033 supôs
que o cross-encoder resolveria. Não resolveu: a margem piorou de −0,19 para **−17,63** com o
gabarito ampliado (D-035). A abstenção desceu para a geração e **funciona lá** — 5/5, incluindo
uma pergunta desenhada para induzir alucinação com citação de fonte real. Isso NÃO encostou na
M4: fechou dentro da M2.

**Um risco novo, menor, que a sessão 03 revelou:** o `llama-3.1-8b` erra a **citação** com
frequência não desprezível (aponta índice errado, ou responde sem apontar nada) mesmo quando a
resposta está certa. A abstenção é confiável; o "de onde veio" ainda não é. Como rastreabilidade é
requisito duro do TAPI, isso é trabalho da M4 — modelo maior só neste nó, ou uma verificação por
código de que a afirmação ocorre no trecho citado.

## Riscos identificados

| Risco | Mitigação |
|---|---|
| **A NVIDIA aposentar o embedder ou o reranker antes de 09/09 (HTTP 410).** Já aconteceu DUAS vezes: 18/05 (D-013) e 25/08 (D-046). A cadência do catálogo de preview é de meses, e o vídeo é 07/09 | **hoje: nenhuma.** Env var não cobre — trocar o embedder invalida os 381 vetores. `scripts/reembedar.py` reduz a recuperação a ~25 chamadas e 20 min, mas a régua inteira precisa ser re-medida junto. **Um caminho local de fallback é o Bloco 0 da próxima sessão** |
| Créditos do build.nvidia.com insuficientes para 8 agentes em desenvolvimento | validar no Bloco 1 da sessão 01, antes de qualquer decisão depender disso; provedor configurável por env var |
| Montar a base consumir dias demais (é o maior sumidouro do projeto) | timebox rígido; base pequena e bem curada vale mais que grande e rasa — o barema avalia o raciocínio sobre os dados, não o tamanho do dataset |
| Estado do grafo mal modelado, exigindo refatorar os 8 nós | resolver no Bloco 3 da sessão 01, com plan mode, antes de escrever lógica |
| Vídeo deixado para o fim | data-limite 07/09 tratada como inegociável |
| Perder pontos por não conseguir defender uma decisão | log de decisões atualizado na hora + sessões de arguição (ver `guia-de-trabalho.md`) |

## Questões a levar para a liga

O TAPI não responde:
- qual o **canal de submissão** e o formato da entrega
- se a entrega é **individual ou em grupo** (a linguagem sugere individual)

Vale perguntar cedo — o eliminatório nº 1 é entrega fora do prazo *sem alinhamento prévio*.
