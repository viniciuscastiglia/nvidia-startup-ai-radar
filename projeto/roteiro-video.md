# Roteiro do vídeo — NVIDIA Startup AI Radar

> **Restrição dura:** máximo 7 minutos. O TAPI exige **três** conteúdos (`contexto/01-tapi.md:210`):
> explicar a **arquitetura dos agentes**, explicar o **sistema RAG**, e **demonstrar o projeto
> funcional pela interface web**. Eliminatório: *"projeto que não executa e cujo vídeo não
> demonstra funcionamento real"*.
>
> **Formato escolhido:** rosto na câmera + tela. **Ênfase:** o sistema rodando ponta a ponta.
>
> **O diferencial declarado é a AVALIAÇÃO** (D-122), não a recusa — a recusa é o caso visível
> dela. Por isso o bloco final não é confissão de defeito, é a resposta a *"como você sabe?"*.
>
> **Medido:** 824 palavras de fala = **5:41 a 145 ppm**, deixando **79 s** para a demo respirar.
>
> **A decisão que organiza o roteiro:** os três obrigatórios NÃO viram três blocos. A trilha do
> fan-out mostra os agentes e a vitrine do passo 7 mostra o rerank — então a explicação vai
> **narrada por cima da demo**. Blocos separados gastariam 7 minutos para entregar 4.

---

## Mapa dos 7 minutos

| tempo | bloco | obrigatório do TAPI |
|---|---|---|
| 0:00–0:30 | O problema e quem usa | — |
| 0:30–2:25 | A consulta e a trilha do fan-out | **agentes** + **demo** |
| 2:25–3:40 | O dossiê: o que o sistema sabe e o que ele NÃO sabe | **demo** |
| 3:40–5:10 | A recomendação e o RAG por trás dela | **RAG** + **demo** |
| 5:10–6:00 | O sistema recusando — o caso visível da régua | **RAG** |
| 6:00–7:00 | **O diferencial: a régua** | — |

---

## 0:00–0:30 · O problema (rosto na câmera)

> "Sou o Vinícius. Isto é o NVIDIA Startup AI Radar, e ele existe para uma pessoa: o gerente de
> Startups e VCs da NVIDIA Brasil, que precisa decidir **quais startups abordar e com qual
> argumento** para o Inception.
>
> A pergunta difícil não é achar startup de IA — é separar quem construiu IA de verdade de quem é
> um wrapper de LLM que os grandes labs apagam no próximo release."

**Nota de produção:** este é o único trecho puramente de rosto. Depois disso o rosto fica no canto.

---

## 0:30–2:25 · A consulta e a trilha do fan-out — **os agentes**

**Tela:** interface em `127.0.0.1:8000`, estado inicial. Digitar
`fintechs com problema de custo de inferência`, `empresas = 2`, clicar **Analisar**.

> "Escrevo em português. Não tem filtro, não tem formulário — a consulta em linguagem natural é a
> entrada.
>
> O que acende na tela agora é o grafo de verdade. **Query Planner** traduz a frase em critérios
> de busca. **Retriever** seleciona as empresas na base. E aqui está a parte que só o LangGraph
> me dava: em vez de analisar as empresas em fila, o grafo faz **fan-out** — uma chamada por
> empresa, com `Send`, e cada uma tem o próprio subgrafo de seis agentes.
>
> As duas linhas **andam em ritmos diferentes** — não é animação, é o estado real de cada branch
> chegando por SSE.
>
> Os seis por empresa: **Extractor** estrutura o texto solto. **Classifier** decide AI-native,
> AI-enabled ou non-AI. **Evidence Validator** checa se a afirmação tem fonte. **Elegibilidade**
> aplica as regras do Inception. **NVIDIA RAG** consulta a base. E **Recommendation** cruza as
> duas coisas.
>
> A ordem entre Elegibilidade e o RAG não é estética: antes, o sistema recomendava tecnologia para
> empresa que ele mesmo tinha recusado."

**⚠️ CORTE OBRIGATÓRIO:** o `nvidia_rag` leva ~60–90 s nas duas empresas. **Corte seco** entre o
início da trilha e o estado final. Medido em 08/09: run de 2 empresas com rerank Cohere ligado.

---

## 2:25–3:40 · O dossiê — **o que o sistema NÃO sabe**

**Tela:** dossiê da Conta Simples, já carregado.

> "Isto é o dossiê de uma empresa. E o que eu quero mostrar não é o que ele afirma — é o que ele
> **se recusa** a afirmar.
>
> Classificação: **non-AI**. Mas olha a faixa tracejada: **'A VERIFICAR — nenhum sinal de IA
> encontrado na base'**. O sistema não está dizendo que a empresa não usa IA. Está dizendo que
> **os documentos que eu tenho não provam que usa** — e são coisas diferentes.
>
> Embaixo, o Inception: **ELEGÍVEL**, com três requisitos em aberto. Ano de fundação não consta,
> developer não confirmado. Ele não chutou nenhum: **reportou como não verificados**.
>
> E cada dor vem com o trecho literal e a URL. Isso não é disciplina minha, é o **tipo**: a classe
> `Afirmacao` não existe sem uma lista de `Evidencia`. Não dá para esquecer de citar — o código
> não deixa."

