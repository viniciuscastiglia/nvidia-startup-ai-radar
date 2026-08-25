# Mensagens de abertura prontas

> Escritas em 24/08/2026, no fim da sessão de revisão da 03. Copiar e colar.
> Cada uma abre **um chat novo**, e a separação é de propósito: o `guia-de-trabalho.md` diz
> *"uma sessão por bloco coerente"*, e misturar bookkeeping com arquitetura é o que fez a
> sessão 03 pular o `/code-review`.
>
> **Atualizado em 25/08/2026. A numeração escorregou:** em 25/08 a NVIDIA aposentou embedder e
> reranker às 09:00Z (D-046), e a sessão que seria o Extractor virou reconstrução da stack. O
> que estava escrito aqui como *"Chat B — sessão 05"* é agora a **sessão 06**, e foi reescrito:
> o Extractor deixou de ser o item 1. Ver `projeto/sessao-05.md`.

---

## ~~Chat A — Bloco 0 da sessão 04~~ · EXECUTADO em 24/08, mantido como registro

**Sem plan mode.** É execução mecânica; plan mode existe para decisão arquitetural.

```
Sessão 04, Bloco 0. Leia projeto/revisao-03.md antes de qualquer coisa — é a
auditoria da sessão 03 e contém tudo que esta sessão executa.

Contexto em uma linha: há ~1.350 linhas em 19 arquivos sem commit, a auditoria
achou 5 afirmações que não se sustentam, e o texto das correções já está pronto.

Ordem, e não comece nada fora dela:

1. /code-review high sobre a árvore de trabalho. Me apresente os achados e
   ESPERE — eu decido o que entra antes de qualquer commit.

2. Me mostre as 12 mensagens de commit ANTES de rodar qualquer git commit.
   Elas são material de defesa do eliminatório nº 4 e roteiro do vídeo, não
   changelog: cada uma leva o PORQUÊ da decisão, em português. O recorte está
   em revisao-03.md §6, e o decisoes.md entra em pedaços com git add -p.
   Commit direto na main — é o fluxo deste projeto, não crie branch.

3. As 4 notas de correção do revisao-03.md §3, acrescentadas no FIM de cada
   decisão afetada (D-034, D-036, D-037, D-040). O log é append-only: não
   apague nem reescreva o que está lá.

4. A decisão que ficou em aberto no fim do §3: o harness passa a rodar a
   configuração de produção, ou fica truncando o pool de propósito como braço
   de controle? Me apresente os dois lados com o custo de cada um. Eu decido.

Critério de pronto: pytest -q dá 39, avaliar_rag.py --validar dá 24/24, e
git status volta limpo.

Regras: não use subagentes. Não comece o Extractor. Não escreva código sem
explicar a decisão antes.
```

---

## Chat B — sessão 06: a RÉGUA dos agentes, e só então o Extractor

**Aperte `Shift+Tab` duas vezes ANTES de enviar**, para entrar em plan mode.

> **Por que o Extractor não é mais o item 1.** A versão anterior deste prompt (24/08) pedia, com
> razão, *"COMO VAMOS MEDIR que o Extractor melhorou, decidido ANTES de escrevê-lo"*. Relendo em
> 25/08: **esse item é impossível de responder com a base como ela está.** São 3 startups e as
> 3 são `perfil_alvo: AI-native` — não existe caso em que um Extractor com LLM e o casador de
> substring discordem de um jeito verificável.
>
> É a assimetria que explica o projeto inteiro: o RAG chegou a nível 4 porque teve régua desde o
> primeiro dia — 24 perguntas, âncora por pergunta, prova executável de ausência. Os agentes não
> têm nenhuma. Escrever o Extractor antes da régua repete exatamente o erro que a revisão da
> sessão 03 encontrou em dois lugares.

