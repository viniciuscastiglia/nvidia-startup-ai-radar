# Guia de trabalho — como usar o Claude Code neste case

Documento pessoal de método. Escrito em 22/08/2026.

## Por que este arquivo existe

Usar IA para construir não é o risco. O risco é terminar com um sistema que funciona e que eu não
entendo — porque **um sistema que eu não entendo eu não consigo evoluir, depurar nem revisar.**
Cada decisão que eu não sei explicar é uma parte do sistema que virou caixa-preta para o próprio
autor: quando ela quebrar, ou quando um requisito mudar, não há por onde começar.

Este projeto não termina na entrega — ele fica no portfólio e vai ser lido e mexido depois. Todo o
método abaixo existe para que isso seja possível.

O TAPI, aliás, diz a mesma coisa por outro lado:

> *"O uso de IA como ferramenta de desenvolvimento é permitido e esperado. O que se avalia é a
> capacidade de tomar e defender decisões técnicas."*

---

## O modo de trabalho

**Não é "peço e recebo código". É: ele explica → eu decido → ele implementa.**

### O que fazer

**Pedir a decisão antes do código.**
*"Me explica as opções de chunking e recomenda uma"* vale muito mais que *"implementa o
chunking"*. No primeiro caso eu fico com a razão; no segundo, só com o resultado.

**Perguntar "por que não X?" em toda escolha.**
É a resposta que torna a decisão reversível: sem a alternativa registrada, revisitar a escolha
daqui a duas semanas custa refazer a análise inteira. Assim que vier, registrar em `decisoes.md`.

**Interrogar a própria arquitetura.**
Depois de fechar cada parte: *"me faz 5 perguntas difíceis sobre a arquitetura do RAG que eu
acabei de construir"*. Se eu travar em alguma, achei um buraco real — a pergunta que eu não sei
responder quase sempre marca uma escolha que foi feita por inércia e não por decisão.
**Este é o uso mais valioso da ferramenta neste projeto.** Serve de ensaio para o vídeo de quebra.

**Plan mode para tudo que é arquitetural.**
`Shift+Tab` duas vezes. Ele não escreve nada, só pesquisa e propõe. O plano vira documentação, e
o processo força revisar a abordagem antes de existir código para defender por inércia.

**`/code-review` antes de considerar qualquer parte pronta.**

**Uma sessão por bloco coerente.**
"Hoje: ingestão do RAG." Sessão muito longa é resumida e perde detalhe. Como o `CLAUDE.md` e a
pasta `contexto/` carregam sozinhos, sessão nova já começa quente — fechar e abrir não tem custo.

**Commit por decisão, com o porquê na mensagem.**
O histórico do git vira material de defesa.

### O que evitar

**Não pedir o sistema inteiro de uma vez.**
Sai algo que roda e que eu não consigo explicar — e que, portanto, eu não consigo consertar quando
quebrar.

**Não deixar entrar código que eu não li.**
Se algo não está claro, perguntar antes de commitar — não depois.

**Subagentes: evitar neste projeto.**
São úteis para trabalho paralelo independente, mas começam sem contexto e devolvem o resultado
pronto. Num sistema em que cada peça precisa continuar evoluível por mim, receber código que eu não
vi nascer é dívida imediata.

---

## Manutenção da documentação

### `CLAUDE.md` — contexto durável, não diário de bordo
É carregado em **toda** sessão, então tudo que está lá custa contexto. Nunca colocar status,
todo-list ou narrativa do que aconteceu.

**E nunca colocar número.** Número envelhece, e o `CLAUDE.md` é o arquivo que menos se relê com
olhos críticos — foi assim que ele chegou a apresentar dois modelos mortos como vigentes, vinte
linhas acima do próprio aviso de que eles estavam mortos (achado 5 de D-066). A régua mora na
decisão que a produziu; o `CLAUDE.md` aponta para ela.

**O que vale adicionar conforme o projeto anda:**
- seção **Comandos** — subir o banco, rodar o grafo, popular a base, rodar os testes.
  É o que mais economiza tempo em sessão nova
- **convenções** que emergirem: nomenclatura dos nós, estrutura de pastas, formato do estado

> Atalho: digitar `#` seguido do texto no prompt adiciona ao `CLAUDE.md` sem abrir o arquivo.

### `contexto/` — referência estável
O levantamento do case. Só muda se um fato mudar (um link cair, a NVIDIA renomear um produto).

### `projeto/` — vivo
Quatro arquivos: `plano.md` (a sequência), `decisoes.md` (o log), este guia (o método) e
`sessao-atual.md` (o que está aberto agora).

**`decisoes.md` guarda a decisão, não o caderno de laboratório** (D-073, 31/08). A regra anterior
era *"só cresce, nunca reescreve"*, e ela produziu um arquivo de 3.367 linhas com 16 blocos de
correção empilhados: para saber o fato corrente de uma decisão era preciso ler três camadas. A
regra nova:

- **o append-only é garantido pelo git, não pelo arquivo.** `git show` na revisão anterior devolve
  qualquer versão. Manter tudo no arquivo não compra segurança — compra presença na árvore de
  trabalho, que é o custo.
- **um número só fica se é verdade sobre o sistema que roda hoje.** Se o instrumento que o
  produziu morreu, fica a **conclusão**, e só quando ela sobrevive ao instrumento. Medição de
  instrumento morto é armadilha: este projeto já foi mordido por ela (D-064 recomendou por nome um
  modelo que devolvia 404).
- quando uma medição posterior derruba uma conclusão, isso **não some** — vira uma linha
  `**Revisto:**` na decisão. São 13 hoje, e elas são o material mais forte do log.

**`sessao-atual.md` guarda só o que está ABERTO.** Não é diário: fechamento de sessão vira decisão
no log, ou não vale registro.

---

## Para que serve o log de decisões

**Para que a decisão continue revisável.** Uma escolha sem a alternativa descartada ao lado não é
revisável: daqui a duas semanas, mudar de ideia custa refazer a análise inteira, e a tendência é
manter a escolha por inércia — que é o pior motivo possível para manter qualquer coisa.

É por isso que o campo **Alternativas descartadas** é o mais importante do formato, e é por isso
que ele é escrito **no momento da decisão**: reconstituir o raciocínio depois é impossível, e o que
sai da reconstituição é justificativa, não razão.

Os subprodutos são reais e valem ser lembrados — o log é o roteiro do vídeo e vira a seção de
arquitetura do README. Mas eles são subprodutos: **quem escreve para um público escreve a defesa;
quem escreve para si mesmo daqui a seis meses escreve a verdade, inclusive a parte feia.** É a
segunda que serve, e é a que faz o arquivo caber.

---

## Para o vídeo

Chegando perto de 06/09:
- pedir revisão do roteiro contra o teto de 7 minutos e contra o que o TAPI pede que ele mostre
  (arquitetura dos agentes + sistema RAG + demonstração funcional)
- ensaiar com ele antes de gravar, interrogando a arquitetura como acima
- abrir falando da persona real — Andrei Golfeto, Community Manager do Inception LatAm, +1.300
  startups e +140 fundos (ver `contexto/04-ecossistema-br.md` §4). Enquadra o projeto como
  ferramenta de trabalho, não exercício acadêmico

---

## Lembrete final

Toda vez que aparecer a tentação de acelerar aceitando código que eu não entendi: **o tempo que
isso economiza hoje é cobrado com juros na primeira vez que aquela parte quebrar.** Um sistema que
o próprio autor não consegue percorrer não é rápido — é só um sistema onde todo conserto começa do
zero.
