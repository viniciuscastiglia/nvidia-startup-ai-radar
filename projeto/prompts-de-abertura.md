# Mensagem de abertura — sessão 06

> Copiar e colar num chat novo. Este arquivo guarda **só a próxima sessão**: prompt de abertura
> velho é armadilha, porque carrega diagnóstico que já mudou. Os anteriores estão no git.
>
> **Aperte `Shift+Tab` duas vezes ANTES de enviar**, para entrar em plan mode.

## Por que o Extractor não é o item 1

A versão anterior deste prompt (24/08) pedia, com razão, *"COMO VAMOS MEDIR que o Extractor
melhorou, decidido ANTES de escrevê-lo"*. Relendo em 25/08: **esse item é impossível de responder
com a base como ela está.** São 3 startups e as 3 são `perfil_alvo: AI-native` — não existe caso
em que um Extractor com LLM e o casador de substring discordem de um jeito verificável.

É a assimetria que explica o projeto inteiro: o RAG chegou a nível 4 porque teve régua desde o
primeiro dia — 24 perguntas, âncora por pergunta, prova executável de ausência. Os agentes não
têm nenhuma. Escrever o agente antes da régua repete exatamente o erro que a revisão da sessão 03
encontrou em dois lugares.

---

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

   scripts/coletar.py <url> traz o texto real de uma página, e
   scripts/seed.py --verificar-urls confere que toda url_fonte resolve.
   Nenhuma url_fonte inventada — se não resolver, não entra.

2. As opções de desenho do Extractor, com uma recomendação, e para cada uma a
   alternativa descartada e o motivo — é isso que vira resposta pronta quando
   perguntarem "por que não X?".

3. A dívida nº 6 lista duas linhas de ataque e diz "a decidir com medição":
   Extractor real primeiro, ou filtro de recomendabilidade no chunk. Qual vem
   primeiro e por quê.

Antes de eu aprovar, o plano precisa dizer: quantas chamadas de API custa no
total — contando o pytest, que roda o grafo de verdade e estourou o orçamento
da sessão 05 —, o que ele NÃO faz, e o que fazer se a medição empatar.

Regras: português. Toda decisão vai para decisoes.md no momento em que é tomada.
/code-review high antes de considerar pronto.
```

---

**Contexto de prazo, para calibrar o escopo:** faltam ~15 dias e os critérios 1 e 3 valem
**40 pontos** em nível de stub — `src/rag/geracao.py` é o único arquivo do projeto que chama um
LLM. O critério 2 (RAG) vale 20 e já está no teto. A sessão marginal rende aqui, não em mais RAG.

**Depois da 06:** o Extractor com a régua no lugar, o fallback local (Bloco 2 da pauta em
`sessao-05.md`) e a M3 completa — 30 a 50 startups, que é volume de demonstração e não régua.
Critérios da M3 em `plano.md`; o prompt de curadoria que existia aqui saiu no commit de 25/08 e
está no git se for útil.