```
Sessão 06. Estou em plan mode de propósito — não escreva código de agente nesta
conversa.

Leia, nesta ordem: projeto/sessao-05.md (o EOL de 25/08 e os 3 achados de code
review NÃO pagos), contexto/02-rubrica-ai-native.md (a rubrica que o TAPI não
fornece) e a dívida nº 6 em projeto/sessao-04.md.

AQUECIMENTO, antes do plano e fora dele (~5 min, pode escrever código):
o "token" na lista EXCLUSOES["cripto"] de src/agents/briefing.py:25 casa como
substring, e SINAIS_TECNICOS do Extractor inclui "tokens por segundo". Qualquer
startup que fale em "custo por token" sai reportada como NÃO ELEGÍVEL ao
Inception por ser cripto — inclusive a Axenya, que a curadoria marcou como
prospect de prioridade máxima. Conserte em red-green: teste que falha primeiro.

O diagnóstico do RAG está fechado e ficou MAIS forte com a troca de stack, então
não o refaça: o denso puro sozinho agora faz recall@1 de 95% (antes precisava do
reranker), e e@3 vai a 95% com o passo 7. O problema nunca foi a recuperação — é
a CONSULTA. O Extractor é stub e produz o mesmo conjunto de dores para toda
startup, e consulta genérica recupera chunk genérico.

Quero três coisas, nesta ordem, e nenhuma é código de agente:

1. A RÉGUA DOS AGENTES, e ela vem antes de qualquer implementação. Hoje a base
   tem 3 startups, TODAS AI-native: um classificador que devolvesse "AI-native"
   incondicionalmente passaria em 3 de 3. Me proponha o conjunto mínimo de
   fixtures que torna os agentes mensuráveis — meu palpite é 6 a 8, uma por
   quadrante que contexto/02 precisa distinguir (AI-enabled real, non-AI,
   wrapper disfarçado de AI-native, inelegível ao Inception, evidência fraca ou
   datada), mas o número é seu para propor com argumento.

   NÃO é a M3 inteira: 30-50 empresas é curadoria de dias e não bloqueia isto.
   É o subconjunto que serve de gabarito, do jeito que as 24 perguntas servem
   ao RAG. As perfil_alvo_nota que já existem são boas — o problema é que são
   três e todas com o mesmo rótulo.

   Me diga também O QUE se conta: qual campo, qual critério de acerto, e como
   um resultado ambíguo é registrado. "Medido, não decide" é resultado válido.

2. As opções de desenho do Extractor, com uma recomendação, e para cada uma a
   alternativa descartada e o motivo — é isso que vira resposta pronta quando
   perguntarem "por que não X?".

3. A dívida nº 6 lista duas linhas de ataque e diz "a decidir com medição":
   Extractor real primeiro, ou filtro de recomendabilidade no chunk. Qual vem
   primeiro e por quê.

Antes de eu aprovar, o plano precisa dizer: quantas chamadas de API custa no
total, o que ele NÃO faz, e o que fazer se a medição empatar.

Regras: não use subagentes. Português. Toda decisão vai para decisoes.md no
momento em que é tomada. /code-review high antes de considerar pronto.
```

**Contexto de prazo, para calibrar o escopo:** faltam ~15 dias e os critérios 1 e 3 valem
**40 pontos** em nível de stub — `src/rag/geracao.py` é o único arquivo do projeto que chama um
LLM. O critério 2 (RAG) vale 20 e já está no teto. A sessão marginal rende aqui, não em mais RAG.

---

## Chat C — a M3 completa, em paralelo *(opcional, mas é o risco de prazo)*

A M3 vence em **02/09** e não começou. O `plano.md` a chama de *"o maior sumidouro do
projeto"*, e é trabalho braçal que **não bloqueia código** — então dá para intercalar.

> **Não confundir com o item 1 do Chat B.** São duas coisas de tamanho diferente e a ordem
> importa: o Chat B pede o **subconjunto que serve de gabarito** (6-8 startups, uma por
> quadrante, com resultado esperado escrito) e é **bloqueante** — sem ele não há como medir se
> um agente com LLM melhorou. Este Chat C é a **base completa** de 30-50, que é volume de
> demonstração e não régua.
>
> Se o tempo apertar, **a régua sobrevive e o volume é cortado** — é o que o `plano.md` já diz
> em outras palavras: *"corte o número de empresas, não o rigor"*. Uma base de 10 bem curadas
> com os quadrantes cobertos vale mais, no barema, que 50 rasas todas do mesmo tipo.

```
Sessão de curadoria: a M3, base de startups. Leia contexto/04-ecossistema-br.md
e projeto/plano.md (marco M3), mais um arquivo existente de data/seed/*.yaml
para pegar o formato.

Alvo: 30 a 50 startups, 3+ documentos cada, url_fonte real e que resolve, com
diversidade entre AI-native / AI-enabled / non-AI — incluindo os casos difíceis
de propósito: inelegível ao Inception, evidência fraca, wrapper disfarçado de
AI-native.

Comece me propondo o CRITÉRIO de seleção e a divisão por quadrante, não a lista.
Uma base pequena e bem curada vale mais que grande e rasa — o barema avalia o
raciocínio sobre os dados, não o tamanho do dataset.

scripts/coletar.py <url> traz o texto real de uma página, e
scripts/seed.py --verificar-urls confere que toda url_fonte resolve.

Regras: não use subagentes. Nenhuma url_fonte inventada — se não resolver, não entra.
```

---

## Uma linha para o `CLAUDE.md`

A regra *"subagentes: evitar neste projeto"* mora no `guia-de-trabalho.md`, que **não carrega
sozinho** — só o `CLAUDE.md` carrega. Por isso ela está repetida à mão nos três prompts. Para
resolver de vez, digitar no prompt de qualquer sessão:

```
# Não usar subagentes neste projeto: eles começam sem contexto e devolvem resultado
# pronto, que é o oposto do eliminatório nº 4. Ver projeto/guia-de-trabalho.md.
```

O `#` acrescenta ao `CLAUDE.md` sem abrir o arquivo.
