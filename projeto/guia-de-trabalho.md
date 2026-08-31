# Guia de trabalho — como usar o Claude Code neste case

Documento pessoal de método. Escrito em 22/08/2026.

## Por que este arquivo existe

O critério eliminatório nº 4 do barema é:

> *"Código integralmente gerado sem compreensão: o candidato precisa explicar as decisões de
> arquitetura do próprio projeto."*

E a observação do TAPI logo abaixo:

> *"O uso de IA como ferramenta de desenvolvimento é permitido e esperado. O que se avalia é a
> capacidade de tomar e defender decisões técnicas."*

Ou seja: usar IA não é o risco. O risco é terminar com um sistema que funciona e que eu não
consigo defender. Todo o método abaixo existe para evitar isso.

---

## O modo de trabalho

**Não é "peço e recebo código". É: ele explica → eu decido → ele implementa.**

### O que fazer

**Pedir a decisão antes do código.**
*"Me explica as opções de chunking e recomenda uma"* vale muito mais que *"implementa o
chunking"*. No primeiro caso eu fico com a razão; no segundo, só com o resultado.

**Perguntar "por que não X?" em toda escolha.**
Essa resposta é literalmente o que o avaliador vai perguntar. Assim que vier, registrar em
`decisoes.md`.

**Usar ele como banca.**
Depois de fechar cada parte: *"me faz 5 perguntas difíceis sobre a arquitetura do RAG que eu
acabei de construir"*. Se eu travar em alguma, achei o buraco antes do avaliador achar.
**Este é o uso mais valioso da ferramenta neste projeto** — e é o ensaio direto para o vídeo.

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
Sai algo que roda e que eu não consigo explicar. É o eliminatório nº 4 em linha reta.

**Não deixar entrar código que eu não li.**
Se algo não está claro, perguntar antes de commitar — não depois.

**Subagentes: evitar neste projeto.**
São úteis para trabalho paralelo independente, mas começam sem contexto e devolvem o resultado
pronto — exatamente o que eu não quero num projeto onde preciso entender cada peça.

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

## Os três usos do log de decisões

`projeto/decisoes.md` é o hábito de maior alavancagem do projeto porque um único artefato serve
três superfícies de nota:

| Superfície | Peso | Como o log serve |
|---|---|---|
| Eliminatório nº 4 | eliminatório | é o material de defesa |
| Vídeo de apresentação | 20 | é o roteiro pronto |
| Repositório e documentação | 10 | vira a seção de arquitetura do README |

**Escrever no momento da decisão.** Reconstituir o raciocínio no dia 08/09 é impossível.

---

## Para o vídeo (peso 20)

Chegando perto de 06/09:
- pedir revisão do roteiro contra o teto de 7 minutos e contra o que o barema exige
  (arquitetura dos agentes + sistema RAG + demonstração funcional)
- ensaiar com ele antes de gravar, no modo banca
- abrir falando da persona real — Andrei Golfeto, Community Manager do Inception LatAm, +1.300
  startups e +140 fundos (ver `contexto/04-ecossistema-br.md` §4). Enquadra o projeto como
  ferramenta de trabalho, não exercício acadêmico

---

## Lembrete final

Toda vez que aparecer a tentação de acelerar aceitando código que eu não entendi: o barema não
dá ponto por velocidade. Dá ponto por decisão consciente. E tira tudo se eu não souber explicar.
