# Mensagens de abertura prontas

> Escritas em 24/08/2026, no fim da sessão de revisão da 03. Copiar e colar.
> Cada uma abre **um chat novo**, e a separação é de propósito: o `guia-de-trabalho.md` diz
> *"uma sessão por bloco coerente"*, e misturar bookkeeping com arquitetura é o que fez a
> sessão 03 pular o `/code-review`.

---

## Chat A — Bloco 0 da sessão 04: review, commits, correções

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

## Chat B — sessão 05: o Extractor real

**Aperte `Shift+Tab` duas vezes ANTES de enviar**, para entrar em plan mode.

```
Sessão 05: o Extractor real. Estou em plan mode de propósito — não escreva
código nesta conversa.

Leia contexto/02-rubrica-ai-native.md (é a rubrica que o TAPI não fornece),
a dívida nº 6 em projeto/sessao-04.md, e projeto/revisao-03.md §1.

O diagnóstico já está fechado e medido, então não o refaça: o recuperador tem
recall@1 de 95% quando a consulta é boa, e a auditoria confirmou isso em três
pools de rerank e duas estratégias de chunking. O problema não é o RAG — é a
CONSULTA. O Extractor é stub e produz "custo, escalabilidade, observabilidade,
privacidade" para toda startup, e consulta genérica recupera chunk genérico.

Quero três coisas, nesta ordem, e nenhuma delas é código:

1. As opções de desenho do Extractor, com uma recomendação. Para cada uma, a
   alternativa descartada e o motivo — é isso que vira resposta pronta quando
   perguntarem "por que não X?".

2. COMO VAMOS MEDIR que o Extractor melhorou a recomendação, decidido ANTES de
   escrevê-lo. A régua não pode ser definida depois de ver o resultado; foi
   exatamente esse o erro que a revisão da sessão 03 encontrou em dois lugares.

3. A dívida nº 6 lista duas linhas de ataque e diz "a decidir com medição":
   Extractor real primeiro, ou filtro de recomendabilidade no chunk. Me diga
   qual vem primeiro e por quê.

Regras: não use subagentes. Português. Toda decisão vai para decisoes.md no
momento em que é tomada.
```

---

## Chat C — a M3, se der para rodar em paralelo *(opcional, mas é o risco de prazo)*

A M3 vence em **02/09** e não começou. O `plano.md` a chama de *"o maior sumidouro do
projeto"*, e é trabalho braçal que **não bloqueia código** — então dá para intercalar.

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