**Tela:** clicar numa evidência para mostrar a URL real e a regra de confiança.

---

## 3:40–5:10 · A recomendação e o RAG — **o sistema RAG**

**Tela:** rolar até Recomendações. Depois abrir a **vitrine do passo 7**.

> "A recomendação traz os sete campos que o TAPI pede, e eles são atributos de um tipo — não texto
> que um modelo prometeu produzir.
>
> Por trás delas tem o pipeline de RAG de nove passos: as 16 tecnologias viraram **377 chunks**,
> e a busca é **híbrida** — densa com embedding da NVIDIA, mais BM25, fundidas por Reciprocal
> Rank Fusion.
>
> E aí vem o passo 7, o reranking. Eu não peço para você acreditar que funciona — **ele mostra.**
>
> À esquerda, a ordem que a busca híbrida devolveu. À direita, a ordem depois do cross-encoder da
> Cohere, com o deslocamento de cada passagem. Essa aqui subiu da sexta para a primeira.
>
> O que isso compra está medido: recuperar o documento certo, a busca densa sozinha já faz 95% das
> vezes. Mas recuperar o **trecho** que contém a resposta — recall estrito — sai de 79% para
> **95%** com o rerank. A diferença entre achar a página certa e achar a frase certa."

---

## 5:10–6:00 · O sistema recusando — **o caso visível da régua**

**Tela:** botão *"Perguntar à base NVIDIA"*. Pergunta:
`Qual o preço da licença do NVIDIA AI Enterprise por GPU por ano em reais?`

> "Última coisa, e é a que eu mais gosto. Eu pergunto o preço da licença do AI Enterprise.
>
> Ele leu cinco passagens. Todas do AI Enterprise, todas impecáveis no assunto. E a resposta é:
> **não respondeu**. Ele diz o que faltou.
>
> Isso é o passo 8, e a abstenção **não mora num limiar de score** — eu testei duas hipóteses de
> limiar e as duas reprovaram: as distribuições de acerto e de sem-resposta se sobrepõem em todos
> os cinco motores. Não é separável por score. Então a recusa mora no gerador.
>
> Sobre 24 perguntas de gabarito — 19 com resposta na base, 5 sem — ele acerta **23**. E o único
> erro cai no lado seguro: absteve podendo responder."

**⚠️ CORTE OBRIGATÓRIO — MEDIDO EM 377,6 s NO DIA 08/09.** Esta cena **não é filmável em tempo
real**. Grave a pergunta, corte, e retome na resposta. Há um run commitado em
`data/runs/exemplo-*.json` como rede se a API estiver lenta na hora.

---

## 6:00–7:00 · O diferencial: a régua (rosto na câmera + tabela na tela)

**Tela:** terminal com a saída de `avaliar_agentes.py` e `--baseline` lado a lado.

> "Tudo que eu mostrei, eu afirmei. Então a última coisa é **como eu sei**.
>
> Cada afirmação deste sistema tem um script que a mede, e toda tabela tem uma **linha de base
> trivial** obrigatória — um sistema burro, que responde sempre a mesma coisa. Sem ela, '49% de
> precisão' parece bom. Com ela, você vê que são 17 pontos acima de emitir tudo.
>
> E ela me reprova em três campos. O classificador acerta 3 de 7; o trivial acerta 4. Na
> relevância das recomendações eu faço 38% contra 44% dele.
>
> **Isso está publicado no repositório**, com a causa nomeada e o teto do conserto calculado — eu
> medi, e o conserto recupera uma empresa. Deixei assim de propósito: mexer no classificador
> agora seria calibrar contra o meu próprio gabarito.
>
> É esse o diferencial que eu entrego. Não é que o sistema acerta tudo — é que **dá para saber
> onde ele erra, e o número está aqui.** Obrigado."

---

## Checklist antes de gravar

- [ ] `python scripts/smoke_nvidia.py` — 3/3. **Não existe aviso prévio de EOL nesse catálogo**
- [ ] `RERANK_PROVEDOR=cohere` — com o rerank desligado a tela mostra a tecnologia errada
- [ ] `empresas = 2` — 3 empresas custaram 143 s medidos
- [ ] **NÃO rodar `--refetch`** — reescreve o cache e o corpus deixa de ser o que foi medido
- [ ] Fechar as abas e notificações; a tela inteira aparece
- [ ] Ter `data/runs/exemplo-*.json` aberto num run salvo como plano B

## Os dois cortes que o vídeo exige, e por quê

| onde | espera real | medido em |
|---|---|---|
| entre a trilha e o resultado | 60–90 s no `nvidia_rag` | 08/09, 2 empresas, Cohere |
| entre a pergunta e a abstenção | **377,6 s** | 08/09, caminho de produção |

**Nenhum dos dois é defeito de gravação — os dois são latência real do fornecedor**, e o vídeo é
uma restrição de entrega, não uma afirmação sobre a velocidade do sistema.
